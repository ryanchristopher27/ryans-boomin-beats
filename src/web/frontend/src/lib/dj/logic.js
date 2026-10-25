// Pure DJ logic (W1), ported one to one from the iOS app so both clients drive
// Spotify the same way: QueueStore (arrival, reconcile, request detection),
// SuggestionStore (autopilot order, goal cache key) and SyncDoc (merge, shape).
// Unit-tested in logic.test.js; keep in step with BoominBeatsTests.

/** How many upcoming tracks GET /me/player/queue returns at most. */
export const SPOTIFY_QUEUE_WINDOW = 20;

/**
 * Spotify plays queued tracks in order, so arriving at sent[i] means everything
 * before it has already played or been skipped elsewhere.
 * @returns {{ remaining: any[], arrived: any | null }}
 */
export function arrival(trackID, sent) {
	const i = sent.findIndex((s) => s.trackID === trackID);
	if (i < 0) return { remaining: sent, arrived: null };
	return { remaining: sent.slice(i + 1), arrived: sent[i] };
}

/**
 * `sent` minus whatever Spotify has already played, given the ids in its queue
 * view. Played tracks are a prefix of `sent`; the rest is matched in order so a
 * track queued twice pairs with the right copy. A full view (20) may hide
 * trailing tracks, so those are kept. Ceiling: 20+ non-app tracks ahead of ours
 * hide everything, and all of it is treated as played.
 */
export function reconciled(sent, queue) {
	const start = sent.findIndex((s) => queue.includes(s.trackID));
	if (start < 0) return [];
	let remaining = queue;
	const kept = [];
	for (let k = start; k < sent.length; k++) {
		const i = remaining.indexOf(sent[k].trackID);
		if (i >= 0) {
			kept.push(sent[k]);
			remaining = remaining.slice(i + 1);
		} else if (queue.length >= SPOTIFY_QUEUE_WINDOW) {
			kept.push(...sent.slice(k));
			break;
		}
	}
	return kept;
}

/**
 * Indices in `current` (Spotify's queue view) that are guest requests: wedged
 * ahead of one of the app's own tracks, or inserted mid-view since the previous
 * poll (off under Smart Shuffle, which inserts its own picks).
 */
export function detectRequests({ previous, current, appIDs, ignoring, insertionsAllowed }) {
	let lastApp = -1;
	current.forEach((id, i) => appIDs.has(id) && (lastApp = i));
	const previousSet = new Set(previous ?? []);
	let lastShared = -1;
	if (insertionsAllowed && previousSet.size) current.forEach((id, i) => previousSet.has(id) && (lastShared = i));
	const seen = new Set();
	const found = [];
	current.forEach((id, i) => {
		if (appIDs.has(id) || ignoring.has(id)) return;
		const wedged = i < lastApp;
		const inserted = i < lastShared && !previousSet.has(id);
		if ((wedged || inserted) && !seen.has(id)) {
			seen.add(id);
			found.push(i);
		}
	});
	return found;
}

/**
 * Picks in the order autopilot takes them: the goal's move (`lead`) first, then
 * the other moves ranked by adventurousness, one per move per round.
 */
/** @param {any[]} moves @param {number} adventurousness @param {Set<string>} queued @param {string | null} [lead] */
export function autopilotCandidates(moves, adventurousness, queued, lead = null) {
	const a = adventurousness;
	const order =
		a < 0.34 ? ['hold', 'lift', 'drop'] : a < 0.67 ? ['hold', 'lift', 'pivot', 'drop', 'curveball'] : ['pivot', 'curveball', 'lift', 'hold'];
	const tracksOf = (name) => moves.find((m) => m.move === name)?.tracks;
	const lists = order.map(tracksOf).filter(Boolean);
	const candidates = (lead ? tracksOf(lead) ?? [] : []).filter((p) => !queued.has(p.id));
	const longest = Math.max(0, ...lists.map((l) => l.length));
	for (let i = 0; i < longest; i++) {
		for (const list of lists) if (i < list.length && !queued.has(list[i].id)) candidates.push(list[i]);
	}
	return candidates;
}

