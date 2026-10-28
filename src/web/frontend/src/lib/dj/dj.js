// The web DJ engine (W1): the iOS QueueStore, NowPlayingModel, SuggestionStore,
// DJSettings and DJSync in one place. The synced state is a single document
// (`doc`, the SY1 schema), so every edit is one `edit()` and one push. What
// only this tab needs (who's playing, driving bookkeeping) stays local.
//
// Roles are Jam-style, as on iOS: only the primary sends to Spotify, skips on
// arrival, detects requests, records history and runs autopilot. Every device
// edits. No silent failover: a quiet primary is reported, and "Drive from
// here" (`claimPrimary`) moves the role.
import { get, writable } from 'svelte/store';
import * as L from './logic.js';

/** Tracks kept ahead in Spotify while the tab is visible; the rest stays editable. */
const FOREGROUND_DEPTH = 1;
/** While hidden, browsers throttle timers (down to ~1/min), so keep more lined up. */
const BACKGROUND_DEPTH = 5;
const REQUEST_POLL_MS = 10000;
// Player polling (tracker 477d21): Spotify rate-limits /me/player per app, and
// every device and tab polling every 2 s drew 1,157 429s in 38 minutes.
// Progress is interpolated locally, so polls only need to catch changes.
const POLL_MS = 5000; // sync and track changes show within ~5 s
const TAB_FOLLOWER_POLL_MS = 15000; // another tab of this browser is driving
const IDLE_POLL_MS = 10000; // nothing playing
const MAX_BACKOFF_MS = 60000;

export function safeStorage() {
	return {
		get(k) {
			try {
				return localStorage.getItem(k);
			} catch {
				return null;
			}
		},
		set(k, v) {
			try {
				localStorage.setItem(k, v);
			} catch {
				/* private mode / full: the doc still syncs */
			}
		}
	};
}

function deviceLabel() {
	const platform = /** @type {any} */ (globalThis.navigator)?.userAgentData?.platform;
	return platform ? `${platform} web` : 'Web';
}

/**
 * @param {object} deps
 * @param {(method: string, path: string, opts?: {json?: any, headers?: Record<string, string>}) => Promise<{status: number, data: any}>} deps.request
 * @param {() => boolean} [deps.hasLLM]
 * @param {{get: (k: string) => string | null, set: (k: string, v: string) => void}} [deps.storage]
 * @param {string} [deps.label]
 * @param {() => number} [deps.now]
 * @param {number} [deps.debounceMs]
 * @param {(() => Promise<unknown>) | null} [deps.onUnauthorized] refresh the Spotify token after a 401
 * @param {{request: (name: string, cb: () => Promise<unknown>) => unknown} | null} [deps.locks] Web Locks, to elect one driving tab per browser
 */
