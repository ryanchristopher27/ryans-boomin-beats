import { describe, expect, it } from 'vitest';
import { bpFor } from './breakpoint.js';

describe('bpFor', () => {
	it('splits at 760 and 1180 on a 1x scale', () => {
		expect(bpFor(375)).toBe('phone');
		expect(bpFor(759)).toBe('phone');
		expect(bpFor(760)).toBe('tablet');
		expect(bpFor(1179)).toBe('tablet');
		expect(bpFor(1180)).toBe('desktop');
	});
	it('divides by the text scale', () => {
		expect(bpFor(924, 0.9)).toBe('tablet');
		expect(bpFor(900, 1.2)).toBe('phone');
		expect(bpFor(1280, 1.2)).toBe('tablet');
		expect(bpFor(1280, 0.9)).toBe('desktop');
		expect(bpFor(700, 0.9)).toBe('tablet');
	});
});
