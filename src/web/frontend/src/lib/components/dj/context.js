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
		selected: writable(null)
	};
	setContext(KEY, ctx);
	return ctx;
}

/** Outside the DJ page (or in tests) there's nothing to link, so hand back inert stores. */
export function djContext() {
	return getContext(KEY) ?? { selected: writable(null) };
}

/** "Removed X." with Undo, in the app-wide toast. */
export function offerUndo(message, undo) {
	say(message, { undo });
}

/** A song as the selection stores it, from a pick, a queue entry or a TrackRef. */
export const asSong = (t) => ({ id: t.trackID ?? t.id, title: t.title, artists: t.artists ?? [], image: t.image ?? '' });
