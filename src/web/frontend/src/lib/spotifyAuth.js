// Shared Spotify auth: token storage, refresh, and app-wide hydration.
// The Profile page owns the PKCE login flow; everything else just needs the
// access_token populated, which hydrateToken() handles on app load.
import { access_token } from '../stores.js';

export const CLIENT_ID = 'a700071d47504ba68082a5a59d2b0bc0';
export const AUTHORIZE_ENDPOINT = 'https://accounts.spotify.com/authorize';
export const TOKEN_ENDPOINT = 'https://accounts.spotify.com/api/token';
export const REDIRECT_URI = 'http://127.0.0.1:5173/profile';
// user-read-playback-state is required to list devices and read player state.
// Without it /me/player and /me/player/devices return 401 "Permissions missing",
// so queueing can only fail with an opaque 404 and never explain why.
// NOTE: adding a scope requires a full logout/login — a refresh preserves the
// scope set from the original grant.
export const SCOPES =
	'user-top-read playlist-read-private playlist-modify-private playlist-modify-public user-modify-playback-state user-read-playback-state user-library-read user-library-modify user-read-recently-played';

// --- PKCE helpers (login only) ---
function generateCodeVerifier(length = 128) {
	const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
	const array = new Uint8Array(length);
	crypto.getRandomValues(array);
	return Array.from(array).map((b) => chars[b % chars.length]).join('');
}

async function generateCodeChallenge(verifier) {
	const data = new TextEncoder().encode(verifier);
	const digest = await crypto.subtle.digest('SHA-256', data);
	return btoa(String.fromCharCode(...new Uint8Array(digest)))
		.replace(/\+/g, '-')
		.replace(/\//g, '_')
		.replace(/=+$/, '');
}

// --- Token storage ---
export function saveTokens(tokenData) {
	localStorage.setItem('spotify_access_token', tokenData.access_token);
	if (tokenData.refresh_token) {
		localStorage.setItem('spotify_refresh_token', tokenData.refresh_token);
	}
	localStorage.setItem('spotify_expires_at', Date.now() + tokenData.expires_in * 1000);
}

export function loadStoredToken() {
	const accessToken = localStorage.getItem('spotify_access_token');
	const refreshToken = localStorage.getItem('spotify_refresh_token');
	const expiresAt = parseInt(localStorage.getItem('spotify_expires_at') || '0');
	if (!accessToken) return null;
	return { accessToken, refreshToken, expiresAt };
}

export function clearStoredTokens() {
	localStorage.removeItem('spotify_access_token');
	localStorage.removeItem('spotify_refresh_token');
	localStorage.removeItem('spotify_expires_at');
}

// --- Token exchange / refresh ---
export async function exchangeCodeForToken(code, verifier) {
	const res = await fetch(TOKEN_ENDPOINT, {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
		body: new URLSearchParams({
			grant_type: 'authorization_code',
			code,
			redirect_uri: REDIRECT_URI,
			client_id: CLIENT_ID,
			code_verifier: verifier,
		}),
	});
	return res.json();
}

export async function refreshAccessToken(refreshToken) {
	const res = await fetch(TOKEN_ENDPOINT, {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
		body: new URLSearchParams({
			grant_type: 'refresh_token',
			refresh_token: refreshToken,
			client_id: CLIENT_ID,
		}),
	});
	return res.json();
}

/**
 * Hydrate the access_token store from storage on app load, refreshing if
 * expired. Safe to call on every page. Returns true if a valid token is set.
 */
// Refresh this long before expiry, so a page left open (the DJ, all night)
// never sends an expired token (review C2).
const REFRESH_MARGIN_MS = 2 * 60 * 1000;

let inflight = null;

/**
 * One refresh at a time: Spotify rotates refresh tokens, so two concurrent
 * refreshes (page load, the keep-fresh timer, a 401) would spend the same token
 * twice, and the loser's rejection used to sign the user out.
 */
export function hydrateToken({ force = false } = {}) {
	inflight ??= hydrate(force).finally(() => (inflight = null));
	return inflight;
}

async function hydrate(force) {
	if (typeof localStorage === 'undefined') return false;
	const stored = loadStoredToken();
	if (!stored) return false;

	if (!force && Date.now() < stored.expiresAt - REFRESH_MARGIN_MS) {
		access_token.set(stored.accessToken);
		return true;
	}

	if (stored.refreshToken) {
		let data;
		try {
			data = await refreshAccessToken(stored.refreshToken);
		} catch {
			// Offline or Spotify unreachable: keep the session and try again later.
			return false;
		}
		if (data.access_token) {
			saveTokens(data);
			access_token.set(data.access_token);
			return true;
		}
		// Only a rejected refresh token ends the session; anything else is transient.
		if (data.error !== 'invalid_grant') return false;
	}

	clearStoredTokens();
	access_token.set('');
	return false;
}

/** Kick off the PKCE login redirect. */
export async function beginLogin() {
	if (typeof window === 'undefined') return;
	const verifier = generateCodeVerifier();
	const challenge = await generateCodeChallenge(verifier);
	sessionStorage.setItem('spotify_pkce_verifier', verifier);
	const params = new URLSearchParams({
		client_id: CLIENT_ID,
		response_type: 'code',
		redirect_uri: REDIRECT_URI,
		scope: SCOPES,
		code_challenge_method: 'S256',
		code_challenge: challenge,
		show_dialog: 'true',
	});
	window.location = `${AUTHORIZE_ENDPOINT}?${params}`;
}

/** Clear the session everywhere. */
export function logoutSpotify() {
	clearStoredTokens();
	access_token.set('');
}
