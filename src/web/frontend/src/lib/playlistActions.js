// Shared helper for adding tracks to a playlist, usable from any component.
import { get } from 'svelte/store';
import { PUBLIC_API_URL } from '$env/static/public';
import { access_token } from '../stores.js';

export async function addTracksToPlaylist(playlistId, trackIds) {
	const token = get(access_token);
	if (!token) return { error: 'auth' };
	if (!trackIds || trackIds.length === 0) return { ok: true, added: 0 };
	try {
		const res = await fetch(`${PUBLIC_API_URL}/spotify/add-to-playlist/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ playlist_id: playlistId, track_ids: trackIds, access_token: token }),
		});
		if (res.status === 401) return { error: 'auth' };
		const data = await res.json();
		return { ok: true, added: data.added, url: data.playlist_url };
	} catch {
		return { error: 'server' };
	}
}

// Save (or remove) a track from the user's Liked Songs.
export async function setTrackSaved(trackId, saved) {
	const token = get(access_token);
	if (!token) return { error: 'auth' };
	try {
		const res = await fetch(`${PUBLIC_API_URL}/spotify/save-track/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ track_ids: [trackId], remove: !saved, access_token: token }),
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
export async function getSavedStates(trackIds) {
	const token = get(access_token);
	if (!token || !trackIds || trackIds.length === 0) return {};
	try {
		const res = await fetch(
			`${PUBLIC_API_URL}/spotify/saved-contains/?access_token=${token}&ids=${trackIds.join(',')}`
		);
		if (!res.ok) return {};
		const data = await res.json();
		return data.saved || {};
	} catch {
		return {};
	}
}
