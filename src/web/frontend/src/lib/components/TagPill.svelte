<script>
	export let tag = '';
	export let selected = false;
	export let onToggle = () => {};
</script>

<button
	class="tag-pill"
	class:selected
	on:click={() => { selected = !selected; onToggle(tag, selected); }}
>
	{tag}
</button>

<style>
	.tag-pill {
		height: 30px;
		padding: 0 14px;
		background: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: 15px;
		color: var(--text-muted);
		font-size: 0.75rem;
		cursor: pointer;
		transition: border-color var(--transition), color var(--transition),
			background-color var(--transition);
		white-space: nowrap;
	}

	.tag-pill:hover {
		border-color: var(--accent);
		color: var(--text-primary);
	}

	.tag-pill.selected {
		background-color: var(--accent);
		border-color: var(--accent);
		color: var(--surface-0);
		font-weight: 700;
	}

	.tag-pill.selected:hover {
		background-color: var(--accent-hover);
		border-color: var(--accent-hover);
	}
</style>
