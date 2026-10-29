// F2: the one global song preview. A 30 s Deezer clip plays through an <audio>
// element on this device and stops itself at 15 s. Starting another replaces
// it. While it plays, Spotify's volume can be lowered (Settings → "Lower
// Spotify while previewing") and is restored on stop, end, and page unload.
import { get, writable } from 'svelte/store';
import { PUBLIC_API_URL } from '$env/static/public';
import { access_token } from '../stores.js';
import { spotifyHeaders } from './spotifyHeaders.js';
import { duckPreview } from './settings.js';
import { getDJ } from './dj/instance.js';
import { say } from './toast.js';

export const PREVIEW_SECONDS = 15;
export const DUCK_PERCENT = 20;
// Longer than a player poll (5 s), so the polled volume has caught up with a restore.
const RESTORE_SETTLE_MS = 12_000;

/**
 * @typedef {{id: string, title: string, artists: string[], image?: string, isrc?: string | null}} PreviewSong
 * @typedef {{song: PreviewSong, pos: number, status: 'loading' | 'playing', ducked: boolean}} PreviewState
 */

/**
 * @param {{
 *   fetchUrl: (song: PreviewSong) => Promise<string>,
 *   makeAudio: (url: string) => {play: () => Promise<void>, pause: () => void, addEventListener: (e: string, f: () => void) => void},
 *   volume: {get: () => number | null, set: (percent: number, opts?: {keepalive?: boolean}) => Promise<boolean>},
 *   duck: () => boolean,
 *   now?: () => number
 * }} deps
 */
export function createPreview({ fetchUrl, makeAudio, volume, duck, now = Date.now }) {
	/** @type {import('svelte/store').Writable<PreviewState | null>} */
	const state = writable(null);
	let audio = null;
	let timer = null;
	let startedAt = 0;
	// Bumped by every start/stop, so a slow fetch or play() from a replaced preview is ignored.
	let run = 0;
	/** Spotify's volume from before ducking; non-null means it is currently lowered. */
	let saved = null;
	// The volume we last restored to. The polled player state lags a few seconds, so
	// right after a restore it can still read the ducked level (review F2-2).
	let restored = null;
	let restoredAt = 0;
	// Volume calls go out one at a time, so a restore can't overtake the duck it undoes.
	/** @type {Promise<any>} */
	let chain = Promise.resolve();
	const send = (percent, opts) => (chain = chain.then(() => volume.set(percent, opts)).catch(() => false));

	function endAudio() {
		clearInterval(timer);
		audio?.pause();
		audio = null;
	}

	/** @param {{keepalive?: boolean}} [opts] keepalive: the page is going away, so skip the queue. */
	function restore(opts = {}) {
		if (saved == null) return;
		const v = saved;
		saved = null;
		restored = v;
		restoredAt = now();
		if (opts.keepalive) volume.set(v, opts).catch(() => false);
		else send(v);
	}

	function stop(opts) {
		run++;
		endAudio();
		state.set(null);
		restore(opts);
	}

	async function duckNow(mine) {
		const polled = volume.get();
		if (polled == null) return;
		const v = restored != null && now() - restoredAt < RESTORE_SETTLE_MS ? restored : polled;
		saved = v;
		const ok = await send(DUCK_PERCENT);
		if (!ok) {
			if (saved === v) saved = null; // Spotify refused: nothing to restore
			return;
		}
		if (mine === run) state.update((s) => s && { ...s, ducked: true });
	}

	function tick() {
		const pos = Math.min(PREVIEW_SECONDS, (now() - startedAt) / 1000);
		if (pos >= PREVIEW_SECONDS) return stop();
		state.update((s) => s && { ...s, pos });
	}

	/** @param {PreviewSong} song */
	async function start(song) {
		if (get(state)?.song.id === song.id) return stop();
		const mine = ++run;
		endAudio(); // a replace keeps Spotify lowered; the final stop restores it
		state.set({ song, pos: 0, status: 'loading', ducked: saved != null });
		try {
			const el = makeAudio(await fetchUrl(song));
			if (mine !== run) return;
			audio = el;
			el.addEventListener('ended', stop);
			el.addEventListener('error', () => mine === run && (stop(), say("Couldn't play that preview.")));
			await el.play();
		} catch (e) {
			if (mine !== run) return;
			stop();
			say(e instanceof Error && e.message ? e.message : "Couldn't play that preview.");
			return;
		}
		if (mine !== run) return;
		startedAt = now();
		state.update((s) => s && { ...s, status: 'playing' });
		timer = setInterval(tick, 100);
		if (saved == null && duck()) duckNow(mine);
	}

	/** The page is hidden or closing: end the preview and put Spotify's volume back
	 *  with a request that outlives the page. */
	function unload() {
		stop({ keepalive: true });
	}

	return { subscribe: state.subscribe, start, stop, unload };
}

function realDeps() {
	return {
		async fetchUrl(song) {
			const p = new URLSearchParams();
			const dz = /^dz:(\d+)$/.exec(song.id);
			if (dz) p.set('dz', dz[1]);
			const isrc = song.isrc ?? (/^[A-Z]{2}[0-9A-Z]{10}$/.test(song.id) ? song.id : null);
			if (isrc) p.set('isrc', isrc);
			p.set('title', song.title);
			p.set('artist', song.artists?.[0] ?? '');
			let res;
			try {
				res = await fetch(`${PUBLIC_API_URL}/preview/?${p}`);
			} catch {
				throw new Error('Could not reach the server.');
			}
			if (res.status === 404) throw new Error('No preview for this song.');
			if (!res.ok) throw new Error("Previews aren't available right now.");
			return (await res.json()).url;
		},
		makeAudio: (url) => new Audio(url),
		duck: () => get(duckPreview) && !!get(access_token),
		volume: {
			// Only duck when Spotify is audibly playing and we know the volume to restore.
			get() {
				const dj = getDJ();
				const s = dj ? get(dj.player).state : null;
				return s?.active && s.is_playing ? s.device?.volume ?? null : null;
			},
			async set(percent, { keepalive = false } = {}) {
				try {
					const res = await fetch(`${PUBLIC_API_URL}/player/volume/`, {
						method: 'POST',
						headers: { 'Content-Type': 'application/json', ...spotifyHeaders() },
						body: JSON.stringify({ percent }),
						keepalive
					});
					return res.ok && !(await res.json()).error;
				} catch {
					return false;
				}
			}
		}
	};
}

export const preview = createPreview(realDeps());

if (typeof window !== 'undefined') {
	window.addEventListener('pagehide', () => preview.unload());
	// Phones often kill a background tab without pagehide.
	document.addEventListener('visibilitychange', () => document.visibilityState === 'hidden' && preview.unload());
}
