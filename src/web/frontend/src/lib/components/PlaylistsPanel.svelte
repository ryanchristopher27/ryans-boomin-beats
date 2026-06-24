<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import { playlistsPanelOpen, userPlaylists, access_token, pendingAdd } from '../../stores.js';
	import { addTracksToPlaylist } from '$lib/playlistActions.js';
	import PlaylistNameModal from './PlaylistNameModal.svelte';

	let loading = false;
	let error = '';
	let loaded = false;
	let dragOverId = null;
	let status = '';
	let statusTimer;
	let showNameModal = false;

	// Sort: 'recent' = Spotify library order (Spotify exposes no created/modified
	// date for playlists, so this is the closest to recency).
	let sortKey = 'recent';
	let sortDir = 'asc';
	let search = '';
	const sortLabels = { recent: 'Recently added', name: 'Name', count: 'Song count' };

	$: if ($playlistsPanelOpen && $access_token && !loaded && !loading) {
		fetchPlaylists();
	}

	$: sortedPlaylists = sortPlaylists($userPlaylists, sortKey, sortDir);
	$: visiblePlaylists = search.trim()
		? sortedPlaylists.filter((p) => p.name.toLowerCase().includes(search.trim().toLowerCase()))
		: sortedPlaylists;

	function sortPlaylists(list, key, dir) {
		const arr = [...list];
		if (key === 'name') arr.sort((a, b) => a.name.localeCompare(b.name));
		else if (key === 'count') arr.sort((a, b) => a.track_count - b.track_count);
		if (dir === 'desc') arr.reverse();
		return arr;
	}

	async function fetchPlaylists() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/playlists/?access_token=${$access_token}`);
			if (res.status === 401) {
				error = 'auth';
				return;
			}
			const data = await res.json();
			$userPlaylists = data.playlists ?? [];
			loaded = true;
		} catch {
			error = 'server';
		} finally {
			loading = false;
		}
	}

	function refresh() {
		loaded = false;
		fetchPlaylists();
	}

	function flashStatus(msg) {
		status = msg;
		clearTimeout(statusTimer);
		statusTimer = setTimeout(() => (status = ''), 2500);
	}

	function bumpCount(id, n = 1) {
		$userPlaylists = $userPlaylists.map((p) =>
			p.id === id ? { ...p, track_count: p.track_count + n } : p
		);
	}

	function finishPending() {
		if (!$pendingAdd) return;
		const transient = $pendingAdd.transient;
		$pendingAdd = null;
		if (transient) setTimeout(() => ($playlistsPanelOpen = false), 900);
	}

	function cancelPending() {
		if (!$pendingAdd) return;
		const transient = $pendingAdd.transient;
		$pendingAdd = null;
		if (transient) $playlistsPanelOpen = false;
	}

	async function addTracks(pl, trackIds) {
		const r = await addTracksToPlaylist(pl.id, trackIds);
		if (r.ok) {
			bumpCount(pl.id, trackIds.length);
			flashStatus(trackIds.length > 1 ? `Added ${trackIds.length} to ${pl.name}` : `Added to ${pl.name}`);
			finishPending();
		} else {
			flashStatus(r.error === 'auth' ? 'Log in on Profile first' : 'Add failed');
		}
	}

	function handleDrop(e, pl) {
		dragOverId = null;
		const id =
			e.dataTransfer.getData('application/x-track-id') || e.dataTransfer.getData('text/plain');
		if (id) addTracks(pl, [id]);
	}

	function onTileClick(pl) {
		if ($pendingAdd) {
			addTracks(pl, $pendingAdd.trackIds);
		} else {
			window.open(`https://open.spotify.com/playlist/${pl.id}`, '_blank', 'noreferrer');
		}
	}

	async function createPlaylist(name) {
		showNameModal = false;
		const trackIds = $pendingAdd ? $pendingAdd.trackIds : [];
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/create-playlist/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name, track_ids: trackIds, access_token: $access_token }),
			});
			const data = await res.json();
			if (data.playlist_id) {
				flashStatus(trackIds.length ? `Added to ${name}` : `Created ${name}`);
				refresh();
				finishPending();
			} else {
				flashStatus('Create failed');
			}
		} catch {
			flashStatus('Create failed');
		}
	}

	function onKeydown(e) {
		if (e.key === 'Escape' && $pendingAdd) cancelPending();
	}
