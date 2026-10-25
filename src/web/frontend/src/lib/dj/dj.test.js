// The web DJ engine against an in-memory backend with the SY1 contract:
// version + If-Match, 409 with the current document, the primary role.
import { describe, expect, test } from 'vitest';
import { get } from 'svelte/store';
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
	return createDJ({ request: server.request(name), storage, label: name, hasLLM: () => false, debounceMs: 0 });
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

	test('a new tab adopts the shared queue and says so', async () => {
		const server = fakeServer();
		const a = tab(server, 'a');
		await a.refresh();
		a.setMode('autofill');
		await a.flush();

		const storage = memoryStorage();
		storage.set('dj_doc', JSON.stringify({ queue: { sent: [], upcoming: [{ id: 'x', trackID: 'old', title: 'old', artists: [], image: '', skipOnArrival: false }], requests: [], guestSkips: [], keptGuests: [] } }));
		const b = createDJ({ request: server.request('b'), storage, label: 'b', hasLLM: () => false, debounceMs: 0 });
		await b.refresh();
		expect(get(b.doc).options.mode).toBe('autofill');
		expect(get(b.doc).queue.upcoming).toEqual([]);
		expect(get(b.sync).notice).toMatch(/other device/);
	});
});
