// Album-art ambience (W3): the Now playing widget's background is a dark,
// low-chroma tint of the cover's dominant colour. Clamped to OKLCH L 0.18-0.24
// and C <= 0.04 so white and muted text keep >= 4.5:1 on it.

const L_MIN = 0.18;
const L_MAX = 0.24;
const C_MAX = 0.04;

/** sRGB 0-255 → OKLab (Björn Ottosson's matrices). */
export function toOklab(r, g, b) {
	const lin = (c) => {
		c /= 255;
		return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
	};
	const [R, G, B] = [lin(r), lin(g), lin(b)];
	const l = Math.cbrt(0.4122214708 * R + 0.5363325363 * G + 0.0514459929 * B);
	const m = Math.cbrt(0.2119034982 * R + 0.6806995451 * G + 0.1073969566 * B);
	const s = Math.cbrt(0.0883024619 * R + 0.2817188376 * G + 0.6299787005 * B);
	return [
		0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
		1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
		0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s
	];
}

/**
 * The tint for an image's pixels (RGBA bytes). Colourful pixels count more
 * than grey ones, so a vivid subject on a dull background still sets the hue.
 * @returns {string} a CSS oklch() colour
 */
export function ambientColor(pixels) {
	let wSum = 0;
	let L = 0;
	let A = 0;
	let B = 0;
	for (let i = 0; i < pixels.length; i += 4) {
		if (pixels[i + 3] < 128) continue;
		const [l, a, b] = toOklab(pixels[i], pixels[i + 1], pixels[i + 2]);
		const w = Math.hypot(a, b) + 0.01;
		wSum += w;
		L += l * w;
		A += a * w;
		B += b * w;
	}
	if (!wSum) return '';
	const [l, a, b] = [L / wSum, A / wSum, B / wSum];
	const lightness = L_MIN + (L_MAX - L_MIN) * Math.min(1, Math.max(0, l));
	const chroma = Math.min(C_MAX, Math.hypot(a, b));
	const hue = ((Math.atan2(b, a) * 180) / Math.PI + 360) % 360;
	return `oklch(${lightness.toFixed(3)} ${chroma.toFixed(3)} ${hue.toFixed(1)})`;
}

const cache = new Map();

/** Sample a cover (CORS-safe through i.scdn.co) down to 16×16 and tint from it. '' on failure. */
export function sampleCover(url) {
	if (!url) return Promise.resolve('');
	if (cache.has(url)) return cache.get(url);
	const p = new Promise((resolve) => {
		const img = new Image();
		img.crossOrigin = 'anonymous';
		img.onload = () => {
			try {
				const canvas = document.createElement('canvas');
				canvas.width = canvas.height = 16;
				const ctx = canvas.getContext('2d', { willReadFrequently: true });
				if (!ctx) return resolve('');
				ctx.drawImage(img, 0, 0, 16, 16);
				resolve(ambientColor(ctx.getImageData(0, 0, 16, 16).data));
			} catch {
				resolve(''); // tainted canvas or no 2D context: stay neutral
			}
		};
		img.onerror = () => resolve('');
		img.src = url;
	});
	if (cache.size > 50) cache.clear();
	cache.set(url, p);
	return p;
}
