import { describe, expect, test } from 'vitest';
import { COLUMNS, PRESETS, WIDGETS, addable, completeSaved, itemsFor, loadLayout, moveForKey, nudgeBox } from './layout.js';

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
	test('a widget added this session saves with a size (W2 bug)', () => {
		const items = [{ id: 'requests', type: 'requests', x: 0, y: 0, w: 3, h: 4 }];
		const saved = [{ id: 'requests', x: 0, y: 15 }]; // gridstack left w/h out
		expect(completeSaved(saved, items, new Map([['requests', { w: 4, h: 5 }]]))[0]).toMatchObject({ w: 4, h: 5, y: 15 });
		expect(completeSaved(saved, items)[0]).toMatchObject({ w: WIDGETS.requests.w, h: WIDGETS.requests.h });
	});
	test('keyboard nudges stay on the grid and above minimums', () => {
		const box = { x: 9, y: 0, w: 3, h: 4, minW: 3, minH: 3 };
		expect(nudgeBox(box, 1, 0, 0, 0, 12)).toMatchObject({ x: 9 }); // already at the right edge
		expect(nudgeBox(box, 0, -1, 0, 0, 12)).toMatchObject({ y: 0 }); // already at the top
		expect(nudgeBox(box, 0, 0, -1, -2, 12)).toMatchObject({ w: 3, h: 3 }); // minimums hold
		expect(nudgeBox(box, 0, 0, 2, 0, 12)).toMatchObject({ w: 5, x: 7 }); // grows inward
	});
	test('the Add widget menu offers only what is missing', () => {
		const ids = addable(PRESETS.focus.items).map((a) => a.id);
		expect(ids).toContain('upNext');
		expect(ids).toContain('move-hold');
		expect(ids).not.toContain('moves');
	});
	test('Compass keys map to moves, but never while typing or with a modifier', () => {
		const key = (k, extra = {}) => moveForKey({ key: k, target: { tagName: 'DIV' }, ...extra });
		expect([key('ArrowUp'), key('ArrowDown'), key('ArrowLeft'), key('ArrowRight'), key('h'), key('T')]).toEqual(['lift', 'drop', 'pivot', 'curveball', 'hold', 'toward']);
		expect(key('x')).toBe(null);
		expect(key('h', { target: { tagName: 'INPUT' } })).toBe(null);
		expect(key('ArrowUp', { metaKey: true })).toBe(null);
	});
});
