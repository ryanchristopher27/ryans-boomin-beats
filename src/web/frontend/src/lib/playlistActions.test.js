// Choose-time resolve for playlist and search results (plan Q3): keys resolve
// once, Spotify ids pass through, misses drop out. fetch is faked.
import { afterEach, describe, expect, test, vi } from 'vitest';
import { access_token } from '../stores.js';
import { rememberSongs, resolvedId, toSpotifyIds } from './playlistActions.js';

vi.mock('$env/static/public', () => ({ PUBLIC_API_URL: 'http://api' }));

describe('toSpotifyIds', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	test('resolves keys once, passes Spotify ids through, drops misses', async () => {
		access_token.set('tok');
		const calls = [];
		vi.stubGlobal('fetch', vi.fn(async (url, opts) => {
			const { songs } = JSON.parse(opts.body);
			calls.push(songs);
			return { ok: true, status: 200, json: async () => ({ tracks: songs.map((s) => (s.isrc === 'USUM71210785' ? { id: '2Kj9qQ6xuY4Rr9u3R6tWex' } : null)) }) };
		}));
		rememberSongs([
			{ id: 'USUM71210785', isrc: 'USUM71210785', title: 'Money Trees', artists: ['Kendrick Lamar'] },
			{ id: 'dz:42', isrc: null, title: 'Gone', artists: ['Nobody'] }
		]);
		const spotify = '4uLU6hMCjMI75M1A2tKUQC';
		const r = await toSpotifyIds(['USUM71210785', spotify, 'dz:42']);
		expect(r).toEqual({ ids: ['2Kj9qQ6xuY4Rr9u3R6tWex', spotify], missing: 1 });
		expect(calls).toHaveLength(1);
		expect(calls[0]).toEqual([
			{ isrc: 'USUM71210785', title: 'Money Trees', artist: 'Kendrick Lamar' },
			{ isrc: null, title: 'Gone', artist: 'Nobody' }
		]);
		await toSpotifyIds(['USUM71210785']); // already known: no new lookup
		expect(calls).toHaveLength(1);
		expect(resolvedId('USUM71210785')).toBe('2Kj9qQ6xuY4Rr9u3R6tWex');
	});

	test('signed out returns an auth error without calling the server', async () => {
		access_token.set('');
		const fetch = vi.fn();
		vi.stubGlobal('fetch', fetch);
		expect((await toSpotifyIds(['USAAA0000009'])).error).toBe('auth');
		expect(fetch).not.toHaveBeenCalled();
	});
});
