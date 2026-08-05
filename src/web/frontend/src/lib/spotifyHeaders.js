// The Spotify user token travels as a bearer header rather than an
// `access_token` query param or body field — query strings are recorded in
// access logs, proxies, and hosting-platform request logs, where they can't be
// scrubbed. See backend/services/spotify_auth.py.
import { get } from 'svelte/store';
import { access_token } from '../stores.js';

/** @returns {Record<string, string>} */
export function spotifyHeaders() {
	const token = get(access_token);
	return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Bearer header built from an explicit token (for callers holding a local copy). */
/** @returns {Record<string, string>} */
export function bearer(token) {
	return token ? { Authorization: `Bearer ${token}` } : {};
}
