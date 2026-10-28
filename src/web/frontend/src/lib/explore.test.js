import { describe, expect, test } from 'vitest';
import { builderPrompt, extendTrail, parseAnalysis } from './explore.js';

const s = (id) => ({ id, title: id, artists: ['A'] });

describe('explore', () => {
	test('parses analysis lines and skips junk', () => {
		expect(parseAnalysis('Mood: warm\n\nnot a field\nTempo: 92 bpm: slow')).toEqual([
			{ label: 'Mood', value: 'warm' },
			{ label: 'Tempo', value: '92 bpm: slow' }
		]);
		expect(parseAnalysis(null)).toEqual([]);
	});
	test('the Builder prompt names the song and the picks', () => {
		expect(builderPrompt({ title: 'Redbone', artists: ['Childish Gambino'] }, ['funk', 'Slow groove'])).toBe('Songs like Redbone by Childish Gambino: funk, Slow groove');
	});
	test('the Path branches from the current song', () => {
		const trail = [s('a'), s('b'), s('c')];
		expect(extendTrail(trail, 'c', s('d')).map((t) => t.id)).toEqual(['a', 'b', 'c', 'd']);
		expect(extendTrail(trail, 'a', s('d')).map((t) => t.id)).toEqual(['a', 'd']);
		expect(extendTrail(trail, 'b', s('a')).map((t) => t.id)).toEqual(['b', 'a']);
	});
});
