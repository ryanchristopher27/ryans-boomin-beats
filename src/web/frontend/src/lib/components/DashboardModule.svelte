<script>
	export let title = '';
	export let expanded = false;
	export let onToggleExpand = () => {};
	export let scroll = true; // false → module sizes to its content (no internal scroll)
	export let fullHeight = false; // true → fills the viewport height (with internal scroll)
</script>

<section class="module" class:expanded class:scroll class:full-height={fullHeight}>
	<div class="module-head">
		<span class="module-title">{title}</span>
		<button
			class="expand-btn"
			on:click={onToggleExpand}
			title={expanded ? 'Minimize' : 'Expand'}
			aria-label={expanded ? 'Minimize' : 'Expand'}
		>
			{expanded ? '⤡' : '⤢'}
		</button>
	</div>
	<div class="module-body">
		<slot />
	</div>
</section>

<style>
	.module {
		display: flex;
		flex-direction: column;
		min-height: 0;
		overflow: hidden;
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-lg);
	}

	.module.scroll:not(.expanded) {
		height: 440px;
	}

	.module.scroll.full-height:not(.expanded) {
		height: calc(100vh - 300px);
		min-height: 440px;
	}

	.module.expanded {
		height: calc(100vh - 200px);
	}

	.module-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 14px 16px 10px;
		flex-shrink: 0;
	}

	.module-title {
		font-size: 1.3rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.expand-btn {
		flex-shrink: 0;
		width: 30px;
		height: 30px;
		background: none;
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		color: var(--text-muted);
		font-size: 0.9rem;
		cursor: pointer;
		transition: border-color var(--transition), color var(--transition);
	}

	.expand-btn:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.module-body {
		flex: 1;
		min-height: 0;
		padding: 0 8px 12px;
	}

	.module.scroll .module-body,
	.module.expanded .module-body {
		overflow-y: auto;
	}
</style>
