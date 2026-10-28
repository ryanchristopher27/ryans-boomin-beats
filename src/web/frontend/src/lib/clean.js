// Settings → Clean only is the DJ's synced `clean` option; playlists and
// recommendations hide explicit songs by it too (F1).
import { derived, readable } from 'svelte/store';
import { getDJ } from './dj/instance.js';

/** @type {import('svelte/store').Readable<boolean>} */
export const cleanOnly = derived(getDJ()?.doc ?? readable(null), (d) => !!d?.options?.clean);

/** Songs to show under Clean only, and how many were hidden. */
export function cleanFilter(songs, clean) {
	if (!clean) return { shown: songs, hidden: 0 };
	const shown = songs.filter((s) => !(s.spotify ?? s).explicit);
	return { shown, hidden: songs.length - shown.length };
}
