// DJ chat actions applied to the DJ and the page; fakes record the calls.
import { expect, test, vi } from 'vitest';
import { applyActions } from './chat.js';

function fakes() {
	const calls = [];
	const rec = (name) => (...a) => calls.push([name, ...a]);
	const dj = { setMode: rec('mode'), setAdventurousness: rec('bold'), setFamiliar: rec('familiar'), setGoal: rec('goal'), steerMoves: rec('steer') };
	const page = { choose: rec('preset'), apply: rec('layout') };
	return { calls, dj, page };
}

test('applies each action and says what changed', () => {
	const { calls, dj, page } = fakes();
	const done = applyActions(
		[
			{ type: 'preset', name: 'compass' },
			{ type: 'layout', items: [{ type: 'upNext', x: 0, y: 0, w: 4, h: 8 }] },
			{ type: 'controls', mode: 'driver', adventurousness: 0.8 },
			{ type: 'goal', goal: { kind: 'drift' } },
			{ type: 'refresh_moves', note: 'more upbeat' }
		],
		{ dj, page }
	);
	expect(calls.map((c) => c[0])).toEqual(['layout', 'layout', 'mode', 'bold', 'goal', 'steer']);
	// Both layouts keep the chat: Compass gets it added; the custom one too.
	expect(calls[0][1].map((i) => i.id)).toContain('chat');
	expect(calls[1][1].map((i) => i.id)).toEqual(['upNext', 'chat']);
	expect(done).toEqual(['Layout: Compass', 'Layout rearranged', 'Mode: Driver', 'Safe ↔ Bold: 80%', 'Goal: drift', 'New moves: more upbeat']);
});

test('a layout with nothing usable changes nothing', () => {
	const { calls, dj, page } = fakes();
	expect(applyActions([{ type: 'layout', items: [{ type: 'bogus', x: 0, y: 0, w: 3, h: 3 }] }], { dj, page })).toEqual([]);
	expect(calls).toEqual([]);
});
