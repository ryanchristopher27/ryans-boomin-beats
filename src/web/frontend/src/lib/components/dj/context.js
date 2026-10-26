// State the DJ page's widgets share but the engine doesn't own (W4): the
// selected song (linking: Song profile follows it) and the undo toast.
import { getContext, setContext } from 'svelte';
import { writable } from 'svelte/store';

const KEY = Symbol('dj-page');

/** @typedef {{id: string, title: string, artists: string[], image: string}} Song */
/** @typedef {{message: string, undo: () => void, id: number}} Toast */

export function provideDJContext() {
	const ctx = {
		/** @type {import('svelte/store').Writable<Song | null>} null = follow now playing */
		selected: writable(null),
		/** @type {import('svelte/store').Writable<Toast | null>} */
		toast: writable(null)
	};
	setContext(KEY, ctx);
	return ctx;
}

/** Outside the DJ page (or in tests) there's nothing to link, so hand back inert stores. */
export function djContext() {
	return getContext(KEY) ?? { selected: writable(null), toast: writable(null) };
}

let toastId = 0;

/** "Removed X. Undo" for 6 seconds. */
export function offerUndo(ctx, message, undo) {
	const id = ++toastId;
	ctx.toast.set({ message, undo, id });
	setTimeout(() => ctx.toast.update((t) => (t?.id === id ? null : t)), 6000);
}

/** A song as the selection stores it, from a pick, a queue entry or a TrackRef. */
export const asSong = (t) => ({ id: t.trackID ?? t.id, title: t.title, artists: t.artists ?? [], image: t.image ?? '' });
