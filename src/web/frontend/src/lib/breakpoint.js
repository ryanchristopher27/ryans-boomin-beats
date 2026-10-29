// Layout breakpoints on effective width: window width ÷ the text-size scale, so
// a larger text size reaches the phone layout sooner. CSS media queries can't
// divide by --text-scale, so the root carries the answer as data-bp (set in
// +layout.svelte) and styles key off `[data-bp='phone']` / `[data-narrow]`.
export const PHONE = 760;
export const DESKTOP = 1180;

/** @returns {'phone' | 'tablet' | 'desktop'} */
export function bpFor(width, scale = 1) {
	const w = width / scale;
	return w < PHONE ? 'phone' : w < DESKTOP ? 'tablet' : 'desktop';
}
