// The helper relay: a 428 hands back the prompt, the helper answers, and the
// request repeats with every reply so far. fetch is faked.
import { afterEach, expect, test, vi } from 'vitest';
import { llmConfig } from '../stores.js';
import { relayFetch } from './llmRelay.js';

const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

afterEach(() => vi.unstubAllGlobals());

function fake(helper) {
	const sent = [];
	vi.stubGlobal('fetch', vi.fn(async (url, init) => {
		if (url.startsWith('http://127.0.0.1:8787')) return helper(JSON.parse(init.body).prompt, init);
		const body = JSON.parse(init.body);
		sent.push({ method: init.method, ...body });
		if (body.llm_error) return json(200, { error: body.llm_error });
		return body.llm_replies.length < 2 ? json(428, { needs_llm: { prompt: `ask ${body.llm_replies.length}` } }) : json(200, { got: body.llm_replies });
	}));
	return sent;
}

test('replies accumulate across rounds; a GET goes out as a POST', async () => {
	llmConfig.set({ provider: 'helper', apiKey: 'code', connected: true });
	const sent = fake(async (prompt, init) => {
		expect(init.headers['X-Helper-Token']).toBe('code');
		return json(200, { text: `re: ${prompt}` });
	});
	const res = await relayFetch('http://api/song/profile/?title=a', { headers: {} });
	expect(await res.json()).toEqual({ got: ['re: ask 0', 're: ask 1'] });
	expect(sent.map((s) => s.method)).toEqual(['POST', 'POST', 'POST']);
});

test("a helper failure goes back as llm_error, so the route degrades", async () => {
	llmConfig.set({ provider: 'helper', apiKey: 'wrong', connected: true });
	const sent = fake(async () => json(401, { error: 'bad', code: 'bad_token' }));
	const res = await relayFetch('http://api/dj/suggest/', { method: 'POST', body: JSON.stringify({ a: 1 }) });
	expect((await res.json()).error).toMatch(/pairing code is wrong/);
	expect(sent.at(-1)).toMatchObject({ a: 1, llm_replies: [] });
});

test('other providers pass straight through', async () => {
	llmConfig.set({ provider: 'groq', apiKey: 'k', connected: true });
	const f = vi.fn(async () => json(200, {}));
	vi.stubGlobal('fetch', f);
	await relayFetch('http://api/x', { method: 'GET' });
	expect(f.mock.calls[0][1]).toEqual({ method: 'GET' });
});
