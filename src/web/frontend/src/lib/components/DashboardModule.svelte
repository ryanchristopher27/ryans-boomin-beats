<script>
	// A Profile module (R5): glass card, 52px header with expand, own scroll.
	import Icon from './Icon.svelte';

	export let title = '';
	export let expanded = false;
	export let onToggleExpand = () => {};
</script>

<section class="module glass" class:expanded>
	<div class="head">
		<h2>{title}</h2>
		<button class="icon-btn" on:click={onToggleExpand} title={expanded ? 'Show all modules' : 'Expand'} aria-label={expanded ? `Show all modules` : `Expand ${title}`} aria-expanded={expanded}>
			<Icon name={expanded ? 'collapse' : 'expand'} size={15} />
		</button>
	</div>
	<div class="body">
		<slot />
	</div>
</section>

<style>
	.module {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		border-radius: 16px;
		animation: bbin 0.4s var(--ease) both;
	}

	.head {
		flex: none;
		height: 52px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 12px 0 18px;
		border-bottom: 1px solid var(--border-subtle);
	}

	h2 {
		margin: 0;
		font-size: calc(15px * var(--text-scale, 1));
		font-weight: 600;
	}

	.head .icon-btn {
		width: 30px;
		height: 30px;
	}

	.body {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 6px;
	}
</style>
