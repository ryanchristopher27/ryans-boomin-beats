import { describe, expect, test } from 'vitest';
import { ambientColor, nameHue, toOklab } from './ambience.js';

const solid = (r, g, b, n = 4) => Uint8ClampedArray.from({ length: n * 4 }, (_, i) => [r, g, b, 255][i % 4]);
const parse = (s) => s.match(/oklch\(([\d.]+) ([\d.]+) ([\d.]+)\)/).slice(1).map(Number);

describe('ambience', () => {
	test('OKLab of white and black', () => {
		expect(toOklab(255, 255, 255)[0]).toBeCloseTo(1, 3);
		expect(toOklab(0, 0, 0)[0]).toBeCloseTo(0, 3);
	});
	test('stays dark and low-chroma for any cover', () => {
		for (const px of [solid(255, 255, 255), solid(255, 0, 0), solid(0, 0, 255), solid(10, 10, 10)]) {
			const [l, c] = parse(ambientColor(px));
			expect(l).toBeGreaterThanOrEqual(0.18);
			expect(l).toBeLessThanOrEqual(0.24);
			expect(c).toBeLessThanOrEqual(0.04);
		}
	});
	test('keeps the hue of a vivid subject on a grey background', () => {
		const px = new Uint8ClampedArray([...solid(128, 128, 128, 12), ...solid(40, 80, 255, 4)]);
		const blue = parse(ambientColor(solid(40, 80, 255)))[2];
		expect(Math.abs(parse(ambientColor(px))[2] - blue)).toBeLessThan(10);
	});
	test('transparent images give no tint', () => {
		expect(ambientColor(new Uint8ClampedArray(16))).toBe('');
	});
	test('a name always gets the same hue in range', () => {
		expect(nameHue('Redbone')).toBe(nameHue('Redbone'));
		for (const t of ['', 'Redbone', 'Come and Get Your Love', '4EVA']) expect(nameHue(t)).toBeGreaterThanOrEqual(0), expect(nameHue(t)).toBeLessThan(360);
	});
});
