// Connecting an AI provider (BYOK), shared by Settings and first run.
import { PUBLIC_API_URL } from '$env/static/public';
import { get } from 'svelte/store';
import { llmConfig } from '../stores.js';
import { spotifyHeaders } from './spotifyHeaders.js';
import { checkHelper } from './llmRelay.js';

// 'claude-code' runs the CLI on the backend's machine, so it only works against
// a local backend. 'helper' works anywhere: the page relays to the user's own
// trip-fairy-helper (lib/llmRelay.js), and its "key" is the helper's pairing code.
const LOCAL_API = /\/\/(127\.0\.0\.1|localhost)[:/]/.test(PUBLIC_API_URL);

const ALL = [
	{ id: 'claude', label: 'Claude', note: 'Anthropic API key', placeholder: 'sk-ant-…' },
	{ id: 'openai', label: 'OpenAI', note: 'OpenAI API key', placeholder: 'sk-…' },
	{ id: 'groq', label: 'Groq', note: 'Free tier, faster, lighter picks', placeholder: 'gsk_…' },
	{ id: 'helper', label: 'Your Claude Code', note: 'The Claude Code signed in on this computer. No key, no cost.', placeholder: 'Pairing code', keyName: 'Pairing code' },
	{ id: 'claude-code', label: 'Claude Code on the backend', note: 'For a backend running on this Mac. No key needed.', keyless: true }
];
export const PROVIDERS = LOCAL_API ? ALL : ALL.filter((p) => p.id !== 'claude-code');

/**
 * Check the key with the provider (the backend validates it and discards it;
 * nothing is stored server-side), then keep it on this device.
 * @returns {Promise<{ok: true} | {ok: false, error: string}>}
 */
export async function connectLLM(provider, apiKey) {
	if (provider === 'helper') return connectHelper(apiKey);
	const keyless = !!ALL.find((p) => p.id === provider)?.keyless;
	try {
		const res = await fetch(`${PUBLIC_API_URL}/llm/connect/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', ...spotifyHeaders() },
			body: JSON.stringify({ provider, api_key: keyless ? '' : apiKey })
		});
		const data = await res.json();
		if (!data.connected) return { ok: false, error: data.error || data.detail || 'Connection failed.' };
		const config = { provider, apiKey: keyless ? '' : apiKey, connected: true };
		llmConfig.set(config);
		localStorage.setItem('llmConfig', JSON.stringify(config));
		return { ok: true };
	} catch {
		return { ok: false, error: 'Could not reach the server.' };
	}
}

/** The pairing code stays on this device; the backend never sees it. */
async function connectHelper(code) {
	const previous = get(llmConfig);
	const config = { provider: 'helper', apiKey: code.trim(), connected: true };
	llmConfig.set(config); // checkHelper reads the code from here
	try {
		await checkHelper();
	} catch (e) {
		llmConfig.set(previous);
		return { ok: false, error: e.message };
	}
	localStorage.setItem('llmConfig', JSON.stringify(config));
	return { ok: true };
}

export function disconnectLLM() {
	llmConfig.set({ provider: 'claude', apiKey: '', connected: false });
	localStorage.removeItem('llmConfig');
}
