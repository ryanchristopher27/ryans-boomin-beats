<script>
	// The gridstack wrapper (W2). Svelte owns each item's DOM and its widget;
	// gridstack only positions them. Adding an item renders it, then hands the
	// node to gridstack (`makeWidget`); removing un-registers it first.
	import { onDestroy, onMount, tick } from 'svelte';
	import 'gridstack/dist/gridstack.min.css';
	import { COLUMNS, WIDGETS, completeSaved, nudgeBox } from '$lib/dj/layout.js';

	export let items = [];
	export let editing = false;

	let el;
	/** @type {any} */
	let grid = null;

	onMount(async () => {
		const { GridStack } = await import('gridstack');
		const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
		grid = GridStack.init(
			{
				column: COLUMNS,
				cellHeight: 48,
				margin: 5,
				float: false,
				animate: !reduced,
				staticGrid: !editing,
				handle: '.widget-handle',
				// The brief's breakpoints: 12 cols at >= 1280px, 8 at 1024-1279, 6 below.
				// A breakpoint's `w` is inclusive (applies at widths <= w).
				columnOpts: {
					breakpointForWindow: true,
					layout: 'list',
					breakpoints: [
						{ w: 1023, c: 6 },
						{ w: 1279, c: 8 }
					]
				}
			},
			el
		);
	});

	onDestroy(() => grid?.destroy(false));

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
