// Backend calls for the web DJ. Returns {status, data} instead of throwing on
// HTTP errors, because the sync protocol answers with meaningful statuses
// (409 carries the current document). Throws only when the network fails.
import { PUBLIC_API_URL } from '$env/static/public';
import { spotifyHeaders } from '../spotifyHeaders.js';
import { llmHeaders } from '../llmHeaders.js';
import { relayFetch } from '../llmRelay.js';

const AI_PATHS = ['dj/suggest', 'dj/recap', 'song/profile'];

/**
 * @param {string} method
 * @param {string} path
 * @param {{json?: any, headers?: Record<string, string>}} [opts]
 * @returns {Promise<{status: number, data: any}>}
 */
export async function request(method, path, { json = undefined, headers = {} } = {}) {
	const ai = AI_PATHS.some((p) => path.startsWith(p));
	const res = await (ai ? relayFetch : fetch)(`${PUBLIC_API_URL}/${path}`, {
		method,
		headers: {
			...spotifyHeaders(),
			// The LLM key goes only where it's used.
			...(ai ? llmHeaders() : {}),
			...(json !== undefined ? { 'Content-Type': 'application/json' } : {}),
			...headers
		},
		body: json !== undefined ? JSON.stringify(json) : undefined
	});
	let data = null;
	try {
		data = await res.json();
	} catch {
		/* empty or non-JSON body */
	}
	return { status: res.status, data };
}

export function hasLLM() {
	return Object.keys(llmHeaders()).length > 0;
}
