// One DJ engine per browser tab, shared by the DJ page and (W3) the mini player.
// It keeps running across in-app navigation, so a primary tab keeps driving.
import { browser } from '$app/environment';
import { get } from 'svelte/store';
import { createDJ } from './dj.js';
import { hasLLM, request } from './api.js';
import { hydrateToken } from '../spotifyAuth.js';
import { newMovesEverySong } from '../settings.js';

/** @type {ReturnType<typeof createDJ> | null} */
let dj = null;

export function getDJ() {
	if (!browser) return null;
	// A 401 mid-session means the Spotify token lapsed: refresh it now.
	dj ??= createDJ({ request, hasLLM, onUnauthorized: () => hydrateToken({ force: true }), everySong: () => get(newMovesEverySong) });
	return dj;
}