/** How many tracks the DJ keeps lined up after the current one, per mode. */
export const AUTOPILOT_TARGET = { whisper: 0, copilot: 0, autofill: 1, driver: 3 };

export function elapsedMinutes(goal, now = Date.now()) {
	return (now - Date.parse(goal.startedAt)) / 60000;
}

/** Cache-key part for a goal. An arc's instruction changes as it progresses, so its key moves every 5 minutes. */
export function goalKey(goal, now = Date.now()) {
	if (!goal) return 'none';
	if (goal.kind === 'destination') return `dest:${goal.destination}`;
	if (goal.kind === 'arc') return `arc:${goal.shape}:${goal.minutes}:${Math.floor(elapsedMinutes(goal, now) / 5)}`;
	return 'drift';
}

// --- The shared document (SY1 schema in backend/routers/dj_state.py) ---

/** @returns {any} */
export function emptyDoc() {
	return {
		queue: { sent: [], upcoming: [], requests: [], guestSkips: [], keptGuests: [] },
		options: { mode: 'copilot', adventurousness: 0.5, clean: false, goal: null, avoidTracks: [], avoidArtists: [] },
		feedback: { liked: [], disliked: [], skipped: [] },
		recent: []
	};
}

/** Every syncable field, as [section, key] (`recent` is top level). */
/** @param {string | null} section @param {string[]} keys @returns {[string | null, string][]} */
const fields = (section, keys) => keys.map((k) => [section, k]);
const FIELDS = [
	...fields('queue', ['sent', 'upcoming', 'requests', 'guestSkips', 'keptGuests']),
	...fields('options', ['mode', 'adventurousness', 'clean', 'goal', 'avoidTracks', 'avoidArtists']),
	...fields('feedback', ['liked', 'disliked', 'skipped']),
	...fields(null, ['recent'])
];

/** @param {any} doc @param {[string | null, string]} field */
const read = (doc, [s, k]) => (s ? doc[s][k] : doc[k]);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/**
 * Three-way merge after a 409: start from the server's document and keep every
 * field this device changed since `base`. If both changed a field, this device
 * wins (it's the one retrying). Same rule as SyncDoc.merge on iOS.
 */
export function merge(base, local, server) {
	const out = structuredClone(server);
	for (const f of FIELDS) {
		if (same(read(local, f), read(base, f))) continue;
		const v = structuredClone(read(local, f));
		const [section, key] = f;
		if (section) out[section][key] = v;
		else out[key] = v;
	}
	return out;
}

export function docsEqual(a, b) {
	return same(a, b);
}

export function isEmptyDoc(doc) {
	const e = emptyDoc();
	return same(doc.queue, e.queue) && same(doc.feedback, e.feedback) && doc.recent.length === 0;
}

/** A track reduced to what the shared doc stores (the server's TrackRef). */
export function trackRef(t) {
	return { id: t.id, title: t.title, artists: t.artists ?? [], image: t.image ?? '' };
}

/** A new queue entry. `id` names the entry, not the track, so a song can be queued twice. */
export function queueItem(t, extra = {}) {
	return { id: crypto.randomUUID(), trackID: t.trackID ?? t.id, title: t.title, artists: t.artists ?? [], image: t.image ?? '', skipOnArrival: false, ...extra };
}

/** A guest request (the server's GuestRequest: no skip flag). */
export function guestRequest(t) {
	return { id: crypto.randomUUID(), trackID: t.id, title: t.title, artists: t.artists ?? [], image: t.image ?? '' };
}

/** Most recent first, deduped, capped. */
export function pushFront(list, track, cap) {
	return [track, ...list.filter((t) => t.id !== track.id)].slice(0, cap);
}

const NO_DEVICE = 'Open Spotify on any device to start playback.';

export function describe(error) {
	if (error === 'no_active_device') return NO_DEVICE;
	if (error === 'premium_required') return 'Playback control needs Spotify Premium.';
	return "Spotify didn't allow that right now.";
}
export { NO_DEVICE };
