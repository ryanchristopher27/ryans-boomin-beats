// Pure logic for the ⌘K command palette: what it lists and how the keyboard moves.

/** Go-to targets. `href` null means "open Settings". */
export const PAGES = [
	{ label: 'Explore', href: '/', icon: 'compass' },
	{ label: 'Builder', href: '/playlist-builder/', icon: 'wand' },
	{ label: 'DJ', href: '/dj/', icon: 'disc' },
	{ label: 'Profile', href: '/profile/', icon: 'user' },
	{ label: 'Settings', href: null, icon: 'gear' }
];

/** Search spends a request per call (Deezer/Last.fm), so wait for 3+ characters. */
export const MIN_QUERY = 3;
export const RECENT_LIMIT = 6;

/** Same song by Spotify id, ISRC, or (for Deezer-keyed rows) title + first artist. */
function songKey(s) {
	return s.isrc || s.id || `${s.title}|${s.artists?.[0] ?? ''}`.toLowerCase();
}

/** Recent songs, newest first: the explore trail, then the DJ's recently played. Deduped. */
export function recentSongs(trail = [], djRecent = [], limit = RECENT_LIMIT) {
	const seen = new Set();
	const out = [];
	for (const s of [...[...trail].reverse(), ...djRecent]) {
		if (!s?.title || seen.has(songKey(s))) continue;
		seen.add(songKey(s));
		out.push(s);
		if (out.length >= limit) break;
	}
	return out;
}

/** Pages whose label contains the query (all of them when it is empty). */
export function matchPages(query, pages = PAGES) {
	const q = query.trim().toLowerCase();
	return q ? pages.filter((p) => p.label.toLowerCase().includes(q)) : pages;
}

/**
 * The flat, selectable list: songs first, then Go to. An empty query shows recents;
 * a short query shows only page matches; 3+ characters shows the search results.
 * @returns {({ kind: 'song', song: any } | { kind: 'page', page: any })[]}
 */
export function buildItems(query, { recent = [], results = [] } = {}) {
	const q = query.trim();
	const songs = !q ? recent : q.length >= MIN_QUERY ? results : [];
	return [...songs.map((song) => ({ kind: 'song', song })), ...matchPages(q).map((page) => ({ kind: 'page', page }))];
}

/** Next selected index for a key; wraps at both ends. Returns the current index for other keys. */
export function moveSelection(index, key, count) {
	if (!count) return -1;
	if (key === 'ArrowDown') return (index + 1) % count;
	if (key === 'ArrowUp') return (index - 1 + count) % count;
	return index;
}

/** The announced count, e.g. "3 songs, 2 pages". */
export function countLabel(items) {
	const songs = items.filter((i) => i.kind === 'song').length;
	const pages = items.length - songs;
	const part = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`;
	return items.length ? [songs && part(songs, 'song'), pages && part(pages, 'page')].filter(Boolean).join(', ') : 'No results';
}
