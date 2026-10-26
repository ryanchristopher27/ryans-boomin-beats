<script>
	// Chrome shared by every DJ widget: a 40px header (title, actions) over a
	// scrolling body. In edit mode the header becomes the drag handle and gains
	// a remove button.
	import Icon from './Icon.svelte';

	export let title;
	export let editing = false;
	/** @type {(() => void) | null} */
	export let onRemove = null;
	export let ambient = '';
</script>

<section class="widget" class:editing style:--ambient={ambient || null} aria-label={title}>
	<header class="widget-head" class:widget-handle={editing}>
		{#if editing}<span class="grip"><Icon name="grip" size={16} /></span>{/if}
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
		background: var(--ambient, var(--surface-1));
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		overflow: hidden;
		transition: background-color 400ms cubic-bezier(0.16, 1, 0.3, 1);
	}

	.widget.editing {
		outline: 1px dashed rgba(var(--accent-rgb), 0.45);
		outline-offset: -1px;
	}

	.widget-head {
		flex: none;
		height: 40px;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 0 8px 0 14px;
		border-bottom: 1px solid var(--border-subtle);
	}

	.widget-handle {
		cursor: grab;
	}

	.grip {
		color: var(--text-subtle);
		margin-left: -4px;
	}

	h2 {
		margin: 0;
		font-size: 14px;
		font-weight: 600;
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

	@media (prefers-reduced-motion: reduce) {
		.widget {
			transition: none;
		}
	}
</style>
