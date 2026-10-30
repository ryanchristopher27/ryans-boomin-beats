// The web DJ engine against an in-memory backend with the SY1 contract:
// version + If-Match, 409 with the current document, the primary role.
import { describe, expect, test } from 'vitest';
import { get } from 'svelte/store';
const g = get;
import { createDJ } from './dj.js';

const track = (id) => ({ id, title: id, artists: ['A'], image: '', duration_ms: 200000 });

function fakeServer() {
	/** @type {any} */
	const s = { row: null, queued: [], playing: track('now'), calls: [] };
	/** @param {string} device */
	s.request = (device) => async (/** @type {string} */ method, /** @type {string} */ path, /** @type {any} */ { json = undefined, headers = {} } = {}) => {
		s.calls.push({ device, method, path });
		const doc = () => ({ version: s.row?.version ?? 0, state: s.row?.state ?? null, primary: s.row?.primary ?? null });
		if (path === 'player/state/') {
			return { status: 200, data: { active: true, is_playing: true, progress_ms: 1000, track: s.playing, dj: { version: s.row?.version ?? 0, primary: s.row?.primary ?? null } } };
		}
		if (path === 'player/queue/') return { status: 200, data: { queue: s.queued.map(track) } };
		if (path === 'tracks/resolve/') {
			s.resolves = (s.resolves ?? 0) + 1;
			const song = json.songs[0];
			const known = { USAAA0000001: { id: 'sp1', explicit: false }, USAAA0000002: { id: 'sp2', explicit: true } }[song.isrc];
			return { status: 200, data: { tracks: [known ? { ...known, title: song.title, artists: ['A'], image: '', isrc: song.isrc } : null] } };
		}
		if (path === 'spotify/queue/') {
			s.queued.push(...json.track_ids);
			return { status: 200, data: { queued: 1 } };
		}
		if (path === 'dj/state' && method === 'GET') return { status: 200, data: doc() };
		if (path === 'dj/state' && method === 'PUT') {
			const want = Number(headers['If-Match']);
			if (want === 0) {
				if (s.row) return { status: 409, data: doc() };
				s.row = { version: 1, state: structuredClone(json.state), primary: { device: headers['X-DJ-Device'], label: headers['X-DJ-Label'], online: true } };
				return { status: 200, data: doc() };
			}
			if (!s.row || s.row.version !== want) return { status: 409, data: doc() };
			s.row = { ...s.row, version: want + 1, state: structuredClone(json.state) };
			return { status: 200, data: doc() };
		}
		if (path === 'dj/suggest/' && s.suggestMoves) {
			s.suggestBodies = [...(s.suggestBodies ?? []), json];
			const pick = (id) => ({ id, title: id, artists: ['A'], image: '', reason: '' });
			const all = [{ move: 'hold', tracks: [pick('h1')] }, { move: 'lift', tracks: [pick('l1')] }];
			const round = s.suggestBodies.length;
			const moves = json.only_moves?.length ? json.only_moves.map((m) => ({ move: m, tracks: [pick(`${m[0]}${round}`)] })) : all;
			return { status: 200, data: { moves } };
		}
		if (path === 'dj/primary') {
			s.row.primary = { device: json.device, label: json.label, online: true };
			return { status: 200, data: doc() };
		}
		return { status: 200, data: { ok: true } };
	};
	return s;
}

function memoryStorage() {
	const m = new Map();
	return { get: (k) => m.get(k) ?? null, set: (k, v) => m.set(k, v) };
}

const tab = (server, name) => {
	const storage = memoryStorage();
	storage.set('dj_device_id', name);
	return createDJ({ request: server.request(name), storage, label: name, hasLLM: () => false, debounceMs: 0, locks: null });
};

