import { describe, expect, test } from 'vitest';
import { NIGHT, activePreset, applyPreset } from './presets.js';

describe('night presets', () => {
	test('applying a preset sets boldness and the goal', () => {
		const calls = [];
		applyPreset({ setAdventurousness: (a) => calls.push(['bold', a]), setGoal: (g) => calls.push(['goal', g]) }, 'pregame');
		expect(calls).toEqual([['bold', 0.55], ['goal', NIGHT.pregame.goal]]);
	});
	test('the active preset is recognised, and lost once tweaked', () => {
		const opts = { adventurousness: 0.8, goal: { kind: 'arc', shape: 'peak_cool', minutes: 60, startedAt: 'x' } };
		expect(activePreset(opts)).toBe('peak');
		expect(activePreset({ ...opts, adventurousness: 0.6 })).toBe(null);
		expect(activePreset({ ...opts, goal: { ...opts.goal, minutes: 30 } })).toBe(null);
		expect(activePreset({ adventurousness: 0.2, goal: { kind: 'drift' } })).toBe('dinner');
		expect(activePreset({ adventurousness: 0.5, goal: null })).toBe(null);
	});
});
