import { describe, expect, test } from 'vitest';
import { COLUMNS, PRESETS, WIDGETS, addable, itemsFor, loadLayout } from './layout.js';

describe('layout', () => {
	test('presets fit the grid and respect minimum sizes', () => {
		for (const { items } of Object.values(PRESETS)) {
			for (const i of items) {
				expect(i.x + i.w).toBeLessThanOrEqual(COLUMNS);
				expect(i.w).toBeGreaterThanOrEqual(WIDGETS[i.type].minW);
				expect(i.h).toBeGreaterThanOrEqual(WIDGETS[i.type].minH);
			}
			expect(new Set(items.map((i) => i.id)).size).toBe(items.length);
		}
	});
	test('missing or corrupt layouts fall back to Host', () => {
		expect(loadLayout(null).preset).toBe('host');
		expect(loadLayout('{nope').preset).toBe('host');
		const bad = (custom) => loadLayout(JSON.stringify({ preset: 'custom', custom }));
		expect(bad([{ id: 'x', type: 'mystery', x: 0, y: 0, w: 1, h: 1 }])).toEqual({ preset: 'host', custom: null });
		expect(bad([{ id: 'goal', type: 'goal', x: 11, y: 0, w: 3, h: 2 }]).preset).toBe('host');
	});
	test('your layout survives picking a preset', () => {
		const custom = [{ id: 'goal', type: 'goal', x: 0, y: 0, w: 3, h: 2 }];
		const saved = loadLayout(JSON.stringify({ preset: 'board', custom }));
		expect(saved).toEqual({ preset: 'board', custom });
		expect(itemsFor(saved)).toEqual(PRESETS.board.items);
		expect(itemsFor({ ...saved, preset: 'custom' })).toEqual(custom);
	});
	test('the Add widget menu offers only what is missing', () => {
		const ids = addable(PRESETS.focus.items).map((a) => a.id);
		expect(ids).toContain('upNext');
		expect(ids).toContain('move-hold');
		expect(ids).not.toContain('moves');
	});
});
