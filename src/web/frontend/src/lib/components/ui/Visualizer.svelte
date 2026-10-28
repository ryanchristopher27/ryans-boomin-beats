<script>
	// Now playing's visualizer (bbeq): a row of gradient bars that move while
	// music plays and rest low when paused. Decorative; it doesn't read audio.
	export let count = 40;
	export let height = 30;
	export let playing = true;

	// Fixed pseudo-random timings, so the bars look organic but render the same.
	const bars = Array.from({ length: count }, (_, i) => ({
		speed: 0.5 + ((i * 37) % 45) / 100,
		delay: -(((i * 53) % 90) / 100)
	}));
</script>

<div class="viz" class:paused={!playing} style:height="{height}px" aria-hidden="true">
	{#each bars as b}
		<span class="playback-anim" style:animation-duration="{b.speed}s" style:animation-delay="{b.delay}s" />
	{/each}
</div>

<style>
	.viz {
		display: flex;
		align-items: flex-end;
		gap: 3px;
		-webkit-mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent);
		mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent);
	}

	span {
		flex: 1;
		height: 100%;
		border-radius: 2px;
		background: linear-gradient(to top, var(--accent), var(--accent-2));
		transform-origin: bottom;
		animation: bbeq 0.7s ease-in-out infinite alternate;
	}

	.paused span {
		animation-play-state: paused;
		opacity: 0.5;
	}
</style>
