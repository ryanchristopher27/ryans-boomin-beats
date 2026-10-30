// "Your Claude Code" on the hosted site (provider 'helper'). The backend can't
// reach this computer, so when a request needs the AI it answers 428 with the
// prompt; we run it on the user's trip-fairy-helper (127.0.0.1) and repeat the
// request with every reply so far in `llm_replies` (backend: llm_client.NeedsLLM).
// If the helper fails, the last repeat carries `llm_error` instead, and the
// route degrades as it would for any provider's failure.
import { get } from 'svelte/store';
import { llmConfig } from '../stores.js';

export const HELPER_URL = 'http://127.0.0.1:8787';
export const HELPER_COMMAND = 'npx trip-fairy-helper';
// A route makes at most a few AI calls (the Builder retries songs it can't find).
const MAX_ROUNDS = 6;

const UNREACHABLE = `Can't reach your Claude Code helper. Run \`${HELPER_COMMAND}\` and leave it running. If the browser asks to let this site access your local network, choose Allow.`;

/** Raises with a message written for the user. */
async function callHelper(path, init = {}) {
	const code = get(llmConfig)?.apiKey ?? '';
	let res;
	try {
		res = await fetch(`${HELPER_URL}${path}`, { ...init, headers: { 'X-Helper-Token': code.trim(), ...(init.headers ?? {}) } });
	} catch {
		throw new Error(UNREACHABLE);
	}
	const data = await res.json().catch(() => ({}));
	if (res.status === 401) throw new Error('The pairing code is wrong. Copy it again from the helper\'s terminal in Settings → AI.');
	if (!res.ok) throw new Error(data.error || `The helper answered ${res.status}.`);
	return data;
}

/** Settings' Connect: the helper is running, the code is right, and Claude Code is installed. */
export async function checkHelper() {
	const h = await callHelper('/ai/health');
	if (!h.claude) throw new Error('The helper is running, but Claude Code isn\'t installed or signed in on this computer. Run `claude` and /login.');
}

/** `model`: the backend names one (Sonnet), so the CLI's default (often Opus) isn't used. */
async function askHelper(prompt, model) {
	const { text } = await callHelper('/ai/plan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt, model }) });
	return text ?? '';
}

const isRelay = () => get(llmConfig)?.provider === 'helper';

/**
 * fetch() for AI endpoints. Other providers pass straight through. With the
 * helper, a GET becomes a POST so the replies can ride in the body.
 * @param {string} url
 * @param {RequestInit} [init]
 * @returns {Promise<Response>}
 */
export async function relayFetch(url, init = {}) {
	if (!isRelay()) return fetch(url, init);
	const base = init.body ? JSON.parse(String(init.body)) : {};
	const headers = { ...(init.headers ?? {}), 'Content-Type': 'application/json' };
	/** @type {string[]} */
	const replies = [];
	/** @type {string | undefined} */
	let llm_error;
	for (let round = 0; ; round++) {
		const res = await fetch(url, { ...init, method: 'POST', headers, body: JSON.stringify({ ...base, llm_replies: replies, llm_error }) });
		if (res.status !== 428 || llm_error) return res;
		const needs = (await res.clone().json().catch(() => null))?.needs_llm;
		const prompt = needs?.prompt;
		if (!prompt) return res;
		if (round === MAX_ROUNDS) {
			llm_error = 'Your Claude Code was asked too many times for one request.';
			continue;
		}
		try {
			replies.push(await askHelper(prompt, needs.model));
		} catch (e) {
			llm_error = e.message;
		}
	}
}
