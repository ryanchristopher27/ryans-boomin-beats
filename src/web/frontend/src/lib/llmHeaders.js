// BYOK credentials travel per request as headers rather than a server-side
// session cookie — see backend/services/llm_auth.py. Returns {} when no key is
// connected, which endpoints treat as "no LLM" (401 on LLM-only routes,
// graceful degradation on /song/profile/).
import { get } from 'svelte/store';
import { llmConfig } from '../stores.js';

/** @returns {Record<string, string>} */
export function llmHeaders() {
	const { provider, apiKey } = get(llmConfig) ?? {};
	if (!provider || !apiKey) return {};
	return {
		'X-LLM-Provider': provider,
		'X-LLM-Key': apiKey,
	};
}
