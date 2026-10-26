// One DJ engine per browser tab, shared by the DJ page and (W3) the mini player.
// It keeps running across in-app navigation, so a primary tab keeps driving.
import { browser } from '$app/environment';
import { createDJ } from './dj.js';
import { hasLLM, request } from './api.js';

/** @type {ReturnType<typeof createDJ> | null} */
let dj = null;

export function getDJ() {
	if (!browser) return null;
	dj ??= createDJ({ request, hasLLM });
	return dj;
}
