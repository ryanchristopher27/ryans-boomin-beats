// The DJ page's widget grid (W2): the widget catalog, the three presets from
// the design brief, and per-browser persistence. Layout is convenience state,
// so it lives in localStorage (`djLayout.v1`) and never syncs.

export const COLUMNS = 12;
export const STORAGE_KEY = 'djLayout.v1';
export const MOVE_KINDS = ['toward', 'hold', 'lift', 'drop', 'pivot', 'curveball', 'drift'];

/** Widget types: minimum size and the size they're added at, in grid cells. */
export const WIDGETS = {
	nowPlaying: { title: 'Now playing', minW: 3, minH: 3, w: 3, h: 7 },
	controls: { title: 'DJ controls', minW: 3, minH: 4, w: 3, h: 5 },
	goal: { title: 'Goal', minW: 3, minH: 2, w: 3, h: 3 },
	moves: { title: 'Next moves', minW: 4, minH: 6, w: 6, h: 10 },
	move: { title: 'Move', minW: 2, minH: 3, w: 3, h: 6 },
	upNext: { title: 'Up next', minW: 3, minH: 5, w: 3, h: 8 },
	requests: { title: 'Requests', minW: 3, minH: 3, w: 3, h: 4 },
	profile: { title: 'Song profile', minW: 3, minH: 5, w: 3, h: 9 },
	recent: { title: 'Recently played', minW: 3, minH: 3, w: 3, h: 6 },
	playlist: { title: 'Playlist', minW: 3, minH: 5, w: 3, h: 8 }
};

const w = (type, x, y, width, h, extra = {}) => ({ id: extra.kind ? `move-${extra.kind}` : type, type, x, y, w: width, h, ...extra });

export const PRESETS = {
	host: {
		label: 'Host',
		// Goal docks inside DJ controls here, so the art gets the height.
		items: [
			w('nowPlaying', 0, 0, 3, 8),
			w('controls', 0, 8, 3, 7),
			w('moves', 3, 0, 6, 15),
			w('requests', 9, 0, 3, 5),
			w('upNext', 9, 5, 3, 10)
		]
	},
	board: {
		label: 'Board',
		items: [
			w('nowPlaying', 0, 0, 12, 3),
			w('move', 0, 3, 3, 6, { kind: 'hold' }),
			w('move', 3, 3, 3, 6, { kind: 'lift' }),
			w('move', 6, 3, 3, 6, { kind: 'drop' }),
			w('move', 9, 3, 3, 6, { kind: 'pivot' }),
			w('upNext', 0, 9, 5, 6),
			w('requests', 5, 9, 3, 6),
			w('controls', 8, 9, 4, 6)
		]
	},
	// F3g: the moves around Now playing; keys add from them (see MOVE_KEYS).
	compass: {
		label: 'Compass',
		items: [
			w('move', 0, 0, 4, 5, { kind: 'hold' }),
			w('move', 4, 0, 4, 5, { kind: 'lift' }),
			w('move', 8, 0, 4, 5, { kind: 'toward' }),
			w('move', 0, 5, 4, 5, { kind: 'pivot' }),
			w('nowPlaying', 4, 5, 4, 5),
			w('move', 8, 5, 4, 5, { kind: 'curveball' }),
			w('controls', 0, 10, 4, 5),
			w('move', 4, 10, 4, 5, { kind: 'drop' }),
			w('upNext', 8, 10, 4, 5)
		]
	},
	focus: {
		label: 'Focus',
		items: [w('nowPlaying', 0, 0, 5, 8), w('controls', 0, 8, 5, 7), w('moves', 5, 0, 7, 15)]
	}
};

/** @param {any} item */
function valid(item) {
	const def = WIDGETS[item?.type];
	if (!def || typeof item.id !== 'string') return false;
	if (item.type === 'move' && !MOVE_KINDS.includes(item.kind)) return false;
	return ['x', 'y', 'w', 'h'].every((k) => Number.isInteger(item[k]) && item[k] >= 0) && item.x + item.w <= COLUMNS;
}

/**
 * A layout the DJ chat proposed, made safe for the grid: known widgets only, ids
 * as the presets use them, sizes at least each widget's minimum and inside 12
 * columns, no duplicates. Null when nothing usable is left.
 * @param {{type: string, kind?: string, x: number, y: number, w: number, h: number}[]} proposed
 */
