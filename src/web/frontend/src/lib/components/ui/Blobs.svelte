<script>
	// The redesign's drifting colour (bbdrift): a radial wash plus three blurred
	// blobs from one hue. `moving` pauses them (the DJ: only while playing);
	// `hero` fades them out down the page (Profile). Decorative only.
	export let hue = 235;
	export let moving = true;
	export let hero = false;
</script>

<div class="blobs" class:hero class:still={!moving} style:--h={hue} aria-hidden="true">
	<div class="wash" />
	<span class="b1" />
	<span class="b2" />
	<span class="b3" />
</div>

<style>
	.blobs {
		position: absolute;
		inset: 0;
		overflow: hidden;
		pointer-events: none;
		z-index: 0;
	}

	.hero {
		bottom: auto;
		height: 640px;
		-webkit-mask-image: linear-gradient(#000 35%, transparent);
		mask-image: linear-gradient(#000 35%, transparent);
	}

	.wash {
		position: absolute;
		inset: 0;
		background: radial-gradient(90% 70% at 15% 0%, oklch(0.27 0.07 var(--h)) 0%, transparent 65%),
			radial-gradient(70% 60% at 95% 100%, oklch(0.22 0.06 calc(var(--h) + 60)) 0%, transparent 60%);
		transition: background 1.5s;
	}

	span {
		position: absolute;
		border-radius: 50%;
		filter: blur(100px);
		opacity: 0.26;
		animation: bbdrift 22s ease-in-out infinite alternate;
		transition: background 1.5s;
		will-change: transform;
	}

	.b1 {
		left: -10%;
		top: -25%;
		width: 48vw;
		height: 48vw;
		background: oklch(0.5 0.13 var(--h));
	}

	.b2 {
		left: 55%;
		top: 5%;
		width: 40vw;
		height: 40vw;
		background: oklch(0.5 0.13 calc(var(--h) + 50));
		animation-duration: 26s;
		animation-delay: -6s;
	}

	.b3 {
		left: 20%;
		top: 55%;
		width: 36vw;
		height: 36vw;
		background: oklch(0.5 0.13 calc(var(--h) + 320));
		animation-duration: 30s;
		animation-delay: -12s;
	}

	.still span {
		animation-play-state: paused;
	}
</style>
