<script>
	// The fixed mini player (W3) on every page but the DJ page: art, title,
	// progress, transport, the current goal and a way back to the DJ. Hidden
	// when signed out or nothing is playing. Not customizable, by design.
	import { onDestroy, onMount } from 'svelte';
	import { page as route } from '$app/stores';
	import { access_token, playlistsPanelOpen } from '../../../stores.js';
	import { getDJ } from '$lib/dj/instance.js';
	import Icon from './Icon.svelte';

	const dj = /** @type {any} */ (getDJ());
	const { player, doc } = dj;

	let progress = 0;
	let timer;
	onMount(() => (timer = setInterval(() => (progress = dj.progressMs()), 1000)));
	onDestroy(() => clearInterval(timer));

	$: state = $player.state;
	$: track = state?.active ? state.track : null;
	$: visible = !!$access_token && !!track && !$route.url.pathname.startsWith('/dj');
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
</script>

{#if visible && track}
	<!-- Holds the bar's height in the page flow, so content never hides under it. -->
	<div class="spacer" aria-hidden="true" />
	<div class="mini" class:panel-open={$playlistsPanelOpen} role="region" aria-label="Now playing">
		<div class="progress" aria-hidden="true"><div class="fill" style:transform="scaleX({pct / 100})" /></div>
		<img src={track.image} alt="" width="40" height="40" />
		<div class="text">
			<p class="title">{track.title}</p>
			<p class="artist">{track.artists.join(', ')}</p>
		</div>
		<div class="transport">
			<button class="icon-btn" on:click={() => dj.send('previous')} disabled={!allows('skipping_prev')} aria-label="Previous"><Icon name="prev" size={18} /></button>
			{#if state.is_playing}
				<button class="play" on:click={() => dj.send('pause')} disabled={!allows('pausing')} aria-label="Pause"><Icon name="pause" size={18} /></button>
			{:else}
				<button class="play" on:click={() => dj.send('play')} disabled={!allows('resuming')} aria-label="Play"><Icon name="play" size={18} /></button>
			{/if}
			<button class="icon-btn" on:click={() => dj.send('next')} disabled={!allows('skipping_next')} aria-label="Next"><Icon name="next" size={18} /></button>
		</div>
		<div class="end">
			{#if goalLabel}<span class="goal"><Icon name={goal.kind === 'drift' ? 'drift' : 'toward'} size={14} /> {goalLabel}</span>{/if}
			<a class="open" href="/dj/">Open DJ</a>
		</div>
	</div>
{/if}

<style>
	.spacer {
		flex: none;
		height: 80px;
	}

	.mini {
		position: fixed;
		left: var(--primary-spacing);
		right: var(--primary-spacing);
		bottom: var(--primary-spacing);
		min-width: 770px;
		z-index: 40;
		height: 64px;
		box-sizing: border-box;
		display: grid;
		grid-template-columns: 40px minmax(0, 1fr) auto minmax(0, 1fr);
		align-items: center;
		gap: 12px;
		padding: 0 16px 0 12px;
		background: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		overflow: hidden;
		color-scheme: dark;
	}

	/* Beside the docked Playlists panel, not under it. */
	.mini.panel-open {
		right: calc(var(--panel-width) + var(--primary-spacing) * 2);
		min-width: 0;
	}

	.progress {
		position: absolute;
		left: 0;
		right: 0;
		top: 0;
		height: 2px;
		background: rgba(255, 255, 255, 0.08);
	}

	.fill {
		height: 100%;
		background: var(--accent);
		transform-origin: left;
		transition: transform 1s linear;
	}

	img {
		border-radius: 4px;
		object-fit: cover;
		background: var(--surface-2);
	}

	.text {
		min-width: 0;
	}

	p {
		margin: 0;
		line-height: 1.3;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.title {
		font-size: 14px;
		font-weight: 500;
	}

	.artist {
		font-size: 12px;
		color: var(--text-muted);
	}

	.transport {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.icon-btn,
	.play {
		display: inline-grid;
		place-items: center;
		border: none;
		cursor: pointer;
		padding: 0;
	}

	.icon-btn {
		width: 32px;
		height: 32px;
		border-radius: var(--radius-sm);
		background: none;
		color: var(--text-muted);
		transition: color 150ms cubic-bezier(0.16, 1, 0.3, 1), background-color 150ms cubic-bezier(0.16, 1, 0.3, 1);
	}

	.icon-btn:hover:not(:disabled) {
		color: var(--text-primary);
		background: rgba(255, 255, 255, 0.08);
	}

	.play {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: var(--accent);
		color: #0b0b0b;
	}

	button:disabled {
		opacity: 0.4;
		cursor: default;
	}

	button:focus-visible,
	.open:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}

	.end {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 14px;
		min-width: 0;
	}

	.goal {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: #c49bff;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
	}

	.open {
		font-size: 13px;
		font-weight: 500;
		white-space: nowrap;
	}

	@media (prefers-reduced-motion: reduce) {
		.fill,
		.icon-btn {
			transition: none;
		}
	}
</style>
