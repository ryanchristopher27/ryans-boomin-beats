<script>
	// A single row of intensity-shaded cells. Pass cells as
	// [{ value, label?, tick? }] — `label` is the hover title, `tick` the axis label.
	export let cells = [];
	export let max = null;

	$: effectiveMax = max ?? Math.max(1, ...cells.map((c) => c.value || 0));
	function intensity(v) {
		return Math.max(0, Math.min(1, (v || 0) / effectiveMax));
	}
</script>

{#if cells.length}
	<div class="heatmap">
		<div class="cells">
			{#each cells as c}
				<div
					class="cell"
					style="background: rgba(var(--accent-rgb), {0.08 + 0.92 * intensity(c.value)})"
					title={`${c.label ?? ''}: ${c.value}`}
				></div>
			{/each}
		</div>
		<div class="ticks">
			{#each cells as c}
				<span class="tick">{c.tick ?? ''}</span>
			{/each}
		</div>
	</div>
{/if}

<style>
	.cells {
		display: flex;
		gap: 3px;
	}

	.cell {
		flex: 1;
		min-width: 0;
		height: 30px;
		border-radius: 4px;
	}

	.ticks {
		display: flex;
		gap: 3px;
		margin-top: 4px;
	}

	.tick {
		flex: 1;
		min-width: 0;
		text-align: center;
		font-size: 0.62rem;
		color: var(--text-subtle);
	}
</style>
