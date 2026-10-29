import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$env/static/public', () => ({ PUBLIC_API_URL: 'http://api' }));
vi.mock('./dj/instance.js', () => ({ getDJ: () => null }));
vi.mock('./toast.js', () => ({ say: vi.fn() }));

const { createPreview, PREVIEW_SECONDS } = await import('./preview.js');
const { say } = await import('./toast.js');

const song = (id) => ({ id, title: id, artists: ['A'] });

function setup({ vol = 80, duck = true, volOk = true, playFails = false } = {}) {
	const calls = [];
	const audios = [];
	const p = createPreview({
		fetchUrl: async (s) => `https://cdn/${s.id}.mp3`,
		makeAudio: (url) => {
			const a = { url, paused: false, handlers: {}, play: async () => { if (playFails) throw new Error('blocked'); }, pause() { a.paused = true; }, addEventListener(e, f) { a.handlers[e] = f; } };
			audios.push(a);
			return a;
		},
		volume: { get: () => vol, set: async (percent, opts) => (calls.push([percent, !!opts?.keepalive]), volOk) },
		duck: () => duck
	});
	return { p, calls, audios };
}

describe('preview', () => {
	beforeEach(() => vi.useFakeTimers());
	afterEach(() => vi.useRealTimers());

	test('plays, ticks, and stops itself at 15 s, restoring the volume', async () => {
		const { p, calls, audios } = setup();
		await p.start(song('a'));
		expect(get(p)).toMatchObject({ status: 'playing', pos: 0 });
		await vi.advanceTimersByTimeAsync(5000);
		expect(get(p).pos).toBeCloseTo(5, 0);
		expect(get(p).ducked).toBe(true);
		await vi.advanceTimersByTimeAsync(PREVIEW_SECONDS * 1000);
		expect(get(p)).toBeNull();
		expect(audios[0].paused).toBe(true);
		expect(calls).toEqual([[20, false], [80, false]]);
	});

	test('stop restores; stopping twice restores once', async () => {
		const { p, calls } = setup();
		await p.start(song('a'));
		await vi.advanceTimersByTimeAsync(10);
		p.stop();
		p.stop();
		await vi.advanceTimersByTimeAsync(10);
		expect(calls).toEqual([[20, false], [80, false]]);
	});

	test('a new preview replaces the old and the original volume comes back once', async () => {
		const { p, calls, audios } = setup();
		await p.start(song('a'));
		await vi.advanceTimersByTimeAsync(10);
		await p.start(song('b'));
		await vi.advanceTimersByTimeAsync(10);
		expect(audios[0].paused).toBe(true);
		expect(get(p).song.id).toBe('b');
		expect(get(p).ducked).toBe(true);
		p.stop();
		await vi.advanceTimersByTimeAsync(10);
		expect(calls).toEqual([[20, false], [80, false]]);
	});

	test('starting the same song again stops it', async () => {
		const { p } = setup();
		await p.start(song('a'));
		await p.start(song('a'));
		expect(get(p)).toBeNull();
	});

	test('the natural end of the clip stops and restores', async () => {
		const { p, calls, audios } = setup();
		await p.start(song('a'));
		await vi.advanceTimersByTimeAsync(10);
		audios[0].handlers.ended();
		await vi.advanceTimersByTimeAsync(10);
		expect(get(p)).toBeNull();
		expect(calls.at(-1)).toEqual([80, false]);
	});

	test('page unload restores with keepalive', async () => {
		const { p, calls } = setup();
		await p.start(song('a'));
		await vi.advanceTimersByTimeAsync(10);
		p.unload();
		await vi.advanceTimersByTimeAsync(10);
		expect(calls.at(-1)).toEqual([80, true]);
		p.unload();
		await vi.advanceTimersByTimeAsync(10);
		expect(calls).toHaveLength(2);
	});

	test('no ducking when off, when the volume is unknown, or when Spotify refuses', async () => {
		for (const opts of [{ duck: false }, { vol: null }, { volOk: false }]) {
			const { p, calls } = setup(opts);
			await p.start(song('a'));
			await vi.advanceTimersByTimeAsync(10);
			p.stop();
			await vi.advanceTimersByTimeAsync(10);
			expect(calls.filter(([v]) => v !== 20)).toEqual([]);
			expect(get(p)).toBeNull();
		}
	});

	test('a blocked play() clears the preview, says so, and never ducks', async () => {
		const { p, calls } = setup({ playFails: true });
		await p.start(song('a'));
		expect(get(p)).toBeNull();
		expect(say).toHaveBeenCalledWith('blocked');
		expect(calls).toEqual([]);
	});
});
