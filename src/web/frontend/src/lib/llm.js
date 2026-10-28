// Connecting an AI provider (BYOK), shared by Settings and first run.
import { PUBLIC_API_URL } from '$env/static/public';
import { llmConfig } from '../stores.js';
import { spotifyHeaders } from './spotifyHeaders.js';

// 'Your Claude Code' runs the CLI on the backend's machine, so it only works
// against a local backend, never the hosted one.
const LOCAL_API = /\/\/(127\.0\.0\.1|localhost)[:/]/.test(PUBLIC_API_URL);

const ALL = [
	{ id: 'claude', label: 'Claude', note: 'Anthropic API key', placeholder: 'sk-ant-…' },
	{ id: 'openai', label: 'OpenAI', note: 'OpenAI API key', placeholder: 'sk-…' },
	{ id: 'groq', label: 'Groq', note: 'Free tier, faster, lighter picks', placeholder: 'gsk_…' },
	{ id: 'claude-code', label: 'Your Claude Code', note: 'Runs on this Mac. No key needed. Works while the backend runs locally.', keyless: true }
];
export const PROVIDERS = LOCAL_API ? ALL : ALL.filter((p) => p.id !== 'claude-code');

/**
 * Check the key with the provider (the backend validates it and discards it;
 * nothing is stored server-side), then keep it on this device.
 * @returns {Promise<{ok: true} | {ok: false, error: string}>}
 */
export async function connectLLM(provider, apiKey) {
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

export function disconnectLLM() {
	llmConfig.set({ provider: 'claude', apiKey: '', connected: false });
	localStorage.removeItem('llmConfig');
}
