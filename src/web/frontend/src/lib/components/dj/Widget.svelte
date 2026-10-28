<script>
	// Chrome shared by every DJ widget: a 40px header (title, actions) over a
	// scrolling body. In edit mode the header becomes the drag handle and gains
	// a remove button.
	import Icon from '../Icon.svelte';

	export let title;
	export let editing = false;
	/** @type {(() => void) | null} */
	export let onRemove = null;
	/** Keyboard move/resize in edit mode: (dx, dy, dw, dh) in grid cells. */
	/** @type {((dx: number, dy: number, dw: number, dh: number) => void) | null} */
	export let onNudge = null;

	const STEP = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };

	function onKey(e) {
		const step = STEP[e.key];
		if (!step || !onNudge) return;
		e.preventDefault();
		const [x, y] = step;
		if (e.shiftKey) onNudge(0, 0, x, y);
		else onNudge(x, y, 0, 0);
	}
</script>

<section class="widget" class:editing aria-label={title}>
	<header class="widget-head" class:widget-handle={editing}>
		{#if editing}
			<button class="grip" on:keydown={onKey} aria-label="Move or resize {title}. Arrow keys move it; Shift and arrow keys resize it.">
				<Icon name="grip" size={16} />
			</button>
		{/if}
		<h2>{title}</h2>
		<slot name="badge" />
		<div class="actions">
			{#if !editing}<slot name="actions" />{/if}
			{#if editing && onRemove}
				<button class="icon-btn" on:click={onRemove} aria-label="Remove {title}" title="Remove">
					<Icon name="x" size={16} />
				</button>
			{/if}
		</div>
	</header>
	<div class="body">
		<slot />
	</div>
</section>

<style>
	.widget {
		height: 100%;
		display: flex;
		flex-direction: column;
		background: var(--glass);
		-webkit-backdrop-filter: var(--glass-blur);
		backdrop-filter: var(--glass-blur);
		border: 1px solid var(--border-subtle);
		border-radius: 16px;
		overflow: hidden;
	}

	.widget.editing {
		outline: 1px dashed rgba(var(--accent-rgb), 0.45);
		outline-offset: -1px;
	}

	.widget-head {
		flex: none;
		height: 44px;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 0 8px 0 16px;
		border-bottom: 1px solid var(--border-subtle);
	}

	.widget-handle {
		cursor: grab;
	}

	.grip {
		display: inline-grid;
		place-items: center;
		width: 24px;
		height: 24px;
		margin-left: -6px;
		padding: 0;
		border: none;
		border-radius: 6px;
		background: none;
		color: var(--text-muted);
		cursor: grab;
	}

	.grip:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 1px;
	}

	h2 {
		margin: 0;
		font-size: calc(14px * var(--text-scale, 1));
		font-weight: 500;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.actions {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 2px;
	}

	.body {
		flex: 1;
		min-height: 0;
		overflow: auto;
		overscroll-behavior: contain;
	}
</style>
