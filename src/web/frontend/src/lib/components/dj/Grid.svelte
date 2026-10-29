<script>
	// The gridstack wrapper (W2). Svelte owns each item's DOM and its widget;
	// gridstack only positions them. Adding an item renders it, then hands the
	// node to gridstack (`makeWidget`); removing un-registers it first.
	import { onDestroy, onMount, tick } from 'svelte';
	import 'gridstack/dist/gridstack.min.css';
	import { COLUMNS, WIDGETS, completeSaved, nudgeBox } from '$lib/dj/layout.js';

	export let items = [];
	export let editing = false;
	/** Desktop only (12 columns): rows stretch so the grid fills the window
	    and each widget scrolls on its own (R6, the handoff's no-page-scroll). */
	export let fill = false;
	/** The widget that takes a full-width row first when the grid goes below desktop. */
	export let lead = null;

	const CELL = 48;
	const MIN_CELL = 32;
	const BOTTOM_GAP = 20;
	/** Tablet and phone panels cap at this many rows (336px) and scroll inside. */
	const NARROW_MAX_H = 7;
	/** Now playing needs a little more on a phone to stack its art above the title. */
	const PHONE_ART_H = 8;

	let el;
	/** @type {any} */
	let grid = null;

	onMount(async () => {
		const { GridStack } = await import('gridstack');
		const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
		grid = GridStack.init(
			{
				column: COLUMNS,
				cellHeight: CELL,
				margin: 5,
				float: false,
				animate: !reduced,
				staticGrid: !editing,
				handle: '.widget-handle',
				// The brief's breakpoints are applied below, once the widgets are placed at
				// 12 columns: given here, gridstack would clamp them into a narrow
				// window's columns before `stack` could lay them out.
				// Below 720px a 3-column widget would be under 360px, so widgets
				// stack in one column instead.
			},
			el
		);
		// 12 columns from 1200px, 8 from 960, 6 from 720, else 1, measured on the grid
		// itself (a 1280px window leaves ~1245px after padding and the scrollbar) so
		// the Playlists panel counts. Widest first: gridstack matches in order. A
		// breakpoint's `w` is inclusive. columnMax is required: with several
		// breakpoints gridstack doesn't default it, and growing past the widest one
		// then never returned to 12.
		grid.updateOptions({
			columnOpts: {
				columnMax: COLUMNS,
				layout: 'list',
				breakpoints: [
					{ w: 1199, c: 8 },
					{ w: 959, c: 6, layout: stack },
					{ w: 719, c: 1, layout: stack }
				]
			}
		});
		grid.on('change added removed', fit);
		fit();
		addEventListener('resize', onResize);
	});

	onDestroy(() => {
		removeEventListener('resize', onResize);
		clearTimeout(resizeTimer);
		grid?.destroy(false);
	});

	/**
	 * Tablet (6 columns) and phone (1): the page scrolls instead of the grid. Keeps
	 * the items' order; `lead` goes first at full width, Next moves is full width,
	 * everything else takes half a row (a whole one on a phone). Heights are capped.
	 */
	function stack(column, _prev, _placed, nodes) {
		const order = new Map(items.map((it, i) => [it.id, i]));
		const rank = (n) => (n.id === lead ? -1 : order.get(n.id) ?? 0);
		let x = 0;
		let y = 0;
		let rowH = 0;
		for (const n of [...nodes].sort((a, b) => rank(a) - rank(b))) {
			n.w = column === 1 || n.id === lead || n.id === 'moves' ? column : column / 2;
			n.h = n.id === 'nowPlaying' && column === 1 ? PHONE_ART_H : Math.min(n.h, NARROW_MAX_H);
			if (x + n.w > column) {
				y += rowH;
				x = rowH = 0;
			}
			n.x = x;
			n.y = y;
			x += n.w;
			rowH = Math.max(rowH, n.h);
			_placed.push(n);
		}
	}

	/** Stretch the rows to the window's height on desktop; fixed 48px otherwise. */
	function fit() {
		if (!grid) return;
		const rows = Math.max(1, ...grid.engine.nodes.map((n) => n.y + n.h));
		const top = el.getBoundingClientRect().top + scrollY;
		const room = innerHeight - top - BOTTOM_GAP;
		const cell = fill && grid.getColumn() === COLUMNS ? Math.max(MIN_CELL, Math.floor(room / rows)) : CELL;
		if (cell !== grid.getCellHeight()) grid.cellHeight(cell);
	}
	$: if (grid) (fill, fit());

	// gridstack changes its column count on its own (throttled) resize, so fit after it.
	let resizeTimer;
	function onResize() {
		clearTimeout(resizeTimer);
		resizeTimer = setTimeout(fit, 200);
	}

	$: grid?.setStatic(!editing);

	/** gridstack reads an item's position from its gs-* attributes. */
	const gsAttrs = (item) => ({
		'gs-id': item.id,
		'gs-x': item.x,
		'gs-y': item.y,
		'gs-w': item.w,
		'gs-h': item.h,
		'gs-min-w': WIDGETS[item.type].minW,
		'gs-min-h': WIDGETS[item.type].minH
	});

	const nodeFor = (id) => el.querySelector(`[gs-id="${CSS.escape(id)}"]`);

	/** Positions as 12-column coordinates, whatever the current breakpoint. */
	export function save() {
		const saved = /** @type {any[]} */ (grid.save(false, false, undefined, COLUMNS));
		return completeSaved(saved, items, new Map(grid.engine.nodes.map((n) => [n.id, n])));
	}

	export async function add(item) {
		items = [...items, item];
		await tick();
		// Options replace the gs-* attributes rather than merging, so pass them all.
		const { 'gs-id': id, 'gs-w': w, 'gs-h': h, 'gs-min-w': minW, 'gs-min-h': minH } = gsAttrs(item);
		grid.makeWidget(nodeFor(item.id), { id, w, h, minW, minH, autoPosition: true });
	}

	/** Keyboard move/resize: shift by whole cells, kept on the grid and above minimums. */
	export function nudge(id, dx, dy, dw, dh) {
		const node = grid.engine.nodes.find((n) => n.id === id);
		if (!node) return;
		grid.update(node.el, nudgeBox(node, dx, dy, dw, dh, grid.getColumn()));
		return grid.engine.nodes.find((n) => n.id === id);
	}

	export function remove(id) {
		grid.removeWidget(nodeFor(id), false);
		items = items.filter((i) => i.id !== id);
	}
</script>

<div class="grid-stack" bind:this={el}>
	{#each items as item (item.id)}
		<div class="grid-stack-item" {...gsAttrs(item)}>
			<div class="grid-stack-item-content">
				<slot {item} />
			</div>
		</div>
	{/each}
</div>

<style>
	/* Never put CSS `zoom` on the grid or any ancestor: gridstack then
	   misplaces widgets after a resize and drag stops working (R0 spike). */
	.grid-stack {
		margin: 0 -5px;
	}

	/* gridstack's content box is inset by its margin; widgets fill it. */
	.grid-stack :global(.grid-stack-item-content) {
		overflow: visible !important;
	}

	/* The snap preview while dragging. */
	.grid-stack :global(.grid-stack-placeholder > .placeholder-content) {
		background: rgba(var(--accent-rgb), 0.06);
		border: 1px dashed rgba(var(--accent-rgb), 0.5);
		border-radius: var(--radius);
	}

	.grid-stack :global(.ui-resizable-se) {
		opacity: 0.7;
	}
</style>
