import { beforeEach, describe, expect, test, vi } from 'vitest';
import { get } from 'svelte/store';

describe('settings', () => {
	beforeEach(() => {
		vi.resetModules();
		const data = {};
		vi.stubGlobal('localStorage', { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => (data[k] = String(v)), removeItem: (k) => delete data[k] });
	});

	test('defaults follow the handoff', async () => {
		const s = await import('./settings.js');
		expect([get(s.textScale), get(s.compactRows), get(s.playbackMotion)]).toEqual([0.9, false, true]);
	});

	test('a saved choice survives a reload, a junk value does not', async () => {
		localStorage.setItem('bb-zoom', '1.1');
		localStorage.setItem('bb-compact', '"yes"');
		const s = await import('./settings.js');
		expect(get(s.textScale)).toBe(1.1);
		expect(get(s.compactRows)).toBe(false);
	});

	test('reset restores every default', async () => {
		const s = await import('./settings.js');
		s.textScale.set(1.2);
		s.playbackMotion.set(false);
		s.resetSettings();
		expect([get(s.textScale), get(s.playbackMotion)]).toEqual([0.9, true]);
	});
});

describe('clean filter', () => {
	test('hides explicit songs only when Clean only is on', async () => {
		const { cleanFilter } = await import('./clean.js');
		const songs = [{ spotify: { id: 'a', explicit: true } }, { spotify: { id: 'b', explicit: false } }];
		expect(cleanFilter(songs, false)).toEqual({ shown: songs, hidden: 0 });
		expect(cleanFilter(songs, true)).toEqual({ shown: [songs[1]], hidden: 1 });
	});
});

describe('onboarding', () => {
	test('a fresh browser has not decided yet; a saved step comes back', async () => {
		let s = await import('./onboarding.js');
		expect(get(s.onboarding)).toBe(null);
		localStorage.setItem('bb-onboarding', '2');
		vi.resetModules();
		s = await import('./onboarding.js');
		expect(get(s.onboarding)).toBe(2);
	});
});
