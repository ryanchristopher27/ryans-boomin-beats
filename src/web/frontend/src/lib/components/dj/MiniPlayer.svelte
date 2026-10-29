<script>
	// The fixed mini player (W3, restyled R1) on every page but the DJ page: art,
	// title, progress, transport, the current goal and a way back to the DJ.
	// Hidden when signed out or nothing is playing. Not customizable, by design.
	import { onDestroy, onMount } from 'svelte';
	import { page as route } from '$app/stores';
	import { access_token } from '../../../stores.js';
	import { getDJ } from '$lib/dj/instance.js';
	import Icon from '../Icon.svelte';
	import Bars from '../ui/Bars.svelte';

	const dj = /** @type {any} */ (getDJ());
	const { player, doc } = dj;

	let progress = 0;
	let timer;
	onMount(() => (timer = setInterval(() => (progress = dj.progressMs()), 1000)));
	onDestroy(() => {
		clearInterval(timer);
		document.documentElement.style.removeProperty('--mini-h');
	});

	$: state = $player.state;
	$: track = state?.active ? state.track : null;
	$: visible = !!$access_token && !!track && !$route.url.pathname.startsWith('/dj');
	// The dock and toasts sit above the bar while it shows.
	$: document.documentElement.style.setProperty('--mini-h', visible ? '64px' : '0px');
	$: playing = !!state?.is_playing;
	$: pct = track?.duration_ms ? Math.min(100, (progress / track.duration_ms) * 100) : 0;
	$: allows = (a) => !(state?.disallows ?? []).includes(a);
	$: goal = $doc.options.goal;
	$: goalLabel = !goal
		? ''
		: goal.kind === 'destination'
		? `Toward ${goal.destination}`
		: goal.kind === 'drift'
		? 'Drift'
		: `${{ build: 'Build to peak', wind_down: 'Wind down', peak_cool: 'Peak then cool' }[goal.shape]} · ${goal.minutes} min`;

	const clock = (ms) => {
		const s = Math.max(0, Math.floor((ms ?? 0) / 1000));
		return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
	};
</script>

{#if visible && track}
	<!-- Holds the bar's height in the page flow, so content never hides under it. -->
	<div class="spacer" aria-hidden="true" />
	<div class="mini" role="region" aria-label="Now playing">
		<div class="progress" aria-hidden="true"><div class="fill" style:transform="scaleX({pct / 100})" /></div>
		<div class="song">
			<div class="cover" class:playing>
				{#key track.id}
					<img class="glow playback-anim" src={track.image} alt="" aria-hidden="true" />
					<img class="art" src={track.image} alt="" width="40" height="40" />
				{/key}
			</div>
			<div class="text">
				<p class="title">{#if playing}<Bars count={3} height={10} />{/if}<span>{track.title}</span></p>
				<p class="artist">{track.artists.join(', ')}</p>
			</div>
		</div>
		<div class="transport">
			<button class="round" on:click={() => dj.send('previous')} disabled={!allows('skipping_prev')} aria-label="Previous"><Icon name="prev" size={16} filled /></button>
			{#if playing}
				<button class="play" on:click={() => dj.send('pause')} disabled={!allows('pausing')} aria-label="Pause"><Icon name="pause" size={15} filled /></button>
			{:else}
				<button class="play" on:click={() => dj.send('play')} disabled={!allows('resuming')} aria-label="Play"><Icon name="play" size={15} filled /></button>
			{/if}
			<button class="round" on:click={() => dj.send('next')} disabled={!allows('skipping_next')} aria-label="Next"><Icon name="next" size={16} filled /></button>
		</div>
		<div class="end">
			{#if goalLabel}<span class="goal">Goal <span>{goalLabel}</span></span>{/if}
			<span class="time mono">{clock(progress)} / {clock(track.duration_ms)}</span>
			<a class="btn small" href="/dj/">Open DJ</a>
		</div>
	</div>
{/if}

<style>
	.spacer {
		flex: none;
		height: 64px;
	}

	.mini {
		position: fixed;
		left: 0;
		right: 0;
		bottom: var(--tab-h, 0px);
		z-index: 40;
		height: 64px;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
		align-items: center;
		gap: 16px;
		padding: 0 16px;
		border-top: 1px solid var(--border-subtle);
		background: rgba(13, 13, 16, 0.88);
		-webkit-backdrop-filter: blur(20px);
		backdrop-filter: blur(20px);
	}

	.progress {
		position: absolute;
		left: 0;
		right: 0;
		top: -1px;
		height: 2px;
		background: rgba(255, 255, 255, 0.04);
	}

	.fill {
		height: 100%;
		background: linear-gradient(90deg, var(--accent), var(--accent-2));
		box-shadow: 0 0 10px rgba(var(--accent-rgb), 0.7);
		transform-origin: left;
		transition: transform 1s linear;
	}

	.song {
		display: flex;
		align-items: center;
		gap: 12px;
		min-width: 0;
	}

	.cover {
		position: relative;
		flex: none;
		width: 40px;
		height: 40px;
	}

	.art {
		position: relative;
		display: block;
		width: 40px;
		height: 40px;
		border-radius: 6px;
		object-fit: cover;
		background: var(--surface-2);
		animation: bbpop 0.55s var(--ease);
	}

	/* A blurred copy of the cover breathes behind it while playing. */
	.glow {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		border-radius: 6px;
		filter: blur(10px) saturate(1.4);
		opacity: 0.2;
		transition: opacity 0.4s var(--ease);
	}

	.cover.playing .glow {
		opacity: 0.75;
		animation: bbglow 4.5s ease-in-out infinite;
	}

	:global([data-motion="on"]) .cover.playing .art {
		animation: bbpop 0.55s var(--ease), bbbreath 5s ease-in-out 0.55s infinite;
	}

	.text {
		min-width: 0;
	}

	p {
		margin: 0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.title {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: calc(14px * var(--text-scale, 1));
		font-weight: 500;
	}

	.title span {
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.artist {
		font-size: calc(12px * var(--text-scale, 1));
		color: rgba(243, 243, 245, 0.55);
	}

	.transport {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.round,
	.play {
		display: grid;
		place-items: center;
		padding: 0;
		border: none;
		border-radius: 50%;
		cursor: pointer;
	}

	.round {
		width: 34px;
		height: 34px;
		background: transparent;
		color: var(--text-primary);
		transition: background-color var(--transition);
	}

	.round:hover:not(:disabled) {
		background: var(--hover);
	}

	.play {
		width: 38px;
		height: 38px;
		background: #f3f3f5;
		color: #0a0a0c;
	}

	button:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.end {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 14px;
		min-width: 0;
		white-space: nowrap;
	}

	.goal {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		font-size: calc(12px * var(--text-scale, 1));
		color: rgba(243, 243, 245, 0.5);
	}

	.goal span {
		color: var(--accent-2-text);
	}

	.time {
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.end .btn {
		border-color: var(--border-control);
		color: var(--text-primary);
	}

	/* Phone: song and transport only. */
	:global([data-bp='phone']) .mini {
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 8px;
		padding: 0 8px 0 12px;
	}
	:global([data-bp='phone']) .end {
		display: none;
	}
</style>
