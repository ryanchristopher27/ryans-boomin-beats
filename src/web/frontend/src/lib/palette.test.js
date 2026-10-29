import { describe, expect, test } from 'vitest';
import { buildItems, countLabel, matchPages, moveSelection, recentSongs } from './palette.js';

const s = (id, extra = {}) => ({ id, title: `T${id}`, artists: ['A'], ...extra });

describe('palette', () => {
	test('recents: newest trail first, then DJ, deduped and capped', () => {
		const out = recentSongs([s(1), s(2)], [s(2), s(3, { isrc: 'X' }), s(4, { isrc: 'X' })], 4);
		expect(out.map((x) => x.id)).toEqual([2, 1, 3]);
		expect(recentSongs([s(1), s(2), s(3)], [], 2)).toHaveLength(2);
	});

	test('pages filter by label', () => {
		expect(matchPages('dj').map((p) => p.label)).toEqual(['DJ']);
		expect(matchPages('').length).toBe(5);
	});

	test('items: recents when empty, results at 3+ chars, pages only for short queries', () => {
		const recent = [s(1)];
		const results = [s(2), s(3)];
		expect(buildItems('', { recent, results }).filter((i) => i.kind === 'song')).toHaveLength(1);
		expect(buildItems('ab', { recent, results }).filter((i) => i.kind === 'song')).toHaveLength(0);
		const found = buildItems('explore', { recent, results });
		expect(found.filter((i) => i.kind === 'song')).toHaveLength(2);
		expect(found.filter((i) => i.kind === 'page').map((i) => i.page.label)).toEqual(['Explore']);
	});

	test('arrow keys wrap and ignore others', () => {
		expect(moveSelection(0, 'ArrowDown', 3)).toBe(1);
		expect(moveSelection(2, 'ArrowDown', 3)).toBe(0);
		expect(moveSelection(0, 'ArrowUp', 3)).toBe(2);
		expect(moveSelection(1, 'a', 3)).toBe(1);
		expect(moveSelection(0, 'ArrowDown', 0)).toBe(-1);
	});

	test('count label', () => {
		expect(countLabel(buildItems('', { recent: [s(1)] }))).toBe('1 song, 5 pages');
		expect(countLabel([])).toBe('No results');
	});
});
