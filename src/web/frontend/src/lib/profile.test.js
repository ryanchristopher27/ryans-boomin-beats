import { describe, expect, test } from 'vitest';
import { hourLabel, insights, peakHour, summaryParts } from './profile.js';

const decades = [{ label: '2010s', value: 6 }, { label: '2020s', value: 19 }];
const text = (parts) => parts.map((p) => p.text).join('');

describe('profile', () => {
	test('hours read as 12-hour times', () => {
		expect([0, 9, 12, 19].map(hourLabel)).toEqual(['12am', '9am', '12pm', '7pm']);
		expect(peakHour([0, 3, 9, 2])).toBe(2);
		expect(peakHour([0, 0])).toBe(null);
	});
	test('the summary names genres, the top era and the peak hour', () => {
		const parts = summaryParts({ period: 'short_term', genres: ['Rap', 'R&B', 'Pop'], decades, peak: 20 });
		expect(text(parts)).toBe('Your last 4 weeks: mostly rap and r&b, 76% from the 2020s, and you listen most around 8pm.');
		expect(parts.filter((p) => p.strong).map((p) => p.text)).toEqual(['rap and r&b', '8pm']);
	});
	test('the summary degrades without data', () => {
		expect(text(summaryParts({ period: 'long_term', genres: [], decades: [], peak: null }))).toMatch(/fills in as you listen/);
		expect(text(summaryParts({ period: 'long_term', genres: ['soul'], decades: [], peak: null }))).toBe('All time: mostly soul.');
	});
	test('insights carry Builder prompts and a DJ action', () => {
		const cards = insights({ period: 'short_term', genres: ['rap'], decades, peak: 23, topArtist: 'Don Toliver' });
		expect(cards.map((c) => c.label)).toEqual(['Top genre', 'Eras', 'Listening clock', 'Top artist']);
		expect(cards[1]).toMatchObject({ value: 'Mostly the 2020s, some 2010s', prompt: 'my kind of music from the 2010s' });
		expect(cards[2]).toMatchObject({ kind: 'dj', action: 'Start a late-night DJ set' });
		expect(cards[3].prompt).toBe('songs like Don Toliver');
	});
});
