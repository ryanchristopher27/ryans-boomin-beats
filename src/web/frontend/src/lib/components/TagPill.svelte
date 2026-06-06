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
		height: 28px;
		padding: 0 12px;
		background: none;
		border: 1px solid var(--color-light-blue);
		border-radius: 14px;
		color: var(--color-light-blue);
		font-size: 0.75rem;
		cursor: pointer;
		opacity: 0.6;
		transition: all 0.15s;
		white-space: nowrap;
	}

	.tag-pill:hover {
		opacity: 1;
		border-color: var(--color-purple);
		color: var(--color-purple);
	}

	.tag-pill.selected {
		background-color: var(--color-light-blue);
		color: var(--color-dark-gray);
		opacity: 1;
		font-weight: 700;
	}

	.tag-pill.selected:hover {
		background-color: var(--color-purple);
		border-color: var(--color-purple);
		color: white;
	}
</style>
