// State the DJ page's widgets share but the engine doesn't own (W4): the
// selected song (linking: Song profile follows it).
import { getContext, setContext } from 'svelte';
import { writable } from 'svelte/store';
import { say } from '$lib/toast.js';

const KEY = Symbol('dj-page');

/** @typedef {{id: string, title: string, artists: string[], image: string}} Song */

export function provideDJContext() {
	const ctx = {
		/** @type {import('svelte/store').Writable<Song | null>} null = follow now playing */
		selected: writable(null),
		/** The move a Compass key just added from; its card flashes (F3g). */
		flash: writable(/** @type {string | null} */ (null)),
		/** The page's layout, for the DJ chat: set by the DJ page. */
		page: /** @type {{preset: () => string, items: () => any[], choose: (p: string) => void, apply: (items: any[]) => void} | null} */ (null)
	};
	setContext(KEY, ctx);
	return ctx;
}

/** Outside the DJ page (or in tests) there's nothing to link, so hand back inert stores. */
export function djContext() {
	return getContext(KEY) ?? { selected: writable(null), flash: writable(null), page: null };
}

/** "Removed X." with Undo, in the app-wide toast. */
export function offerUndo(message, undo) {
	say(message, { undo });
}

/** A song as the selection stores it, from a pick, a queue entry or a TrackRef. */
export const asSong = (t) => ({ id: t.trackID ?? t.id, title: t.title, artists: t.artists ?? [], image: t.image ?? '' });
