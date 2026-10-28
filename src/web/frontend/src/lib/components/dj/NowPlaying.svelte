<script>
	import { onDestroy, onMount } from 'svelte';
	import Icon from '../Icon.svelte';
	import Visualizer from '../ui/Visualizer.svelte';

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
	$: playing = !!state?.is_playing;
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
		<div class="song">
			<div class="cover skeleton" />
			<div class="meta">
				<div class="line skeleton" style="width: 70%" />
				<div class="line skeleton" style="width: 45%" />
			</div>
		</div>
	{:else if !state.active}
		<p class="empty">Nothing playing. Open Spotify on any device and the DJ picks up from there.</p>
	{:else if !track}
		<p class="empty">Spotify is playing something other than a song.</p>
	{:else}
		<div class="song">
			<div class="cover" class:playing>
				{#key track.id}
					<img class="glow" src={track.image} alt="" aria-hidden="true" />
					<img class="art" src={track.image} alt="" width="100" height="100" />
				{/key}
			</div>
			<div class="meta">
				<p class="title" title={track.title}>{track.title}</p>
				<p class="artists">{track.artists.join(', ')}</p>
			</div>
		</div>

		{#if !compact}<Visualizer {playing} />{/if}

		<div class="progress-wrap">
			<div class="progress" role="progressbar" aria-label="Song progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)}>
				<div class="fill" style:transform="scaleX({pct / 100})" />
			</div>
			<div class="times mono"><span>{time(progress)}</span><span>{time(track.duration_ms)}</span></div>
		</div>

		<div class="controls">
			<button class="round soft" class:on={disliked} on:click={() => rate(false)} aria-label="Less like this" aria-pressed={disliked} title="Less like this">
				<Icon name="down" size={18} />
			</button>
			<button class="round" on:click={() => dj.send('previous')} disabled={!allows('skipping_prev')} aria-label="Previous" title="Previous">
				<Icon name="prev" size={17} filled />
			</button>
			{#if playing}
				<button class="play" on:click={() => dj.send('pause')} disabled={!allows('pausing')} aria-label="Pause"><Icon name="pause" size={18} filled /></button>
			{:else}
				<button class="play" on:click={() => dj.send('play')} disabled={!allows('resuming')} aria-label="Play"><Icon name="play" size={18} filled /></button>
			{/if}
			<button class="round" on:click={() => dj.send('next')} disabled={!allows('skipping_next')} aria-label="Next" title="Next">
				<Icon name="next" size={17} filled />
			</button>
			<button class="round soft" class:on={liked} on:click={() => rate(true)} aria-label="More like this" aria-pressed={liked} title="More like this">
				<Icon name="up" size={18} />
			</button>
		</div>
		{#if state.device?.name && !compact}
			<p class="device"><Icon name="speaker" size={13} /> {state.device.name}</p>
		{/if}
	{/if}
	{#if $player.message}
		<p class="message" role="status">{$player.message}</p>
	{/if}
</div>

<style>
	.np {
		height: 100%;
		padding: 16px;
		display: flex;
		flex-direction: column;
		gap: 14px;
	}

	.song {
		display: flex;
		gap: 14px;
		align-items: center;
		min-width: 0;
	}

	.cover {
		position: relative;
		flex: none;
		width: 100px;
		height: 100px;
	}

	.art,
	.glow {
		width: 100%;
		height: 100%;
		border-radius: 12px;
		object-fit: cover;
	}

	.art {
		position: relative;
		display: block;
		background: var(--surface-2);
		box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4);
		animation: bbpop 0.55s var(--ease);
	}

	/* A blurred copy of the cover glows behind it, brighter while playing. */
	.glow {
		position: absolute;
		inset: 0;
		filter: blur(22px) saturate(1.4);
		opacity: 0.2;
		transition: opacity 0.4s var(--ease);
	}

	.cover.playing .glow {
		opacity: 0.75;
		animation: bbglow 4.5s ease-in-out infinite;
	}

	.cover.playing .art {
		animation: bbpop 0.55s var(--ease), bbbreath 5s ease-in-out 0.55s infinite;
	}

	.cover.skeleton {
		border-radius: 12px;
	}

	.meta {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	p {
		margin: 0;
	}

	.title {
		font-size: 19px;
		font-weight: 600;
		line-height: 1.15;
		letter-spacing: -0.02em;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.artists {
		font-size: 13px;
		color: rgba(243, 243, 245, 0.65);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.line {
		height: 12px;
	}

	.progress-wrap {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.progress {
		height: 4px;
		border-radius: 4px;
		background: rgba(255, 255, 255, 0.12);
		overflow: hidden;
	}

	.fill {
		height: 100%;
		border-radius: 4px;
		background: linear-gradient(90deg, var(--accent), var(--accent-2));
		box-shadow: 0 0 12px rgba(var(--accent-rgb), 0.6);
		transform-origin: left;
		transition: transform 0.5s linear;
	}

	.times {
		display: flex;
		justify-content: space-between;
		font-size: 11px;
		color: rgba(243, 243, 245, 0.5);
	}

	.controls {
		display: flex;
		align-items: center;
		justify-content: space-between;
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
		width: 36px;
		height: 36px;
		background: transparent;
		color: var(--text-primary);
		transition: background-color var(--transition), color var(--transition);
	}

	.round.soft {
		color: rgba(243, 243, 245, 0.65);
	}

	.round:hover:not(:disabled) {
		background: rgba(255, 255, 255, 0.06);
	}

	.round.on {
		color: var(--accent);
	}

	.play {
		width: 48px;
		height: 48px;
		background: #f3f3f5;
		color: #0a0a0c;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
	}

	button:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.device {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: rgba(243, 243, 245, 0.5);
	}

	.empty,
	.message {
		font-size: 14px;
		line-height: 1.5;
		color: var(--text-muted);
	}

	.empty {
		margin: auto 0;
		text-align: center;
	}

	.message {
		font-size: 13px;
		color: var(--warning);
	}

	/* The Board preset's short banner: one row. */
	.compact {
		flex-direction: row;
		align-items: center;
		gap: 16px;
		padding: 10px 16px;
	}

	.compact .song {
		flex: 1;
		min-width: 0;
	}

	.compact .cover {
		width: 56px;
		height: 56px;
	}

	.compact .progress-wrap {
		flex: 1.4;
	}

	.compact .times {
		display: none;
	}

	.compact .controls {
		flex: none;
		justify-content: flex-start;
	}

	.compact .title {
		-webkit-line-clamp: 1;
		font-size: 16px;
	}
</style>
