<script>
	import { onDestroy, onMount } from 'svelte';
	import Icon from './Icon.svelte';

	/** @type {any} */
	export let dj;

	const { player, doc } = dj;
	let progress = 0;
	// A short widget (the Board preset's banner) lays out as one row.
	let height = 400;
	$: compact = height < 260;
	let timer;

	onMount(() => (timer = setInterval(() => (progress = dj.progressMs()), 500)));
	onDestroy(() => clearInterval(timer));

	$: state = $player.state;
	$: track = state?.track;
	$: progress = state ? dj.progressMs() : 0;
	$: pct = track?.duration_ms ? Math.min(100, (progress / track.duration_ms) * 100) : 0;
	$: allows = (a) => !(state?.disallows ?? []).includes(a);
	$: liked = $doc.feedback.liked[0]?.id === track?.id;
	$: disliked = $doc.feedback.disliked[0]?.id === track?.id;

	const time = (ms) => {
		const s = Math.floor(ms / 1000);
		return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
	};

	function rate(more) {
		dj.rate(track, more);
		dj.loadSuggestions(track, true);
	}
</script>

<div class="np" class:compact bind:clientHeight={height}>
	{#if !state}
		<div class="art skeleton" />
		<div class="meta">
			<div class="line skeleton" style="width: 70%" />
			<div class="line skeleton" style="width: 45%" />
		</div>
	{:else if !state.active}
		<p class="empty">Nothing playing. Open Spotify on any device to start playback.</p>
	{:else if !track}
		<p class="empty">Spotify is playing something other than a song.</p>
	{:else}
		<img class="art" src={track.image} alt="" width="320" height="320" />
		<div class="meta">
			<p class="title" title={track.title}>{track.title}</p>
			<p class="artists">{track.artists.join(', ')}</p>

			<div class="progress" role="progressbar" aria-label="Song progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)}>
				<div class="fill" style:transform="scaleX({pct / 100})" />
			</div>
			<div class="times"><span>{time(progress)}</span><span>{time(track.duration_ms)}</span></div>

			<div class="controls">
				<button class="icon-btn" class:on={disliked} on:click={() => rate(false)} aria-label="Less like this" aria-pressed={disliked} title="Less like this">
					<Icon name="down" size={20} />
				</button>
				<button class="icon-btn" on:click={() => dj.send('previous')} disabled={!allows('skipping_prev')} aria-label="Previous" title="Previous">
					<Icon name="prev" size={20} />
				</button>
				{#if state.is_playing}
					<button class="play" on:click={() => dj.send('pause')} disabled={!allows('pausing')} aria-label="Pause"><Icon name="pause" size={22} /></button>
				{:else}
					<button class="play" on:click={() => dj.send('play')} disabled={!allows('resuming')} aria-label="Play"><Icon name="play" size={22} /></button>
				{/if}
				<button class="icon-btn" on:click={() => dj.send('next')} disabled={!allows('skipping_next')} aria-label="Next" title="Next">
					<Icon name="next" size={20} />
				</button>
				<button class="icon-btn" class:on={liked} on:click={() => rate(true)} aria-label="More like this" aria-pressed={liked} title="More like this">
					<Icon name="up" size={20} />
				</button>
			</div>
			{#if state.device?.name}
				<p class="device"><Icon name="speaker" size={14} /> {state.device.name}</p>
			{/if}
		</div>
	{/if}
	{#if $player.message}
		<p class="message" role="status">{$player.message}</p>
	{/if}
</div>

<style>
	.np {
		height: 100%;
		box-sizing: border-box;
		padding: 16px;
		display: flex;
		flex-direction: column;
		gap: 14px;
	}

	/* The art takes whatever height the widget has left and stays square. */
	.art {
		flex: 1 1 0;
		min-height: 64px;
		max-height: 320px;
		width: auto;
		max-width: 100%;
		aspect-ratio: 1;
		align-self: center;
		border-radius: var(--radius-sm);
		object-fit: cover;
	}

	.meta {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	p {
		margin: 0;
	}

	.title {
		font-size: 24px;
		font-weight: 600;
		line-height: 1.2;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.artists {
		font-size: 14px;
		color: var(--text-muted);
		margin-top: 2px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.progress {
		margin-top: 14px;
		height: 4px;
		border-radius: 2px;
		background: rgba(255, 255, 255, 0.14);
		overflow: hidden;
	}

	.fill {
		height: 100%;
		background: var(--accent);
		transform-origin: left;
		transition: transform 500ms linear;
	}

	.times {
		display: flex;
		justify-content: space-between;
		font-size: 12px;
		color: var(--text-muted);
		margin-top: 6px;
		font-variant-numeric: tabular-nums;
	}

	.controls {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 10px;
		margin-top: 8px;
	}

	.play {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		border: none;
		background: var(--accent);
		color: #0b0b0b;
		display: grid;
		place-items: center;
		cursor: pointer;
	}

	.play:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.icon-btn.on {
		color: var(--accent);
	}

	.device {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		margin-top: 10px;
		font-size: 12px;
		color: var(--text-muted);
	}

	.empty {
		margin: auto;
		max-width: 28ch;
		text-align: center;
		color: var(--text-muted);
		font-size: 14px;
		line-height: 1.5;
	}

	.message {
		font-size: 13px;
		color: #ff8a8a;
		text-align: center;
	}

	/* The Board preset's banner: art beside the text, one row of controls. */
	.compact {
		flex-direction: row;
		align-items: center;
		padding: 10px 16px;
	}

	.compact .art {
		flex: none;
		height: 88px;
		min-height: 0;
		align-self: center;
	}

	.compact .meta {
		flex: 1;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		grid-template-areas: 'title controls' 'artists controls' 'progress progress';
		column-gap: 16px;
	}

	.compact .title {
		grid-area: title;
		font-size: 20px;
	}

	.compact .artists {
		grid-area: artists;
	}

	.compact .progress {
		grid-area: progress;
		margin-top: 10px;
	}

	.compact .controls {
		grid-area: controls;
		margin: 0;
	}

	.compact .times,
	.compact .device {
		display: none;
	}

	.skeleton {
		background: var(--surface-2);
		border-radius: var(--radius-sm);
	}

	.line {
		height: 14px;
		margin-top: 8px;
	}

	@media (prefers-reduced-motion: reduce) {
		.fill {
			transition: none;
		}
	}
</style>
