// Shared helper for adding tracks to a playlist, usable from any component.
import { get } from 'svelte/store';
import { PUBLIC_API_URL } from '$env/static/public';
import { access_token } from '../stores.js';
import { bearer } from './spotifyHeaders.js';

// --- Choose-time Spotify resolve (plan Q3) ---
// Search and playlist results come from Deezer, so their `spotify.id` is a key
// (an ISRC, or `dz:<id>`), not a Spotify id. Every action that needs a real id
// (add to playlist, save, queue) goes through toSpotifyIds(), which spends the
// one Spotify search a song costs, once, and remembers the answer.

/** key -> {isrc, title, artist} for songs shown from Deezer. */
const known = new Map();
/** key -> Spotify id, or null when Spotify doesn't have it. */
const resolved = new Map();

const SPOTIFY_ID = /^[0-9A-Za-z]{22}$/;

/** Register shown songs so their keys can be resolved later. */
export function rememberSongs(tracks) {
	for (const t of tracks ?? []) {
		if (t?.id && !SPOTIFY_ID.test(t.id)) known.set(t.id, { isrc: t.isrc ?? null, title: t.title, artist: t.artists?.[0] ?? '' });
	}
}

export function resolvedId(key) {
	return SPOTIFY_ID.test(key) ? key : resolved.get(key) ?? null;
}

/**
 * Spotify ids for these keys, in order; Spotify ids pass straight through.
 * Songs Spotify doesn't have are dropped (and counted in `missing`).
 * @returns {Promise<{ids: string[], missing: number, error?: string}>}
 */
export async function toSpotifyIds(keys) {
	const token = get(access_token);
	if (!token) return { ids: [], missing: 0, error: 'auth' };
	const todo = [...new Set(keys.filter((k) => !SPOTIFY_ID.test(k) && !resolved.has(k)))];
	for (let i = 0; i < todo.length; i += 50) {
		const batch = todo.slice(i, i + 50);
		const songs = batch.map((k) => known.get(k) ?? { isrc: /^[A-Z]{2}[0-9A-Z]{10}$/.test(k) ? k : null, title: '', artist: '' });
		try {
			const res = await fetch(`${PUBLIC_API_URL}/tracks/resolve/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', ...bearer(token) },
				body: JSON.stringify({ songs })
			});
			if (res.status === 401) return { ids: [], missing: 0, error: 'auth' };
			if (!res.ok) return { ids: [], missing: 0, error: 'server' };
			const { tracks } = await res.json();
			batch.forEach((k, j) => resolved.set(k, tracks[j]?.id ?? null));
		} catch {
			return { ids: [], missing: 0, error: 'server' };
		}
	}
	const ids = keys.map(resolvedId);
	return { ids: ids.filter(Boolean), missing: ids.filter((x) => !x).length };
}

export async function addTracksToPlaylist(playlistId, keys) {
	const token = get(access_token);
	if (!token) return { error: 'auth' };
	if (!keys || keys.length === 0) return { ok: true, added: 0 };
	const { ids: trackIds, missing, error } = await toSpotifyIds(keys);
	if (error) return { error };
	if (!trackIds.length) return { ok: true, added: 0, missing };
	try {
		const res = await fetch(`${PUBLIC_API_URL}/spotify/add-to-playlist/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', ...bearer(token) },
			body: JSON.stringify({ playlist_id: playlistId, track_ids: trackIds }),
		});
		if (res.status === 401) return { error: 'auth' };
		const data = await res.json();
		return { ok: true, added: data.added, url: data.playlist_url, missing };
	} catch {
		return { error: 'server' };
	}
}

// Save (or remove) a track from the user's Liked Songs.
export async function setTrackSaved(key, saved) {
	const token = get(access_token);
	if (!token) return { error: 'auth' };
	const { ids, error } = await toSpotifyIds([key]);
	if (error) return { error };
	if (!ids.length) return { error: 'not_on_spotify' };
	const trackId = ids[0];
	try {
		const res = await fetch(`${PUBLIC_API_URL}/spotify/save-track/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', ...bearer(token) },
			body: JSON.stringify({ track_ids: [trackId], remove: !saved }),
		});
		if (res.status === 403) return { error: 'reconnect' };
		if (res.status === 401) return { error: 'auth' };
		if (!res.ok) return { error: 'server' };
		return { ok: true };
	} catch {
		return { error: 'server' };
	}
}

// Returns a map of { trackId: bool } for which tracks are in Liked Songs.
// Only songs already resolved are checked: looking up a whole result list just
// to draw hearts would spend the searches Q3 exists to save. Keys come back
// mapped from their Spotify ids.
export async function getSavedStates(keys) {
	const token = get(access_token);
	const byId = new Map((keys ?? []).map((k) => [resolvedId(k), k]).filter(([id]) => id));
	const trackIds = [...byId.keys()];
	if (!token || trackIds.length === 0) return {};
	try {
		const res = await fetch(
			`${PUBLIC_API_URL}/spotify/saved-contains/?ids=${trackIds.join(',')}`,
			{ headers: bearer(token) }
		);
		if (!res.ok) return {};
		const data = await res.json();
		return Object.fromEntries(Object.entries(data.saved || {}).map(([id, v]) => [byId.get(id) ?? id, v]));
	} catch {
		return {};
	}
}
