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
			<button class="explore-btn" on:click={() => onExplore({ title: song.spotify.title, artists: song.spotify.artists, id: song.spotify.id, image: song.spotify.image })} title="Explore this song">
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
		border-radius: var(--radius);
		transition: background-color var(--transition);
		flex-wrap: wrap;
	}

	.card:hover {
		background-color: var(--surface-2);
	}

	.card.checked {
		background-color: var(--surface-2);
	}

	.checkbox {
		accent-color: var(--accent);
		width: 16px;
		height: 16px;
		flex-shrink: 0;
		cursor: pointer;
	}

	.album-art {
		width: 48px;
		height: 48px;
		border-radius: var(--radius-sm);
		flex-shrink: 0;
		object-fit: cover;
	}

	.info {
		flex: 1;
		min-width: 0;
	}

	.title {
		font-weight: 600;
		font-size: 0.9rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.title a {
		color: var(--text-primary);
		text-decoration: none;
		transition: color var(--transition);
	}

	.title a:hover {
		color: var(--accent);
	}

	.artist {
		font-size: 0.8rem;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.album {
		font-size: 0.75rem;
		color: var(--text-subtle);
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
		color: var(--text-subtle);
	}

	.reason-btn {
		background: none;
		border: 1px solid var(--border-subtle);
		border-radius: 50%;
		color: var(--text-muted);
		width: 20px;
		height: 20px;
		font-size: 0.65rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0;
		transition: border-color var(--transition), color var(--transition);
	}

	.reason-btn:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.explore-btn {
		background: none;
		border: 1px solid var(--accent);
		border-radius: var(--radius-sm);
		color: var(--accent);
		font-size: 0.7rem;
		font-weight: 700;
		padding: 3px 10px;
		cursor: pointer;
		white-space: nowrap;
		transition: background-color var(--transition), color var(--transition);
	}

	.explore-btn:hover {
		background-color: var(--accent);
		color: var(--surface-0);
	}

	.reason {
		width: 100%;
		font-size: 0.78rem;
		color: var(--text-muted);
		font-style: italic;
		padding: 4px 14px 0 76px;
	}
</style>
