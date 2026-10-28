import { describe, expect, test } from 'vitest';
import { playlistMeta, playlistName, replyText } from './builder.js';

describe('builder', () => {
	test('names a playlist from its prompt', () => {
		expect(playlistName('late night jazz for studying.')).toBe('Late night jazz for studying');
		expect(playlistName('  ')).toBe('New playlist');
		expect(playlistName('moody r&b for a night drive, nothing too slow, and some 90s classics please')).toBe('Moody r&b for a night drive, nothing too…');
	});
	test('summarises the assistant reply', () => {
		expect(replyText('[{"title":"a"},{"title":"b"}]', true)).toBe('Picked 2 songs and checked each one.');
		expect(replyText('[]', false)).toMatch(/couldn't find/);
		expect(replyText('plain words', false)).toBe('plain words');
	});
	test('meta counts songs and minutes', () => {
		expect(playlistMeta([{ spotify: { duration_ms: 200000 } }, { spotify: { duration_ms: 100000 } }])).toBe('2 songs · 5 min');
		expect(playlistMeta([{ spotify: {} }])).toBe('1 song');
	});
});
