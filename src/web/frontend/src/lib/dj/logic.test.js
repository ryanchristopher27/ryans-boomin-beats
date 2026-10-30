// Ports of the iOS BoominBeatsTests (QueueLogicTests + SyncTests), so both
// clients' queue logic is held to the same cases.
import { describe, expect, test } from 'vitest';
import { arrival, autopilotCandidates, detectRequests, docsEqual, emptyDoc, goalKey, merge, mergeMove, reconciled, roundMoves } from './logic.js';

const item = (id, skip = false) => ({ id: `e-${id}-${Math.random()}`, trackID: id, title: id, artists: ['A'], image: '', skipOnArrival: skip });
const ids = (items) => items.map((i) => i.trackID);

describe('arrival', () => {
	test('drops everything up to the arrived track', () => {
		const { remaining, arrived } = arrival('b', [item('a'), item('b'), item('c')]);
		expect(arrived.trackID).toBe('b');
		expect(ids(remaining)).toEqual(['c']);
	});
	test('of an unknown track changes nothing', () => {
		const { remaining, arrived } = arrival('guest', [item('a'), item('b')]);
		expect(arrived).toBeNull();
		expect(ids(remaining)).toEqual(['a', 'b']);
	});
	test('matches the first copy of a duplicate', () => {
		const { remaining, arrived } = arrival('x', [item('x', true), item('y'), item('x')]);
		expect(arrived.skipOnArrival).toBe(true);
		expect(ids(remaining)).toEqual(['y', 'x']);
	});
});

describe('reconcile', () => {
	test('drops the played prefix', () => {
		expect(ids(reconciled([item('a'), item('b'), item('c')], ['b', 'c', 'ctx1']))).toEqual(['b', 'c']);
	});
	test('drops everything when nothing is visible', () => {
		const full = Array.from({ length: 20 }, (_, i) => `ctx${i}`);
		expect(reconciled([item('a'), item('b')], full)).toEqual([]);
	});
	test('matches duplicates in order', () => {
		expect(ids(reconciled([item('x'), item('y'), item('x')], ['x', 'y', 'x']))).toEqual(['x', 'y', 'x']);
	});
	test('drops a missing trailing track when the view is not full', () => {
		expect(ids(reconciled([item('a'), item('b'), item('c')], ['a', 'b']))).toEqual(['a', 'b']);
	});
	test('keeps tracks past a full window', () => {
		const view = ['a', ...Array.from({ length: 18 }, (_, i) => `guest${i}`), 'b'];
		expect(ids(reconciled([item('a'), item('b'), item('c'), item('d')], view))).toEqual(['a', 'b', 'c', 'd']);
	});
});

describe('guest requests', () => {
	const detect = (previous, current, { app = [], ignoring = [], insertions = true } = {}) =>
		detectRequests({ previous, current, appIDs: new Set(app), ignoring: new Set(ignoring), insertionsAllowed: insertions }).map((i) => current[i]);

	test('a wedged track ahead of an app track is a request', () => {
		expect(detect(null, ['g', 'next', 'c1', 'c2'], { app: ['next'] })).toEqual(['g']);
	});
	test('a track after the last app track is not wedged', () => {
		expect(detect(null, ['next', 'g', 'c1'], { app: ['next'] })).toEqual([]);
	});
	test('a mid-view insertion is a request on the next poll', () => {
		expect(detect(['next', 'c1', 'c2', 'c3'], ['next', 'g', 'c1', 'c2', 'c3'], { app: ['next'] })).toEqual(['g']);
	});
	test('context sliding in at the tail is not a request', () => {
		expect(detect(['c1', 'c2', 'c3'], ['c2', 'c3', 'c4'])).toEqual([]);
	});
	test('Smart Shuffle disables the insertion rule', () => {
		expect(detect(['next', 'c1', 'c2'], ['next', 'rec', 'c1', 'c2'], { app: ['next'], insertions: false })).toEqual([]);
	});
	test('known requests are not flagged again', () => {
		expect(detect(null, ['g', 'next'], { app: ['next'], ignoring: ['g'] })).toEqual([]);
	});
	test('a duplicate request is reported once', () => {
		expect(detect(null, ['g', 'g', 'next'], { app: ['next'] })).toEqual(['g']);
	});
});