</script>

<svelte:window on:keydown={onKeydown} />

{#if $playlistsPanelOpen}
	<aside class="panel" class:picking={$pendingAdd}>
		<div class="panel-head">
			<span class="panel-title">Playlists</span>
			<div class="head-actions">
				<button class="icon-btn" title="Refresh" on:click={refresh} disabled={!$access_token || loading}>⟳</button>
				<button class="icon-btn" title="Close" on:click={() => ($playlistsPanelOpen = false)}>✕</button>
			</div>
		</div>

		{#if $pendingAdd}
			<div class="pending-banner">
				<span class="pending-text">Adding <strong>{$pendingAdd.label}</strong> — pick a playlist</span>
				<button class="icon-btn" title="Cancel" on:click={cancelPending}>✕</button>
			</div>
		{/if}

		{#if status}
			<div class="status">{status}</div>
		{/if}

		{#if !$access_token}
			<div class="state">Log in on the Profile page to see your playlists.</div>
		{:else if loading}
			<div class="state">Loading…</div>
		{:else if error === 'server'}
			<div class="state">Couldn't load playlists. <button class="link" on:click={refresh}>Retry</button></div>
		{:else}
			{#if $userPlaylists.length > 0}
				<input
					class="search-input"
					type="text"
					placeholder="Search playlists…"
					bind:value={search}
				/>
				<div class="sort-bar">
					<select class="sort-select" bind:value={sortKey} aria-label="Sort by">
						<option value="recent">{sortLabels.recent}</option>
						<option value="name">{sortLabels.name}</option>
						<option value="count">{sortLabels.count}</option>
					</select>
					<button
						class="sort-dir"
						title={sortDir === 'asc' ? 'Ascending' : 'Descending'}
						on:click={() => (sortDir = sortDir === 'asc' ? 'desc' : 'asc')}
					>
						{sortDir === 'asc' ? '↑' : '↓'}
					</button>
				</div>
			{/if}

			<div class="grid">
				<button class="tile new-tile" on:click={() => (showNameModal = true)}>
					<div class="tile-img new-img">＋</div>
					<div class="tile-name">New playlist</div>
					<div class="tile-count">&nbsp;</div>
				</button>

				{#each visiblePlaylists as pl (pl.id)}
					<div
						class="tile"
						class:drag-over={dragOverId === pl.id}
						role="button"
						tabindex="0"
						on:click={() => onTileClick(pl)}
						on:keydown={(e) => e.key === 'Enter' && onTileClick(pl)}
						on:dragover|preventDefault={() => (dragOverId = pl.id)}
						on:dragleave={() => (dragOverId = null)}
						on:drop|preventDefault={(e) => handleDrop(e, pl)}
					>
						{#if pl.image}
							<img class="tile-img" src={pl.image} alt="" />
						{:else}
							<div class="tile-img placeholder"></div>
						{/if}
						<div class="tile-name" title={pl.name}>{pl.name}</div>
						<div class="tile-count">{pl.track_count} songs</div>
					</div>
				{/each}
			</div>
		{/if}
	</aside>
{/if}

{#if showNameModal}
	<PlaylistNameModal onSave={createPlaylist} onCancel={() => (showNameModal = false)} />
{/if}

<style>
	.panel {
		position: fixed;
		/* Match the page content's top offset: main padding + body-div margin-top. */
		top: calc(88px + var(--primary-spacing));
		right: var(--primary-spacing);
		bottom: 0;
		width: var(--panel-width);
		box-sizing: border-box;
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-bottom: none;
		border-top-left-radius: var(--radius-lg);
		border-top-right-radius: var(--radius-lg);
		z-index: 45;
		display: flex;
		flex-direction: column;
		animation: fadeIn 0.2s ease;
	}

	.panel.picking {
		box-shadow: inset 0 0 0 2px var(--accent);
	}

	.panel-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 16px 12px;
		flex-shrink: 0;
	}

	.panel-title {
		font-size: 0.85rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-subtle);
	}

	.head-actions {
		display: flex;
		gap: 4px;
	}

	.icon-btn {
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		font-size: 0.95rem;
		width: 26px;
		height: 26px;
		border-radius: var(--radius-sm);
		transition: color var(--transition), background-color var(--transition);
		flex-shrink: 0;
	}

	.icon-btn:hover:not(:disabled) {
		color: var(--text-primary);
		background-color: var(--surface-2);
	}

	.icon-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.pending-banner {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 0 16px 10px;
		padding: 8px 10px;
		background-color: rgba(var(--accent-rgb), 0.12);
		border: 1px solid var(--accent);
		border-radius: var(--radius-sm);
		font-size: 0.75rem;
		color: var(--text-muted);
	}

	.pending-text {
		flex: 1;
		min-width: 0;
	}

	.pending-text strong {
		color: var(--text-primary);
	}

	.status {
		margin: 0 16px 10px;
		font-size: 0.75rem;
		color: #6bffb8;
	}

	.state {
		padding: 24px 16px;
		font-size: 0.8rem;
		color: var(--text-subtle);
		text-align: center;
	}

	.link {
		background: none;
		border: none;
		color: var(--accent);
		cursor: pointer;
		font-size: inherit;
		padding: 0;
	}

	.search-input {
		margin: 0 16px 10px;
		background-color: var(--surface-0);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		padding: 7px 10px;
		font-size: 0.8rem;
		font-family: inherit;
		flex-shrink: 0;
	}

	.search-input::placeholder {
		color: var(--text-subtle);
	}

	.search-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.sort-bar {
		display: flex;
		gap: 8px;
		padding: 0 16px 12px;
		flex-shrink: 0;
	}

	.sort-select {
		flex: 1;
		min-width: 0;
		background-color: var(--surface-0);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		padding: 6px 8px;
		font-size: 0.78rem;
		font-family: inherit;
		cursor: pointer;
	}

	.sort-select:focus {
		outline: none;
		border-color: var(--accent);
	}

	.sort-dir {
		width: 32px;
		flex-shrink: 0;
		background-color: var(--surface-0);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		font-size: 0.85rem;
		cursor: pointer;
		transition: border-color var(--transition);
	}

	.sort-dir:hover {
		border-color: var(--accent);
	}

	.grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
		padding: 0 16px 20px;
		overflow-y: auto;
	}

	.tile {
		display: flex;
		flex-direction: column;
		gap: 4px;
		min-width: 0;
		cursor: pointer;
		border-radius: var(--radius-sm);
		padding: 6px;
		border: 1px solid transparent;
		background: none;
		text-align: left;
		font-family: inherit;
		transition: background-color var(--transition), border-color var(--transition);
	}

	.tile:hover {
		background-color: var(--surface-2);
	}

	.tile.drag-over {
		border-color: var(--accent);
		background-color: rgba(var(--accent-rgb), 0.12);
	}

	.panel.picking .tile:not(.new-tile):hover {
		border-color: var(--accent);
	}

	.tile-img {
		width: 100%;
		aspect-ratio: 1 / 1;
		object-fit: cover;
		border-radius: var(--radius-sm);
		background-color: var(--surface-2);
	}

	.tile-img.placeholder {
		display: block;
	}

	.new-img {
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.6rem;
		color: var(--text-subtle);
		border: 1px dashed var(--border-subtle);
		background: none;
	}

	.tile-name {
		font-size: 0.78rem;
		font-weight: 600;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.tile-count {
		font-size: 0.7rem;
		color: var(--text-subtle);
	}
</style>
