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
	recent: { title: 'Recently played', minW: 3, minH: 3, w: 3, h: 6 }
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

/** Move summaries, reused from iOS. */
export const MOVE_SUMMARY = {
	hold: 'Keep the vibe',
	lift: 'Raise the energy',
	drop: 'Give the room a breather',
	pivot: 'Change genre, keep a thread',
	curveball: 'Something unexpected',
	toward: 'Next step toward your goal',
	drift: 'Somewhere new'
};
