<script>
	import { playlistsPanelOpen, userPlaylists, pendingAdd } from '../../stores.js';
	import { addTracksToPlaylist } from '$lib/playlistActions.js';

	export let song;
	export let checked = false;
	export let onToggle = () => {};
	export let onExplore = null;
	export let saved = false;
	export let onSaveToggle = null;

	let showReason = false;
	let showAddMenu = false;
	let addStatus = '';

	function millisToTime(ms) {
		const minutes = Math.floor(ms / 60000);
		const seconds = ((ms % 60000) / 1000).toFixed(0);
		return `${minutes}:${Number(seconds) < 10 ? '0' : ''}${seconds}`;
	}

	function onDragStart(e) {
		e.dataTransfer.setData('application/x-track-id', song.spotify.id);
		e.dataTransfer.setData('text/plain', song.spotify.id);
		e.dataTransfer.effectAllowed = 'copy';
	}

	function toggleSelect() {
		onToggle(song.spotify.id, !checked);
	}

	function onAddClick() {
		if ($playlistsPanelOpen) {
			showAddMenu = !showAddMenu;
		} else {
			// Open the panel transiently in "pick a playlist for this song" mode.
			$pendingAdd = { trackIds: [song.spotify.id], label: song.spotify.title, transient: true };
			$playlistsPanelOpen = true;
		}
	}

	async function addToPlaylist(pl) {
		showAddMenu = false;
		const r = await addTracksToPlaylist(pl.id, [song.spotify.id]);
		addStatus = r.ok ? `Added to ${pl.name}` : 'Failed';
		setTimeout(() => (addStatus = ''), 2000);
	}
</script>

<svelte:window on:click={() => (showAddMenu = false)} />

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div class="card" class:checked draggable="true" on:dragstart={onDragStart} on:click={toggleSelect}>
	<img
		class="album-art"
		src={song.spotify.image}
		alt={song.spotify.album}
		draggable="false"
	/>

	<div class="info">
		<div class="title">
			<a href={song.spotify.track_url} target="_blank" rel="noreferrer" draggable="false" on:click|stopPropagation>{song.spotify.title}</a>
		</div>
		<div class="artist">{song.spotify.artists.join(', ')}</div>
		<div class="album">{song.spotify.album}</div>
	</div>

	<div class="meta">
		<div class="duration">{millisToTime(song.spotify.duration_ms)}</div>
		{#if onSaveToggle}
			<button
				class="heart-btn"
				class:saved
				on:click|stopPropagation={() => onSaveToggle(song.spotify.id, !saved)}
				title={saved ? 'Remove from Liked Songs' : 'Save to Liked Songs'}
			>
				{saved ? '♥' : '♡'}
			</button>
		{/if}
		{#if song.reason}
			<button class="reason-btn" on:click|stopPropagation={() => showReason = !showReason} title="Why this song?">
				{showReason ? '▲' : '?'}
			</button>
		{/if}
		{#if onExplore}
			<button class="explore-btn" on:click|stopPropagation={() => onExplore({ title: song.spotify.title, artists: song.spotify.artists, id: song.spotify.id, image: song.spotify.image })} title="Explore this song">
				Explore →
			</button>
		{/if}
		<button class="add-btn" on:click|stopPropagation={onAddClick} title="Add to playlist">＋</button>
	</div>

	{#if showAddMenu}
		<div class="add-menu" on:click|stopPropagation>
			{#if $userPlaylists.length === 0}
				<div class="add-empty">No playlists loaded</div>
			{:else}
				{#each $userPlaylists as pl (pl.id)}
					<button class="add-item" on:click|stopPropagation={() => addToPlaylist(pl)} title={pl.name}>{pl.name}</button>
				{/each}
			{/if}
		</div>
	{/if}

	{#if addStatus}
		<div class="add-status">{addStatus}</div>
	{/if}

	{#if showReason && song.reason}
		<div class="reason">{song.reason}</div>
	{/if}
</div>

<style>
	.card {
		position: relative;
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 14px;
		border-radius: var(--radius);
		transition: background-color var(--transition);
		flex-wrap: wrap;
		cursor: pointer;
	}

	.card:active {
		cursor: grabbing;
	}

	.card:hover {
		background-color: var(--surface-2);
	}

	.card.checked {
		background-color: var(--surface-2);
	}

	.card.checked::before {
		content: '';
		position: absolute;
		left: 0;
		top: 6px;
		bottom: 6px;
		width: 4px;
		border-radius: 0 3px 3px 0;
		background: var(--brand-gradient);
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

	.heart-btn {
		background: none;
		border: none;
		color: var(--text-muted);
		font-size: 1rem;
		line-height: 1;
		cursor: pointer;
		padding: 0 2px;
		flex-shrink: 0;
		transition: color var(--transition), transform var(--transition);
	}

	.heart-btn:hover {
		color: var(--accent);
		transform: scale(1.15);
	}

	.heart-btn.saved {
		color: var(--accent);
	}

	.add-btn {
		background: none;
		border: 1px solid var(--border-subtle);
		border-radius: 50%;
		color: var(--text-muted);
		width: 22px;
		height: 22px;
		font-size: 0.9rem;
		line-height: 1;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0;
		flex-shrink: 0;
		transition: border-color var(--transition), color var(--transition);
	}

	.add-btn:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.add-menu {
		position: absolute;
		top: calc(100% - 6px);
		right: 14px;
		z-index: 30;
		width: 200px;
		max-height: 260px;
		overflow-y: auto;
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
		padding: 4px;
	}

	.add-item {
		display: block;
		width: 100%;
		text-align: left;
		background: none;
		border: none;
		color: var(--text-primary);
		font-size: 0.8rem;
		padding: 7px 10px;
		border-radius: var(--radius-sm);
		cursor: pointer;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.add-item:hover {
		background-color: var(--surface-2);
	}

	.add-empty {
		padding: 10px;
		font-size: 0.78rem;
		color: var(--text-subtle);
		text-align: center;
	}

	.add-status {
		width: 100%;
		font-size: 0.72rem;
		color: #6bffb8;
		padding: 2px 14px 0 76px;
	}

	.reason {
		width: 100%;
		font-size: 0.78rem;
		color: var(--text-muted);
		font-style: italic;
		padding: 4px 14px 0 76px;
	}
</style>
