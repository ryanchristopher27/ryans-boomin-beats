<script>
	export let song;
	export let checked = false;
	export let onToggle = () => {};
	export let onExplore = null;

	let showReason = false;

	function millisToTime(ms) {
		const minutes = Math.floor(ms / 60000);
		const seconds = ((ms % 60000) / 1000).toFixed(0);
		return `${minutes}:${Number(seconds) < 10 ? '0' : ''}${seconds}`;
	}
</script>

<div class="card" class:checked>
	<input
		class="checkbox"
		type="checkbox"
		bind:checked
		on:change={() => onToggle(song.spotify.id, checked)}
	/>

	<img
		class="album-art"
		src={song.spotify.image}
		alt={song.spotify.album}
	/>

	<div class="info">
		<div class="title">
			<a href={song.spotify.track_url} target="_blank" rel="noreferrer">{song.spotify.title}</a>
		</div>
		<div class="artist">{song.spotify.artists.join(', ')}</div>
		<div class="album">{song.spotify.album}</div>
	</div>

	<div class="meta">
		<div class="duration">{millisToTime(song.spotify.duration_ms)}</div>
		{#if song.reason}
			<button class="reason-btn" on:click={() => showReason = !showReason} title="Why this song?">
				{showReason ? '▲' : '?'}
			</button>
		{/if}
		{#if onExplore}
			<button class="explore-btn" on:click={() => onExplore({ title: song.spotify.title, artists: song.spotify.artists, id: song.spotify.id })} title="Explore this song">
				Explore →
			</button>
		{/if}
	</div>

	{#if showReason && song.reason}
		<div class="reason">{song.reason}</div>
	{/if}
</div>

<style>
	.card {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 14px;
		border-radius: 10px;
		transition: background-color 0.15s;
		flex-wrap: wrap;
	}

	.card:hover {
		background-color: rgba(94, 201, 255, 0.06);
	}

	.card.checked {
		background-color: rgba(94, 201, 255, 0.1);
	}

	.checkbox {
		accent-color: var(--color-light-blue);
		width: 16px;
		height: 16px;
		flex-shrink: 0;
		cursor: pointer;
	}

	.album-art {
		width: 48px;
		height: 48px;
		border-radius: 6px;
		flex-shrink: 0;
		object-fit: cover;
	}

	.info {
		flex: 1;
		min-width: 0;
	}

	.title {
		font-weight: 700;
		font-size: 0.9rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.title a {
		color: var(--color-light-blue);
		text-decoration: none;
	}

	.title a:hover {
		color: var(--color-purple);
	}

	.artist {
		font-size: 0.8rem;
		color: rgba(94, 201, 255, 0.75);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.album {
		font-size: 0.75rem;
		color: rgba(255, 255, 255, 0.4);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.meta {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}

	.duration {
		font-size: 0.8rem;
		color: rgba(255, 255, 255, 0.5);
	}

	.reason-btn {
		background: none;
		border: 1px solid rgba(94, 201, 255, 0.4);
		border-radius: 50%;
		color: var(--color-light-blue);
		width: 20px;
		height: 20px;
		font-size: 0.65rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0;
	}

	.reason-btn:hover {
		border-color: var(--color-purple);
		color: var(--color-purple);
	}

	.explore-btn {
		background: none;
		border: 1px solid rgba(94, 201, 255, 0.4);
		border-radius: 8px;
		color: var(--color-light-blue);
		font-size: 0.7rem;
		font-weight: 700;
		padding: 2px 8px;
		cursor: pointer;
		white-space: nowrap;
	}

	.explore-btn:hover {
		border-color: var(--color-purple);
		color: var(--color-purple);
	}

	.reason {
		width: 100%;
		font-size: 0.78rem;
		color: rgba(94, 201, 255, 0.7);
		font-style: italic;
		padding: 4px 14px 0 76px;
	}
</style>
