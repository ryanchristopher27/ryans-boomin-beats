<script>
	// Compact horizontal bar chart. Pass items as [{ label, value }].
	export let items = [];
	export let max = null;
	export let valueSuffix = '';

	$: effectiveMax = max ?? Math.max(1, ...items.map((i) => i.value || 0));
</script>

{#if items.length}
	<div class="bars">
		{#each items as item (item.label)}
			<div class="bar-row">
				<span class="bar-label" title={item.label}>{item.label}</span>
				<span class="bar-track">
					<span class="bar-fill" style="width: {Math.max(2, (100 * (item.value || 0)) / effectiveMax)}%"></span>
				</span>
				<span class="bar-value">{item.value}{valueSuffix}</span>
			</div>
		{/each}
	</div>
{/if}

<style>
	.bars {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.bar-row {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.bar-label {
		width: 38%;
		flex-shrink: 0;
		font-size: 0.78rem;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		text-align: right;
	}

	.bar-track {
		flex: 1;
		min-width: 0;
		height: 10px;
		background-color: var(--surface-2);
		border-radius: 5px;
		overflow: hidden;
	}

	.bar-fill {
		display: block;
		height: 100%;
		border-radius: 5px;
		background: var(--brand-gradient);
	}

	.bar-value {
		width: 34px;
		flex-shrink: 0;
		font-size: 0.74rem;
		font-weight: 600;
		color: var(--text-subtle);
		text-align: right;
	}
</style>