export function layoutFromChat(proposed) {
	const seen = new Set();
	const out = [];
	for (const p of Array.isArray(proposed) ? proposed : []) {
		const def = WIDGETS[p?.type];
		if (!def || (p.type === 'move' && !MOVE_KINDS.includes(p.kind))) continue;
		const id = p.type === 'move' ? `move-${p.kind}` : p.type;
		if (seen.has(id)) continue;
		const int = (v, lo, hi) => Math.min(hi, Math.max(lo, Math.round(Number(v) || 0)));
		const w = int(p.w, def.minW, COLUMNS);
		const item = { id, type: p.type, x: int(p.x, 0, COLUMNS - w), y: int(p.y, 0, 60), w, h: int(p.h, def.minH, 30), ...(p.type === 'move' ? { kind: p.kind } : {}) };
		if (!valid(item)) continue;
		seen.add(id);
		out.push(item);
	}
	return out.length ? out : null;
}

/**
 * The saved layout: `{preset, custom}`, where `custom` is "Your layout" (null
 * until the user edits one). Missing or corrupt parts fall back to Host.
 * @returns {{preset: string, custom: any[] | null}}
 */
export function loadLayout(raw) {
	let saved = null;
	try {
		saved = JSON.parse(raw ?? 'null');
	} catch {
		/* corrupt: start over */
	}
	const custom = Array.isArray(saved?.custom) && saved.custom.length && saved.custom.every(valid) ? saved.custom : null;
	const preset = PRESETS[saved?.preset] || (saved?.preset === 'custom' && custom) ? saved.preset : 'host';
	return { preset, custom };
}

/** The items for a layout choice, as a fresh copy the grid can own. */
export function itemsFor({ preset, custom }) {
	return structuredClone(preset === 'custom' && custom ? custom : PRESETS[preset]?.items ?? PRESETS.host.items);
}

/**
 * gridstack's save() as layout items. A widget added this session can come back
 * without a size (W2 bug), so fall back to the live node, then the type's default.
 */
export function completeSaved(saved, items, live = new Map()) {
	const byId = new Map(items.map((i) => [i.id, i]));
	return saved.map(({ id, x, y, w, h }) => {
		const item = byId.get(id);
		const node = live.get(id);
		return { ...item, x: x ?? 0, y: y ?? 0, w: w ?? node?.w ?? WIDGETS[item.type].w, h: h ?? node?.h ?? WIDGETS[item.type].h };
	});
}

/** Keyboard move/resize: shift a box by whole cells, kept on the grid and above its minimums. */
export function nudgeBox(box, dx, dy, dw, dh, cols) {
	const w = Math.max(box.minW ?? 1, Math.min(cols, box.w + dw));
	const h = Math.max(box.minH ?? 1, box.h + dh);
	return { x: Math.max(0, Math.min(cols - w, box.x + dx)), y: Math.max(0, box.y + dy), w, h };
}

/** Widgets not on the grid yet, for the Add widget menu. */
export function addable(items) {
	const ids = new Set(items.map((i) => i.id));
	/** @type {{id: string, type: string, kind?: string, label: string}[]} */
	const out = Object.keys(WIDGETS)
		.filter((t) => t !== 'move' && !ids.has(t))
		.map((type) => ({ id: type, type, label: WIDGETS[type].title }));
	for (const kind of MOVE_KINDS) if (!ids.has(`move-${kind}`)) out.push({ id: `move-${kind}`, type: 'move', kind, label: `${moveLabel(kind)} move` });
	return out;
}

export const moveLabel = (kind) => kind[0].toUpperCase() + kind.slice(1);

/** Compass keys (F3g): each adds that move's first pick that isn't queued yet. */
export const MOVE_KEYS = { ArrowUp: 'lift', ArrowDown: 'drop', ArrowLeft: 'pivot', ArrowRight: 'curveball', h: 'hold', t: 'toward' };
export const KEY_LABEL = { lift: '↑', drop: '↓', pivot: '←', curveball: '→', hold: 'H', toward: 'T' };

/** The key a keydown means, or null when the host is typing or using a modifier. */
export function moveForKey(e) {
	if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return null;
	const el = /** @type {any} */ (e.target);
	if (el?.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el?.tagName)) return null;
	return MOVE_KEYS[e.key.length === 1 ? e.key.toLowerCase() : e.key] ?? null;
}

/** Move summaries, reused from iOS. */
export const MOVE_SUMMARY = {
	hold: 'Keep the vibe',
	lift: 'Raise the energy',
	drop: 'Give the room a breather',
	pivot: 'Change genre, keep a thread',
	curveball: 'Something unexpected',
	toward: 'Next step toward your goal',
	drift: 'Somewhere new',
	similar: 'Like this one'
};
