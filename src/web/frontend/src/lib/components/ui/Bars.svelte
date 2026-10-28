<script>
	// The "playing" equaliser bars (bbeq). Decorative; still when `paused`.
	export let count = 3;
	export let height = 12;
	export let paused = false;
	export let color = 'var(--accent)';

	// Fixed, uneven timings so neighbouring bars never move in step.
	const SPEEDS = [0.62, 0.81, 0.53, 0.95, 0.7, 0.58, 0.88];
</script>

<span class="bars" class:paused style:height="{height}px" style:--bar={color} aria-hidden="true">
	{#each Array(count) as _, i}
		<span style:animation-duration="{SPEEDS[i % SPEEDS.length]}s" style:animation-delay="-{(i * 0.37) % 1}s" />
	{/each}
</span>

<style>
	.bars {
		flex: none;
		display: inline-flex;
		align-items: flex-end;
		gap: 2px;
	}

	.bars span {
		width: 2px;
		height: 100%;
		border-radius: 1px;
		background: var(--bar);
		transform-origin: bottom;
		animation: bbeq 0.7s ease-in-out infinite alternate;
	}

	.paused span {
		animation-play-state: paused;
	}
</style>
