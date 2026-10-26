// Token refresh (review C2): one refresh at a time, and only a rejected refresh
// token signs the user out. localStorage and fetch are faked.
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { get } from 'svelte/store';
import { access_token } from '../stores.js';
import { hydrateToken } from './spotifyAuth.js';

function fakeStorage() {
	const m = new Map();
	return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) };
}

describe('hydrateToken', () => {
	beforeEach(() => {
		vi.stubGlobal('localStorage', fakeStorage());
		localStorage.setItem('spotify_access_token', 'old');
		localStorage.setItem('spotify_refresh_token', 'r1');
		localStorage.setItem('spotify_expires_at', String(Date.now() - 1000)); // expired
	});
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	test('concurrent callers share one refresh', async () => {
		const fetch = vi.fn(async () => ({ json: async () => ({ access_token: 'new', refresh_token: 'r2', expires_in: 3600 }) }));
		vi.stubGlobal('fetch', fetch);
		const results = await Promise.all([hydrateToken(), hydrateToken({ force: true }), hydrateToken()]);
		expect(results).toEqual([true, true, true]);
		expect(fetch).toHaveBeenCalledTimes(1);
		expect(get(access_token)).toBe('new');
		expect(localStorage.getItem('spotify_refresh_token')).toBe('r2');
	});

	test('a network failure keeps the session', async () => {
		vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('offline'); }));
		expect(await hydrateToken()).toBe(false);
		expect(localStorage.getItem('spotify_refresh_token')).toBe('r1');
	});

	test('a rejected refresh token signs out', async () => {
		vi.stubGlobal('fetch', vi.fn(async () => ({ json: async () => ({ error: 'invalid_grant' }) })));
		expect(await hydrateToken()).toBe(false);
		expect(localStorage.getItem('spotify_refresh_token')).toBeNull();
		expect(get(access_token)).toBe('');
	});

	test('a fresh token is used without refreshing', async () => {
		localStorage.setItem('spotify_expires_at', String(Date.now() + 30 * 60 * 1000));
		const fetch = vi.fn();
		vi.stubGlobal('fetch', fetch);
		expect(await hydrateToken()).toBe(true);
		expect(fetch).not.toHaveBeenCalled();
	});
});
