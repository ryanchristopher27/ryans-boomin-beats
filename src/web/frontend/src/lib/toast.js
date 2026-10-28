import { writable } from 'svelte/store';

/** The one toast on screen, or null.
 * @type {import('svelte/store').Writable<{ id: number, text: string, undo?: () => void } | null>} */
export const toast = writable(null);

let timer;
let seq = 0;

/**
 * Show a short confirmation above the mini player. With `undo`, it gets an
 * Undo button and stays 4.5s instead of 2.2s (the handoff's timings).
 * @param {string} text
 * @param {{ undo?: () => void }} [opts]
 */
export function say(text, { undo } = {}) {
	clearTimeout(timer);
	const id = ++seq;
	toast.set({ id, text, undo });
	timer = setTimeout(() => toast.update((t) => (t?.id === id ? null : t)), undo ? 4500 : 2200);
}

export function dismiss() {
	clearTimeout(timer);
	toast.set(null);
}