export function createDJ({ request, hasLLM = () => true, storage = safeStorage(), label = deviceLabel(), now = () => Date.now(), debounceMs = 400, onUnauthorized = null, locks = /** @type {any} */ (globalThis.navigator)?.locks ?? null }) {
	const load = (k) => {
		try {
			return JSON.parse(storage.get(k) ?? 'null');
		} catch {
			return null;
		}
	};

	const deviceID = storage.get('dj_device_id') || crypto.randomUUID();
	storage.set('dj_device_id', deviceID);

	// --- Stores (what the UI renders) ---
	const doc = writable(L.withDefaults(load('dj_doc')));
	doc.subscribe((d) => storage.set('dj_doc', JSON.stringify(d)));
	/** @type {import('svelte/store').Writable<{state: any, message: string | null}>} */
	const player = writable({ state: null, message: null });
	// Start in the last known role, so a participant doesn't drive before its first poll.
	let isPrimary = load('dj_is_primary') ?? true;
	/** @type {import('svelte/store').Writable<{status: string, error: string | null, primary: any, notice: string | null, isPrimary: boolean, deviceID: string, label: string}>} */
	const sync = writable({ status: 'unavailable', error: null, primary: null, notice: null, isPrimary, deviceID, label });
	/** @type {import('svelte/store').Writable<{status: string, moves: any[], error: string | null}>} */
	const suggestions = writable({ status: 'idle', moves: [], error: null });
	// F3c: what the host said was off about each move this session, and which
	// moves are being re-asked right now.
	/** @type {import('svelte/store').Writable<Record<string, string[]>>} */
	const moveFeedback = writable({});
	/** @type {import('svelte/store').Writable<Record<string, boolean>>} */
	const moveLoading = writable({});
	// Tonight's set (F3f): what played on this device, for Save tonight's set.
	const setlog = writable(load('dj_setlog') ?? []);
	setlog.subscribe((log) => storage.set('dj_setlog', JSON.stringify(log)));

	// Tabs in one browser share a device id (localStorage), so without this every
	// open tab would drive: double-queuing tracks and flagging each other's sends
	// as guest requests (review C1). One tab holds the lock until it closes; the
	// next waiting tab then takes over.
	let tabLeader = !locks;
	/** Whether this tab sends to Spotify: the primary device, and its leading tab. */
	const drives = () => isPrimary && tabLeader;

	const d = () => get(doc);
	const setSync = (patch) => sync.update((s) => ({ ...s, ...patch }));
	const setMessage = (message) => player.update((p) => ({ ...p, message }));

	// --- Local bookkeeping ---
	let version = 0;
	/** @type {any} */
	let base = null; // last document this tab and the server agreed on
	let applying = false;
	let pushTimer = null;
	let pushing = null;
	let syncing = false;
	let lastTrackID = null;
	let lastQueueView = null;
	const autoSkipped = new Set();
	let toppingUp = false;
	let depth = FOREGROUND_DEPTH;
	let fetchedAt = now();
	let lastRequestPoll = 0;
	let messageFromPoll = false;
	let failures = 0;
	let backoffMs = 0;
	let suggestedFor = null;
	const cache = new Map();
	/** @type {string | null} */
	let inFlight = null;

	/** Every change to synced state goes through here. */
	function edit(fn) {
		doc.update((x) => {
			fn(x);
			return x;
		});
		changed();
	}

	// --- Sync (DJSync on iOS) ---

	function changed() {
		if (applying || !base) return;
		clearTimeout(pushTimer);
		pushTimer = setTimeout(() => {
			pushTimer = null;
			pushing = push().finally(() => (pushing = null));
		}, debounceMs); // coalesce bursts (drag-reorder)
	}

	async function push(attempt = 0) {
		const local = structuredClone(d());
		if (!base || L.docsEqual(local, base) || attempt >= 3) return;
		let r;
		try {
			r = await request('PUT', 'dj/state', { json: { state: local }, headers: { 'If-Match': String(version) } });
		} catch {
			return; // offline: the local copy stands; the next edit or poll retries
		}
		if (r.status === 200) {
			version = r.data.version;
			base = local;
			setPrimary(r.data.primary);
			setSync({ status: 'synced', error: null });
		} else if (r.status === 409) {
			// Someone else saved first. Keep our changed fields on top of theirs.
			const server = r.data.state ?? L.emptyDoc();
			const merged = L.merge(base, local, server);
			adopt(server, r.data.version);
			apply(merged);
			await push(attempt + 1);
		} else {
			// e.g. 422 (client/server schema drift) or sync down: don't claim "synced" (review W3).
			setSync({ status: 'error', error: r.data?.detail ? String(r.data.detail).slice(0, 200) : `Sync failed (${r.status}).` });
		}
	}

	async function observeSync(dj) {
		if (!dj) {
			// Sync off or unreachable: keep the last role; one failed poll must not start a participant driving.
			if (!base) setSync({ status: 'unavailable' });
			return;
		}
		setPrimary(dj.primary);
		if (dj.version === 0) await seed();
		else if (dj.version !== version && !pushTimer && !pushing) await pull();
	}

	async function pull() {
		if (syncing) return;
		syncing = true;
		try {
			const before = structuredClone(d());
			const r = await request('GET', 'dj/state');
			if (r.status !== 200 || !r.data.state) return;
			if (!base && !L.isEmptyDoc(before) && !L.docsEqual(r.data.state, before)) {
				setSync({ notice: 'Using the queue from your other device.' });
			}
			const editedMeanwhile = base && !L.docsEqual(d(), before);
			const local = structuredClone(d());
			adopt(r.data.state, r.data.version);
			setPrimary(r.data.primary);
			setSync({ status: 'synced', error: null });
			if (editedMeanwhile) {
				// An edit landed while the GET was in flight: keep it on top of the
				// server's copy and push, instead of overwriting it (review W2).
				await apply(L.merge(before, local, r.data.state));
				changed();
			} else {
				await apply(r.data.state);
			}
		} catch {
			/* next poll retries */
		} finally {
			syncing = false;
		}
	}

	/** No shared state yet: this tab uploads its own and becomes primary. Losing that race means adopting the winner. */
	async function seed() {
		if (syncing) return;
		syncing = true;
		try {
			const local = structuredClone(d());
			const r = await request('PUT', 'dj/state', {
				json: { state: local },
				headers: { 'If-Match': '0', 'X-DJ-Device': deviceID, 'X-DJ-Label': label }
			});
			if (r.status === 200) {
				adopt(local, r.data.version);
			} else if (r.status === 409 && r.data.state) {
				adopt(r.data.state, r.data.version);
				apply(r.data.state);
			} else return;
			setPrimary(r.data.primary);
			setSync({ status: 'synced' });
		} catch {
			/* next poll retries */
		} finally {
			syncing = false;
		}
	}

	function adopt(state, v) {
		base = structuredClone(state);
		version = v;
	}

	function apply(state) {
		const before = d().options;
		applying = true;
		doc.set(structuredClone(state));
		applying = false;
		if (!L.docsEqual(before, state.options)) prefetch();
		// A participant's add only reaches Spotify through the primary.
		return topUp(depth);
	}

	function setPrimary(info) {
		// No primary recorded: this tab drives until someone claims.
		const nowPrimary = info ? info.device === deviceID : true;
		setSync({ primary: info ?? null });
		if (nowPrimary === isPrimary) return;
		isPrimary = nowPrimary;
		storage.set('dj_is_primary', JSON.stringify(isPrimary));
		setSync({ isPrimary });
		if (isPrimary) startDriving();
	}

	/** Drive from here. */
	async function claimPrimary() {
		try {
			const r = await request('POST', 'dj/primary', { json: { device: deviceID, label } });
			if (r.status === 200) setPrimary(r.data.primary);
		} catch {
			/* stays a participant; the button can be pressed again */
		}
	}

	/** Push any pending edit now (tests; leaving the page). */
	async function flush() {
		if (pushTimer) {
			clearTimeout(pushTimer);
			pushTimer = null;
			pushing = push().finally(() => (pushing = null));
		}
		await pushing;
	}

	// --- The queue (QueueStore on iOS) ---

	const aheadCount = () => d().queue.sent.filter((s) => !s.skipOnArrival).length + d().queue.upcoming.length;

	async function add(track, extra = {}) {
		edit((x) => x.queue.upcoming.push(L.queueItem(track, extra)));
		await topUp(depth);
	}

	/**
	 * Queue a DJ pick (plan Q2). Picks come from Deezer with no Spotify id, so
	 * this spends the one Spotify search a song costs: resolve by ISRC, then add.
	 * @returns {Promise<{ok: true} | {ok: false, reason: 'not_on_spotify' | 'explicit' | 'unavailable'}>}
	 */
	async function addPick(pick, extra = {}) {
		let r;
		try {
			r = await request('POST', 'tracks/resolve/', { json: { songs: [{ isrc: pick.isrc ?? null, title: pick.title, artist: pick.artists?.[0] ?? '' }] } });
		} catch {
			return { ok: false, reason: 'unavailable' };
		}
		if (r.status !== 200) return { ok: false, reason: 'unavailable' };
		const track = r.data?.tracks?.[0];
		if (!track) return { ok: false, reason: 'not_on_spotify' };
		// Deezer's copy can be clean while Spotify only has the explicit one.
		if (d().options.clean && track.explicit) return { ok: false, reason: 'explicit' };
		await add({ id: track.id, title: track.title, artists: track.artists, image: track.image, isrc: pick.isrc ?? track.isrc }, extra);
		return { ok: true };
	}

	function moveUpcoming(from, to) {
		edit((x) => {
			const [it] = x.queue.upcoming.splice(from, 1);
			x.queue.upcoming.splice(to, 0, it);
		});
	}

	function removeUpcoming(id) {
		edit((x) => (x.queue.upcoming = x.queue.upcoming.filter((i) => i.id !== id)));
	}

	/** A sent track can't leave Spotify; it's skipped on arrival and replaced. */
	async function removeSent(id) {
		markSkip(id);
		await topUp(depth);
	}

	async function playLater(item) {
		markSkip(item.id);
		edit((x) => x.queue.upcoming.push(L.queueItem(item)));
		await topUp(depth);
	}

	function markSkip(id) {
		edit((x) => {
			const s = x.queue.sent.find((i) => i.id === id);
			if (s) s.skipOnArrival = true;
		});
	}

	/** A song started: note it in tonight's set, with who put it there. */
	function logSong(track) {
		const q = d().queue;
		const entry = {
			id: track.id,
			title: track.title,
			artists: track.artists ?? [],
			image: track.image ?? '',
			duration_ms: track.duration_ms ?? 0,
			dj: !!q.sent.find((i) => i.trackID === track.id)?.addedByDJ,
			guest: q.keptGuests.includes(track.id) || q.requests.some((r) => r.trackID === track.id)
		};
		setlog.update((log) => L.logPlay(log, entry, now()));
	}

	/** Everything in Up next, so an edit can be undone (F3b). */
	function snapshotUpcoming() {
		return structuredClone(d().queue.upcoming);
	}

	/**
	 * Undo an Up next edit: put the list back as it was, minus anything that
	 * has since gone to Spotify (that can't be taken back).
	 */
	async function restoreSnapshot(snapshot) {
		edit((x) => {
			const sent = new Set(x.queue.sent.map((i) => i.id));
			x.queue.upcoming = snapshot.filter((i) => !sent.has(i.id));
		});
		await topUp(depth);
	}

	/** Empty Up next (songs already in Spotify stay). */
	function clearUpcoming() {
		edit((x) => (x.queue.upcoming = []));
	}

	/** Undo for "remove" in Up next: put the entry back where it was. */
	async function restoreUpcoming(item, index) {
		edit((x) => {
			if (x.queue.upcoming.some((i) => i.id === item.id)) return;
			x.queue.upcoming.splice(Math.min(index, x.queue.upcoming.length), 0, item);
		});
		await topUp(depth);
	}

	/** Undo for "decline": forget the skip and put the request back. */
	function undoDecline(req) {
		edit((x) => {
			const i = x.queue.guestSkips.lastIndexOf(req.trackID);
			if (i >= 0) x.queue.guestSkips.splice(i, 1);
			if (!x.queue.requests.some((r) => r.id === req.id)) x.queue.requests.push(req);
		});
	}

	function keep(req) {
		edit((x) => {
			x.queue.requests = x.queue.requests.filter((r) => r.id !== req.id);
			if (!x.queue.keptGuests.includes(req.trackID)) x.queue.keptGuests.push(req.trackID);
		});
	}

	async function later(req) {
		edit((x) => {
			x.queue.requests = x.queue.requests.filter((r) => r.id !== req.id);
			x.queue.guestSkips.push(req.trackID);
			x.queue.upcoming.push(L.queueItem(req));
		});
		await topUp(depth);
	}

	function decline(req) {
		edit((x) => {
			x.queue.requests = x.queue.requests.filter((r) => r.id !== req.id);
			x.queue.guestSkips.push(req.trackID);
		});
	}

	/** Send tracks from Up Next until `n` non-skipped tracks are ahead in Spotify. Primary only. */
	async function topUp(n) {
		if (!drives() || toppingUp) return;
		toppingUp = true;
		try {
			while (d().queue.sent.filter((s) => !s.skipOnArrival).length < n && d().queue.upcoming.length) {
				const next = d().queue.upcoming[0];
				let r;
				try {
					r = await request('POST', 'spotify/queue/', { json: { track_ids: [next.trackID] } });
				} catch {
					setMessage("Couldn't reach the server.");
					return;
				}
				if (r.status !== 200 || r.data?.queued !== 1) {
					setMessage(r.data?.error ? L.describe(r.data.error) : r.data?.detail ?? "Couldn't queue that track.");
					return;
				}
				setMessage(null);
				// By id, not position: a synced edit may have landed during the call.
				edit((x) => {
					x.queue.upcoming = x.queue.upcoming.filter((i) => i.id !== next.id);
					x.queue.sent.push(next);
				});
			}
		} finally {
			toppingUp = false;
		}
	}

	/** After every poll: act on a track change. Primary only. */
	async function observeTrack(state) {
		const trackID = state.track?.id;
		if (!drives() || !trackID || trackID === lastTrackID) return;
		lastTrackID = trackID;
		// Guest skips first: after "Later" the guest's earlier copy is the one arriving.
		const gi = d().queue.guestSkips.indexOf(trackID);
		if (gi >= 0) {
			edit((x) => x.queue.guestSkips.splice(gi, 1));
			await skipCurrent(trackID);
		} else {
			const { remaining, arrived } = L.arrival(trackID, d().queue.sent);
			edit((x) => {
				x.queue.sent = remaining;
				if (!arrived) {
					// An undecided request that arrives just plays: Spotify already put it there.
					x.queue.requests = x.queue.requests.filter((r) => r.trackID !== trackID);
					x.queue.keptGuests = x.queue.keptGuests.filter((k) => k !== trackID);
				}
			});
			if (arrived?.skipOnArrival) await skipCurrent(trackID);
		}
		await topUp(depth);
	}

	async function skipCurrent(trackID) {
		autoSkipped.add(trackID);
		await request('POST', 'player/next/').catch(() => {});
		// The next track may share this id (after "Later"); re-observe whatever plays.
		lastTrackID = null;
	}

	async function readQueue() {
		try {
			const r = await request('GET', 'player/queue/');
			return r.status === 200 ? r.data.queue : null;
		} catch {
			return null;
		}
	}

	/** On start / tab return: drop sent tracks that played meanwhile, using Spotify's queue. */
	async function reconcile() {
		const state = get(player).state;
		if (!drives() || !state) return;
		lastTrackID = null;
		await observeTrack(state);
		const queue = await readQueue();
		if (!queue) return;
		edit((x) => (x.queue.sent = L.reconciled(x.queue.sent, queue.map((t) => t.id))));
		record(queue, state.smart_shuffle ?? false);
		await topUp(depth);
	}

	async function pollRequests(smartShuffle) {
		if (!drives()) return;
		const queue = await readQueue();
		if (queue) record(queue, smartShuffle);
	}

	function record(queue, smartShuffle) {
		const view = queue.map((t) => t.id);
		const q = d().queue;
		const found = L.detectRequests({
			previous: lastQueueView,
			current: view,
			appIDs: new Set(q.sent.map((s) => s.trackID)),
			ignoring: new Set([...q.requests.map((r) => r.trackID), ...q.keptGuests, ...q.guestSkips]),
			insertionsAllowed: !smartShuffle
		});
		if (found.length) edit((x) => x.queue.requests.push(...found.map((i) => L.guestRequest(queue[i]))));
		lastQueueView = view;
	}

	/** Became primary mid-session: resume driving from the shared queue. */
	function startDriving() {
		lastTrackID = null;
		lastQueueView = null;
		topUp(depth);
	}

	// --- Options (DJSettings on iOS) ---

	function setOption(key, value) {
		edit((x) => (x.options[key] = value));
		prefetch();
	}

	function avoidTrack(t) {
		if (d().options.avoidTracks.some((a) => a.id === t.id)) return;
		edit((x) => x.options.avoidTracks.push({ id: t.id, title: t.title, artist: t.artists?.[0] ?? t.artist ?? '', ...(t.isrc ? { isrc: t.isrc } : {}) }));
	}

	function avoidArtist(name) {
		if (d().options.avoidArtists.some((a) => a.toLowerCase() === name.toLowerCase())) return;
		edit((x) => x.options.avoidArtists.push(name));
	}

	function unavoid({ track, artist }) {
		edit((x) => {
			if (track) x.options.avoidTracks = x.options.avoidTracks.filter((a) => a.id !== track);
			if (artist) x.options.avoidArtists = x.options.avoidArtists.filter((a) => a !== artist);
		});
	}

	// --- Now playing (NowPlayingModel on iOS) ---

	function progressMs(at = now()) {
		const s = get(player).state;
		if (!s?.progress_ms) return 0;
		const elapsed = s.is_playing ? at - fetchedAt : 0;
		return Math.min(s.progress_ms + elapsed, s.track?.duration_ms ?? Infinity);
	}

	async function refresh() {
		let r;
		try {
			r = await request('GET', 'player/state/', { headers: { 'X-DJ-Device': deviceID } });
		} catch {
			r = { status: 0, data: null };
		}
		if (r.status === 401 && onUnauthorized) {
			// The Spotify token expired mid-session (review C2): refresh, retry next poll.
			await onUnauthorized().catch(() => {});
		}
		if (r.status !== 200) {
			player.update((p) => ({ ...p, message: r.data?.detail ?? "Couldn't reach the server." }));
			messageFromPoll = true;
			// Back off: Spotify's Retry-After when the server passes it on, else 5, 10, 20, 40, 60 s.
			failures++;
			backoffMs = Math.min(MAX_BACKOFF_MS, r.data?.retry_after ? r.data.retry_after * 1000 : POLL_MS * 2 ** (failures - 1));
			return;
		}
		failures = 0;
		backoffMs = 0;
		const s = r.data;
		const previous = get(player).state?.track;
		// History and skips are recorded by the primary; others get them via sync.
		if (drives() && previous && previous.id !== s.track?.id) {
			const skipped = progressMs() < previous.duration_ms / 2 && !autoSkipped.has(previous.id);
			edit((x) => {
				if (skipped) x.feedback.skipped = L.pushFront(x.feedback.skipped, L.trackRef(previous), 5);
				x.recent = L.pushFront(x.recent, L.trackRef(previous), 10);
			});
		}
		if (s.track && previous?.id !== s.track.id) logSong(s.track);
		fetchedAt = now();
		player.update((p) => {
			const stale = messageFromPoll || (p.message === L.NO_DEVICE && s.active);
			return { state: s, message: stale ? null : p.message };
		});
		if (messageFromPoll) messageFromPoll = false;
		await observeSync(s.dj);
		await observeTrack(s);
		// Spotify's queue is a slower read: every ~10s, not every poll.
		if (now() - lastRequestPoll >= REQUEST_POLL_MS) {
			lastRequestPoll = now();
			await pollRequests(s.smart_shuffle ?? false);
		}
		if (s.track && s.track.id !== suggestedFor) {
			suggestedFor = s.track.id;
			prefetch();
		}
	}

	function rate(track, more) {
		const ref = L.trackRef(track);
		edit((x) => {
			x.feedback.liked = x.feedback.liked.filter((t) => t.id !== ref.id);
			x.feedback.disliked = x.feedback.disliked.filter((t) => t.id !== ref.id);
			if (more) x.feedback.liked = L.pushFront(x.feedback.liked, ref, 5);
			else x.feedback.disliked = L.pushFront(x.feedback.disliked, ref, 5);
		});
	}

	async function send(command) {
		try {
			const r = await request('POST', `player/${command}/`);
			setMessage(r.data?.error ? L.describe(r.data.error) : null);
		} catch {
			setMessage("Couldn't reach the server.");
		}
		messageFromPoll = false;
		// Spotify's player state lags a command slightly; re-read after a beat.
		await new Promise((res) => setTimeout(res, 400));
		await refresh();
	}

	// --- Suggestions (SuggestionStore on iOS) ---

	// Suggestions cost an LLM call and 20-50 Spotify searches, so they're only
	// fetched while a DJ page is open, or when Autofill/Driver need picks to queue.
	let watchers = 0;

	/** The DJ page calls this on mount; the returned function on destroy. */
	function watchSuggestions() {
		// The library seeds Familiar ↔ New; rounds use it once it has arrived.
		loadLibrary();
		watchers++;
		prefetch();
		return () => watchers--;
	}

	function prefetch() {
		const track = get(player).state?.track;
		if (!track) return;
		if (!watchers && L.AUTOPILOT_TARGET[d().options.mode] === 0) return;
		if (d().options.mode === 'whisper') suggestions.set({ status: 'idle', moves: [], error: null });
		else loadSuggestions(track);
	}

	const ref = (t) => ({ id: t.trackID ?? t.id ?? '', isrc: t.isrc ?? null, title: t.title, artist: t.artists?.[0] ?? t.artist ?? '' });

	// The listener's top tracks seed Familiar ↔ New (F3d); fetched once per session.
	let library = null;
	let libraryLoad = null;
	function loadLibrary() {
		libraryLoad ??= fetchLibrary();
		return libraryLoad;
	}
	async function fetchLibrary() {
		try {
			const r = await request('GET', 'spotify/top-tracks/?limit=20');
			library = r.status === 200 ? (r.data?.tracks ?? []).map(ref) : [];
		} catch {
			library = [];
		}
		return library;
	}

	/** The /dj/suggest/ request for a track: the night so far, the host's taste and controls. */
	function suggestBody(track, extra = {}) {
		const o = d().options;
		const q = d().queue;
		const f = d().feedback;
		return {
			now_playing: ref(track),
			recent: d().recent.map(ref),
			upcoming: [...q.sent, ...q.upcoming].map(ref),
			adventurousness: o.adventurousness,
			clean: o.clean,
			liked: f.liked.map(ref),
			disliked: f.disliked.map(ref),
			skipped: f.skipped.map(ref),
			avoid_tracks: o.avoidTracks.map(ref),
			avoid_artists: o.avoidArtists,
			goal: o.goal && {
				kind: o.goal.kind,
				destination: o.goal.destination ?? '',
				shape: o.goal.shape ?? 'build',
				minutes: o.goal.minutes ?? 30,
				elapsed_minutes: Math.max(0, L.elapsedMinutes(o.goal, now()))
			},
			feedback: get(moveFeedback),
			familiar: o.familiar ?? 0.5,
			library: library ?? [],
			...extra
		};
	}

	/**
	 * Re-ask one move (F3c), optionally saying what was off about its picks.
	 * Only that move's picks change; the rest of the round stays.
	 * @param {string} move
	 * @param {string} [note] e.g. 'Too slow'; none = "just show new ones"
	 */
	async function refreshMove(move, note) {
		const track = get(player).state?.track;
		if (!track || get(moveLoading)[move]) return;
		if (note) moveFeedback.update((fb) => ({ ...fb, [move]: [...new Set([...(fb[move] ?? []), note])].slice(-6) }));
		moveLoading.update((m) => ({ ...m, [move]: true }));
		const shown = get(suggestions).moves.find((m) => m.move === move)?.tracks ?? [];
		try {
			const r = await request('POST', 'dj/suggest/', { json: suggestBody(track, { only_moves: [move], exclude: shown.map(ref) }) });
			const fresh = r.data?.moves?.find((m) => m.move === move);
			if (r.status !== 200 || !fresh?.tracks.length) return { ok: false };
			if (get(player).state?.track?.id !== track.id) return { ok: false }; // the song changed meanwhile
			suggestions.update((s) => ({ ...s, moves: s.moves.map((m) => (m.move === move ? fresh : m)) }));
			cache.clear(); // a cached round would bring the replaced picks back
			return { ok: true };
		} catch {
			return { ok: false };
		} finally {
			moveLoading.update((m) => ({ ...m, [move]: false }));
		}
	}

	async function loadSuggestions(track = get(player).state?.track, force = false) {
		if (!track) return;
		const o = d().options;
		// Settings that change the answer are part of the key.
		const key = `${track.id}|${Math.floor(o.adventurousness * 3)}|${Math.floor((o.familiar ?? 0.5) * 3)}|${o.clean}|${L.goalKey(o.goal, now())}|${JSON.stringify(get(moveFeedback))}`;
		if (!force && cache.has(key)) {
			suggestions.set({ status: 'loaded', moves: cache.get(key), error: null });
			return autopilot();
		}
		// Don't stack requests for the same answer (Groq's per-minute token limit).
		if (inFlight === key) return;
		inFlight = key;
		suggestions.update((s) => ({ ...s, status: 'loading' }));
		const body = suggestBody(track);
		try {
			const r = await request('POST', 'dj/suggest/', { json: body });
			if (inFlight !== key) return; // a newer track started its own load
			const moves = r.data?.moves ?? [];
			if (r.status !== 200 || !moves.length) {
				suggestions.set({ status: 'failed', moves: [], error: r.data?.error ?? r.data?.detail ?? 'No suggestions this time.' });
				return;
			}
			if (cache.size > 20) cache.clear();
			cache.set(key, moves);
			suggestions.set({ status: 'loaded', moves, error: null, source: r.data?.source ?? 'ai' });
			await autopilot();
		} catch {
			if (inFlight === key) suggestions.set({ status: 'failed', moves: [], error: "Couldn't reach the server." });
		} finally {
			if (inFlight === key) inFlight = null;
		}
	}

	/** Autofill and Driver: keep the mode's target lined up from the current moves. Primary only. */
	async function autopilot() {
		const o = d().options;
		const target = L.AUTOPILOT_TARGET[o.mode] ?? 0;
		const s = get(suggestions);
		if (!drives() || target === 0 || aheadCount() >= target || s.status !== 'loaded') return;
		const queued = L.queuedKeys([...d().queue.sent, ...d().queue.upcoming]);
		const lead = o.goal ? (o.goal.kind === 'drift' ? 'drift' : 'toward') : null;
		const candidates = L.autopilotCandidates(s.moves, o.adventurousness, queued, lead);
		// Each add is one Spotify lookup; a miss just moves on to the next candidate.
		while (aheadCount() < target && candidates.length) await addPick(candidates.shift(), { addedByDJ: true });
	}

	// --- Lifecycle ---

	let timer = null;
	let running = false;

	function nextDelay() {
		if (backoffMs) return backoffMs;
		const s = get(player).state;
		if (!s?.active) return IDLE_POLL_MS;
		// Another tab of this browser drives; this one only mirrors (review C1).
		if (isPrimary && !tabLeader) return TAB_FOLLOWER_POLL_MS;
		if (!s.is_playing || !s.track) return POLL_MS;
		// The driver wakes just after the track should end, so the next song is
		// handled promptly; everyone else just polls.
		const remaining = s.track.duration_ms - progressMs();
		if (drives() && remaining < POLL_MS + 500) return Math.max(300, remaining + 300);
		return POLL_MS;
	}

	async function loop() {
		if (!running) return;
		await refresh();
		if (running) timer = setTimeout(loop, nextDelay());
	}

	function onVisibility() {
		if (document.visibilityState === 'hidden') {
			depth = BACKGROUND_DEPTH;
			topUp(depth);
			flush();
		} else {
			depth = FOREGROUND_DEPTH;
			reconcile();
		}
	}

	async function start() {
		if (running) return;
		running = true;
		globalThis.document?.addEventListener('visibilitychange', onVisibility);
		await refresh();
		await reconcile();
		timer = setTimeout(loop, nextDelay());
	}

	function stop() {
		running = false;
		clearTimeout(timer);
		globalThis.document?.removeEventListener('visibilitychange', onVisibility);
		flush();
	}

	// Ask for the driving-tab lock last, once everything it may call exists.
	locks?.request('boomin-beats-dj-driver', () => {
		tabLeader = true;
		if (isPrimary) startDriving();
		return new Promise(() => {}); // held for the life of the tab
	});

	return {
		doc,
		player,
		sync,
		suggestions,
		moveFeedback,
		moveLoading,
		setlog,
		clearSet: () => setlog.set([]),
		refreshMove,
		// lifecycle
		start,
		stop,
		refresh,
		flush,
		// sync
		claimPrimary,
		dismissNotice: () => setSync({ notice: null }),
		nextDelay,
		// queue
		add,
		addPick,
		moveUpcoming,
		snapshotUpcoming,
		restoreSnapshot,
		clearUpcoming,
		removeUpcoming,
		restoreUpcoming,
		removeSent,
		playLater,
		keep,
		later,
		decline,
		undoDecline,
		// options
		setMode: (m) => setOption('mode', m),
		setAdventurousness: (a) => setOption('adventurousness', a),
		setFamiliar: (f) => setOption('familiar', f),
		setClean: (c) => setOption('clean', c),
		// Every field filled, as the server stores it.
		setGoal: (g) => setOption('goal', g && { destination: '', shape: 'build', minutes: 30, ...g, startedAt: g.startedAt ?? new Date(now()).toISOString() }),
		avoidTrack,
		avoidArtist,
		unavoid,
		// now playing
		send,
		rate,
		progressMs,
		loadSuggestions,
		watchSuggestions,
		// for widgets with their own reads (Song profile)
		request
	};
}