describe('web DJ engine', () => {
	test('the first tab seeds the shared state, becomes primary and drives', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh();
		expect(server.row.primary.device).toBe('a');
		expect(get(a.sync).isPrimary).toBe(true);

		await a.add(track('t1'));
		await a.flush();
		expect(server.queued).toEqual(['t1']); // one ahead sent to Spotify
		expect(server.row.state.queue.sent.map((i) => i.trackID)).toEqual(['t1']);
	});

	test('addMany appends a whole set in order, sending only one ahead (F3h)', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh();
		await a.addMany([track('t1'), track('t2'), track('t3')]);
		await a.flush();
		expect(server.queued).toEqual(['t1']);
		expect(server.row.state.queue.upcoming.map((i) => i.trackID)).toEqual(['t2', 't3']);
	});

	test('a participant edits the shared queue but never sends to Spotify', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh();
		const b = tab(server, 'b');
		await b.refresh();
		expect(get(b.sync).isPrimary).toBe(false);
		expect(get(b.sync).primary.label).toBe('a');

		await b.add(track('t1'));
		await b.flush();
		expect(server.calls.some((c) => c.device === 'b' && c.path === 'spotify/queue/')).toBe(false);
		expect(server.row.state.queue.upcoming.map((i) => i.trackID)).toEqual(['t1']);

		// The primary picks it up on its next poll and sends it.
		await a.flush();
		await a.refresh();
		expect(server.queued).toEqual(['t1']);
	});

	test('concurrent edits to different fields both survive (409 merge)', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh();
		const b = tab(server, 'b');
		await b.refresh();

		await b.add(track('t1')); // b saves first
		await b.flush();
		a.setMode('driver'); // a is still on the old version
		await a.flush();

		expect(server.row.state.options.mode).toBe('driver');
		expect(server.row.state.queue.upcoming.map((i) => i.trackID)).toEqual(['t1']);
	});

	test('Drive from here moves the role', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh();
		const b = tab(server, 'b');
		await b.refresh();
		await b.claimPrimary();
		expect(get(b.sync).isPrimary).toBe(true);
		await a.refresh();
		expect(get(a.sync).isPrimary).toBe(false);
	});

	test('undo puts a removed song and a declined request back', async () => {
		const server = fakeServer();
		const b = tab(server, 'b');
		server.row = { version: 1, state: null, primary: { device: 'a', label: 'a', online: true } };
		const { get: g } = await import('svelte/store');
		await b.refresh(); // a participant: nothing leaves for Spotify
		await b.add(track('t1'));
		await b.add(track('t2'));
		const item = g(b.doc).queue.upcoming[0];
		b.removeUpcoming(item.id);
		await b.restoreUpcoming(item, 0);
		expect(g(b.doc).queue.upcoming.map((i) => i.trackID)).toEqual(['t1', 't2']);

		b.doc.update((x) => ((x.queue.requests = [{ id: 'r', trackID: 'g', title: 'g', artists: [], image: '' }]), x));
		const req = g(b.doc).queue.requests[0];
		b.decline(req);
		b.undoDecline(req);
		expect(g(b.doc).queue.requests.map((r) => r.id)).toEqual(['r']);
		expect(g(b.doc).queue.guestSkips).toEqual([]);
	});

	test('Up next edits undo from a snapshot, minus songs already sent', async () => {
		const server = fakeServer();
		const b = tab(server, 'b');
		server.row = { version: 1, state: null, primary: { device: 'a', label: 'a', online: true } };
		await b.refresh(); // a participant: nothing leaves for Spotify
		for (const id of ['t1', 't2', 't3']) await b.add(track(id));
		const ids = () => g(b.doc).queue.upcoming.map((i) => i.trackID);

		let snap = b.snapshotUpcoming();
		b.moveUpcoming(2, 0); // Play next
		expect(ids()).toEqual(['t3', 't1', 't2']);
		await b.restoreSnapshot(snap);
		expect(ids()).toEqual(['t1', 't2', 't3']);

		snap = b.snapshotUpcoming();
		b.clearUpcoming();
		expect(ids()).toEqual([]);
		// Meanwhile t2 went to Spotify: undo can't bring it back into Up next.
		b.doc.update((x) => ((x.queue.sent = [{ ...snap[1] }]), x));
		await b.restoreSnapshot(snap);
		expect(ids()).toEqual(['t1', 't3']);
	});

	test('suggestions are only fetched while watched, or when autopilot needs them', async () => {
		const server = fakeServer();
		const storage = memoryStorage();
		storage.set('dj_device_id', 'a');
		const a = createDJ({ request: server.request('a'), storage, label: 'a', hasLLM: () => true, debounceMs: 0, locks: null });
		const asks = () => server.calls.filter((c) => c.path === 'dj/suggest/').length;
		await a.refresh();
		expect(asks()).toBe(0); // Co-pilot, no DJ page open
		const stop = a.watchSuggestions();
		expect(asks()).toBe(1);
		await new Promise((r) => setTimeout(r, 0)); // let that ask settle (the in-flight guard)
		stop();
		a.setMode('driver');
		expect(asks()).toBe(2); // Driver queues picks itself
	});

	test('the board stays when the song changes and comes back after a reload; the setting asks every song', async () => {
		const server = fakeServer();
		server.suggestMoves = true;
		const storage = memoryStorage();
		storage.set('dj_device_id', 'a');
		const settle = () => new Promise((r) => setTimeout(r, 0));
		const asks = () => server.calls.filter((c) => c.path === 'dj/suggest/').length;
		let everySong = false;
		const a = createDJ({ request: server.request('a'), storage, label: 'a', hasLLM: () => true, debounceMs: 0, locks: null, everySong: () => everySong });
		await a.refresh();
		const stop = a.watchSuggestions();
		await settle();
		expect(asks()).toBe(1);
		expect(g(a.suggestions).forTrack.id).toBe('now');

		server.playing = track('next');
		await a.refresh();
		await settle();
		expect(g(a.suggestions).forTrack.id).toBe('now'); // the board on screen stays
		expect(asks()).toBe(2); // ...while the new song's board is built in the background
		await a.loadSuggestions(); // "New picks for next": already built, no new ask
		expect(asks()).toBe(2);
		expect(g(a.suggestions).forTrack.id).toBe('next');

		// A reload (a new engine on the same storage) shows the saved board at once.
		const b = createDJ({ request: server.request('a'), storage, label: 'a', hasLLM: () => true, debounceMs: 0, locks: null, everySong: () => false });
		expect(g(b.suggestions)).toMatchObject({ status: 'loaded', forTrack: { id: 'next' } });

		everySong = true;
		server.playing = track('third');
		await a.refresh();
		await settle();
		expect(asks()).toBe(3);
		expect(g(a.suggestions).forTrack.id).toBe('third');
		stop();
	});

	test('parallel rounds ask one move per request and show moves as they land', async () => {
		const server = fakeServer();
		server.suggestMoves = true;
		const storage = memoryStorage();
		storage.set('dj_device_id', 'a');
		const a = createDJ({ request: server.request('a'), storage, label: 'a', hasLLM: () => true, debounceMs: 0, locks: null, parallelMoves: () => true });
		await a.refresh();
		a.watchSuggestions();
		await new Promise((r) => setTimeout(r, 0));
		const asked = server.suggestBodies.map((b) => b.only_moves);
		expect(asked).toEqual([['hold'], ['lift'], ['drop'], ['pivot'], ['curveball']]);
		expect(g(a.suggestions).moves.map((m) => m.move)).toEqual(['hold', 'lift', 'drop', 'pivot', 'curveball']);
	});

	test('near the end of a song, the next sent song gets its board in the background', async () => {
		const server = fakeServer();
		server.suggestMoves = true;
		const storage = memoryStorage();
		storage.set('dj_device_id', 'a');
		const a = createDJ({ request: server.request('a'), storage, label: 'a', hasLLM: () => true, debounceMs: 0, locks: null });
		await a.refresh();
		a.watchSuggestions();
		await a.add(track('t1')); // sent to Spotify as the next song
		await a.flush();
		await new Promise((r) => setTimeout(r, 0));
		const before = server.suggestBodies.length;
		server.playing = { ...track('now'), duration_ms: 30000 }; // 29 s left
		await a.refresh();
		await new Promise((r) => setTimeout(r, 0));
		expect(server.suggestBodies.slice(before).map((b) => b.now_playing.id)).toEqual(['t1']);
	});

	test('a failed round keeps the board it would have replaced', async () => {
		const server = fakeServer();
		server.suggestMoves = true;
		const storage = memoryStorage();
		storage.set('dj_device_id', 'a');
		const a = createDJ({ request: server.request('a'), storage, label: 'a', hasLLM: () => true, debounceMs: 0, locks: null });
		await a.refresh();
		a.watchSuggestions();
		await new Promise((r) => setTimeout(r, 0));
		server.suggestMoves = false; // the fake answers with no moves now
		await a.loadSuggestions(undefined, true);
		expect(g(a.suggestions)).toMatchObject({ status: 'loaded', error: 'No suggestions this time.' });
		expect(g(a.suggestions).moves.length).toBe(2);
	});

	test('a per-move refresh re-asks only that move, with feedback, and keeps the rest', async () => {
		const server = fakeServer();
		server.suggestMoves = true;
		const storage = memoryStorage();
		storage.set('dj_device_id', 'a');
		const a = createDJ({ request: server.request('a'), storage, label: 'a', hasLLM: () => true, debounceMs: 0, locks: null });
		await a.refresh();
		const stop = a.watchSuggestions();
		await new Promise((r) => setTimeout(r, 0));
		const tracksOf = (m) => g(a.suggestions).moves.find((x) => x.move === m).tracks.map((t) => t.id);
		expect(tracksOf('lift')).toEqual(['l1']);

		await a.refreshMove('lift', 'Too slow');
		const body = server.suggestBodies.at(-1);
		expect(body.only_moves).toEqual(['lift']);
		expect(body.feedback).toEqual({ lift: ['Too slow'] });
		expect(body.exclude.map((r) => r.title)).toEqual(['l1']);
		expect(tracksOf('lift')).toEqual(['l2']);
		expect(tracksOf('hold')).toEqual(['h1']); // untouched
		expect(g(a.moveFeedback)).toEqual({ lift: ['Too slow'] });
		stop();
	});

	test('two tabs of one browser: only the tab holding the lock drives (review C1)', async () => {
		const server = fakeServer();
		// A minimal Web Locks: the first request holds the lock; later ones wait.
		let held = false;
		const waiting = [];
		const locks = {
			request: (_name, cb) => {
				if (held) waiting.push(cb);
				else {
					held = true;
					cb();
				}
			}
		};
		const shared = memoryStorage();
		shared.set('dj_device_id', 'laptop');
		const opts = { storage: shared, label: 'laptop', hasLLM: () => false, debounceMs: 0, locks };
		const first = createDJ({ request: server.request('tab1'), ...opts });
		const second = createDJ({ request: server.request('tab2'), ...opts });
		await first.refresh();
		await second.refresh();
		await second.add(track('t1'));
		await second.flush();
		expect(server.calls.some((c) => c.device === 'tab2' && c.path === 'spotify/queue/')).toBe(false);
		await first.flush();
		await first.refresh();
		expect(server.queued).toEqual(['t1']); // sent once, by the leading tab
		expect(waiting.length).toBe(1); // the second tab takes over when the first closes
	});

	test('an edit made while a pull is in flight survives (review W2)', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh();
		let editMidGet = false;
		const real = server.request('b');
		const storage = memoryStorage();
		storage.set('dj_device_id', 'b');
		const b = createDJ({
			request: async (method, path, opts) => {
				const r = await real(method, path, opts);
				if (editMidGet && method === 'GET' && path === 'dj/state') {
					editMidGet = false;
					b.doc.update((x) => (x.queue.upcoming.push({ id: 'mid', trackID: 'mid', title: 'mid', artists: [], image: '', skipOnArrival: false }), x));
				}
				return r;
			},
			storage, label: 'b', hasLLM: () => false, debounceMs: 0, locks: null
		});
		await b.refresh(); // first sync: adopts v1
		a.setMode('driver'); // a remote change, so b's next poll pulls
		await a.flush();
		editMidGet = true;
		await b.refresh(); // the pull's GET returns after b's edit
		await b.flush();
		expect(g(b.doc).options.mode).toBe('driver');
		expect(g(b.doc).queue.upcoming.map((i) => i.trackID)).toEqual(['mid']);
		expect(server.row.state.queue.upcoming.map((i) => i.trackID)).toEqual(['mid']); // and it was pushed
	});

	test('a push the server rejects shows as an error, not "synced" (review W3)', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh();
		const real = server.request;
		server.request = () => async () => ({ status: 422, data: { detail: 'bad field' } });
		const a2 = createDJ({ request: async (m, p, o) => (m === 'PUT' ? { status: 422, data: { detail: 'bad field' } } : real('a')(m, p, o)), storage: (() => { const s = memoryStorage(); s.set('dj_device_id', 'a'); return s; })(), label: 'a', hasLLM: () => false, debounceMs: 0, locks: null });
		await a2.refresh(); // adopts v1
		a2.setMode('driver');
		await a2.flush();
		expect(g(a2.sync).status).toBe('error');
		expect(g(a2.sync).error).toBe('bad field');
	});

	test('a DJ pick is looked up on Spotify only when queued (plan Q2)', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh();
		const pick = (isrc, title) => ({ id: isrc, isrc, title, artists: ['A'], image: '', reason: '' });

		expect(await a.addPick(pick('USAAA0000001', 'good'))).toEqual({ ok: true });
		const item = g(a.doc).queue.sent[0];
		expect([item.trackID, item.isrc]).toEqual(['sp1', 'USAAA0000001']); // the Spotify id, plus the ISRC
		expect(server.queued).toEqual(['sp1']);

		expect(await a.addPick(pick('USZZZ9999999', 'missing'))).toEqual({ ok: false, reason: 'not_on_spotify' });
		a.setClean(true);
		expect(await a.addPick(pick('USAAA0000002', 'explicit'))).toEqual({ ok: false, reason: 'explicit' });
		expect(server.resolves).toBe(3);
		expect(g(a.doc).queue.upcoming).toEqual([]);
	});

	test('polling: 5 s while playing, near-end wake for the driver, backoff on 503 (477d21)', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh(); // playing, 1 s into a 200 s track
		expect(a.nextDelay()).toBe(5000);

		server.playing = { ...track('now'), duration_ms: 4000 };
		await a.refresh(); // 3 s left: the driver wakes just after the end
		expect(a.nextDelay()).toBe(3300);

		const real = server.request;
		const busy = createDJ({ request: async () => ({ status: 503, data: { detail: 'Spotify is busy.', retry_after: 7 } }), storage: memoryStorage(), label: 'x', hasLLM: () => false, debounceMs: 0, locks: null });
		await busy.refresh();
		expect(busy.nextDelay()).toBe(7000);
		const down = createDJ({ request: async () => ({ status: 500, data: null }), storage: memoryStorage(), label: 'y', hasLLM: () => false, debounceMs: 0, locks: null });
		for (const want of [5000, 10000, 20000, 40000, 60000, 60000]) {
			await down.refresh();
			expect(down.nextDelay()).toBe(want);
		}
		expect(real).toBe(server.request);
	});

	test('a new tab adopts the shared queue and says so', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh();
		a.setMode('autofill');
		await a.flush();

		const storage = memoryStorage();
		storage.set('dj_doc', JSON.stringify({ queue: { sent: [], upcoming: [{ id: 'x', trackID: 'old', title: 'old', artists: [], image: '', skipOnArrival: false }], requests: [], guestSkips: [], keptGuests: [] } }));
		const b = createDJ({ request: server.request('b'), storage, label: 'b', hasLLM: () => false, debounceMs: 0, locks: null });
		await b.refresh();
		expect(get(b.doc).options.mode).toBe('autofill');
		expect(get(b.doc).queue.upcoming).toEqual([]);
		expect(get(b.sync).notice).toMatch(/other device/);
	});
});