describe('autopilot', () => {
	const move = (name, picks) => ({ move: name, tracks: picks.map((id) => ({ id, title: id, artists: ['A'], image: '', reason: '' })) });
	const moves = [move('hold', ['h1', 'h2']), move('lift', ['l1', 'l2']), move('drop', ['d1']), move('pivot', ['p1', 'p2']), move('curveball', ['c1'])];
	const pickIds = (p) => p.map((x) => x.id);

	test('safe stays on hold/lift/drop and interleaves', () => {
		expect(pickIds(autopilotCandidates(moves, 0.1, new Set()))).toEqual(['h1', 'l1', 'd1', 'h2', 'l2']);
	});
	test('bold leads with pivot and curveball', () => {
		expect(pickIds(autopilotCandidates(moves, 0.9, new Set())).slice(0, 4)).toEqual(['p1', 'c1', 'l1', 'h1']);
	});
	test("a goal's move leads with all its picks", () => {
		const picks = autopilotCandidates([move('toward', ['t1', 't2']), ...moves], 0.1, new Set(['t2']), 'toward');
		expect(pickIds(picks).slice(0, 3)).toEqual(['t1', 'h1', 'l1']);
	});
	test('skips already queued tracks', () => {
		expect(autopilotCandidates(moves, 0.1, new Set(['h1', 'l1']))[0].id).toBe('d1');
	});
	test('goal cache key moves with arc progress', () => {
		const now = Date.now();
		const arc = { kind: 'arc', shape: 'build', minutes: 30, startedAt: new Date(now).toISOString() };
		const early = goalKey(arc, now);
		expect(goalKey(arc, now + 6 * 60000)).not.toBe(early);
		expect(goalKey(null)).toBe('none');
		expect(goalKey({ kind: 'drift' })).toBe('drift');
	});
});

describe('sync merge', () => {
	test("keeps both devices' edits to different fields", () => {
		const base = emptyDoc();
		base.queue.upcoming = [item('a'), item('b')];
		const local = structuredClone(base);
		local.queue.upcoming.reverse();
		const server = structuredClone(base);
		server.options.mode = 'driver';
		const merged = merge(base, local, server);
		expect(ids(merged.queue.upcoming)).toEqual(['b', 'a']);
		expect(merged.options.mode).toBe('driver');
	});
	test('prefers this device when both changed the same field', () => {
		const base = emptyDoc();
		const local = structuredClone(base);
		local.options.adventurousness = 0.9;
		const server = structuredClone(base);
		server.options.adventurousness = 0.1;
		expect(merge(base, local, server).options.adventurousness).toBe(0.9);
	});
	test("the server's filled-in defaults don't count as a change", () => {
		const local = emptyDoc();
		local.queue.upcoming = [{ id: 'e', trackID: 't', title: 't', artists: [], image: '', skipOnArrival: false }];
		const server = structuredClone(local);
		server.queue.upcoming[0] = { addedByDJ: null, ...server.queue.upcoming[0] };
		expect(docsEqual(local, server)).toBe(true);
	});
	test('takes server fields this device did not touch', () => {
		const base = emptyDoc();
		const server = structuredClone(base);
		server.recent = [{ id: 'x', title: 'x', artists: [], image: '' }];
		expect(merge(base, base, server)).toEqual(server);
	});
});

describe("tonight's set", () => {
	const song = (id, extra = {}) => ({ id, title: id, duration_ms: 180000, ...extra });
	test('logs each song once, and a long gap starts a new set', async () => {
		const { logPlay, SET_GAP_MS } = await import('./logic.js');
		let log = logPlay([], song('a'), 0);
		log = logPlay(log, song('a'), 1000); // still the same song
		log = logPlay(log, song('b'), 200000);
		expect(log.map((e) => e.id)).toEqual(['a', 'b']);
		log = logPlay(log, song('c'), 200000 + SET_GAP_MS + 1);
		expect(log.map((e) => e.id)).toEqual(['c']);
	});
	test('stats count time, DJ picks and guest requests', async () => {
		const { setStats } = await import('./logic.js');
		expect(setStats([song('a', { dj: true }), song('b', { guest: true }), song('c')])).toEqual({ songs: 3, minutes: 9, djPicks: 1, requests: 1 });
	});
});

describe('parallel rounds', () => {
	test('roundMoves mirrors the backend: a goal move first, only when the goal makes one', () => {
		expect(roundMoves(null)).toEqual(['hold', 'lift', 'drop', 'pivot', 'curveball']);
		expect(roundMoves({ kind: 'drift' })[0]).toBe('drift');
		expect(roundMoves({ kind: 'arc' })[0]).toBe('toward');
		expect(roundMoves({ kind: 'destination', destination: '  ' })).toHaveLength(5);
	});

	test('mergeMove keeps display order and drops songs another move has', () => {
		const order = ['hold', 'lift', 'drop'];
		const t = (id) => ({ id, title: id });
		let b = mergeMove([], { move: 'drop', tracks: [t('a')] }, order);
		b = mergeMove(b, { move: 'hold', tracks: [t('a'), t('b')] }, order);
		expect(b.map((m) => [m.move, m.tracks.map((x) => x.id)])).toEqual([['hold', ['b']], ['drop', ['a']]]);
	});
});
