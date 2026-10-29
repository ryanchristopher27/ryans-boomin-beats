<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import { playlistsPanelOpen, userPlaylists, access_token, pendingAdd } from '../../stores.js';
	import { spotifyHeaders } from '../spotifyHeaders.js';
	import { addTracksToPlaylist, createPlaylist } from '$lib/playlistActions.js';
	import PlaylistNameModal from './PlaylistNameModal.svelte';
	import Icon from './Icon.svelte';
	import { say } from '$lib/toast.js';

	let loading = false;
	let error = '';
	let loaded = false;
	let dragOverId = null;
	let showNameModal = false;

	// Sort: 'recent' = Spotify library order (Spotify exposes no created/modified
	// date for playlists, so this is the closest to recency). One button cycles.
	const SORTS = ['recent', 'name', 'count'];
	const sortLabels = { recent: 'Recent', name: 'A to Z', count: 'Most songs' };
	let sortKey = 'recent';
	let search = '';
	// Any song row on the page is being dragged: outline every tile.
	let dragging = false;

	$: if ($playlistsPanelOpen && $access_token && !loaded && !loading) {
		fetchPlaylists();
	}

	$: sortedPlaylists = sortPlaylists($userPlaylists, sortKey);
	$: visiblePlaylists = search.trim()
		? sortedPlaylists.filter((p) => p.name.toLowerCase().includes(search.trim().toLowerCase()))
		: sortedPlaylists;

	function sortPlaylists(list, key) {
		const arr = [...list];
		if (key === 'name') arr.sort((a, b) => a.name.localeCompare(b.name));
		else if (key === 'count') arr.sort((a, b) => b.track_count - a.track_count);
		return arr;
	}

	async function fetchPlaylists() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/playlists/`, { headers: spotifyHeaders() });
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
			say(trackIds.length > 1 ? `Added ${trackIds.length} to ${pl.name}` : `Added to ${pl.name}`);
			finishPending();
		} else {
			say(r.error === 'auth' ? 'Log in on Profile first' : 'Add failed');
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

	async function onCreate(name) {
		showNameModal = false;
		const trackIds = $pendingAdd ? $pendingAdd.trackIds : [];
		const r = await createPlaylist(name, trackIds);
		if (r.ok) {
			say(trackIds.length ? `Added to ${name}` : `Created ${name}`);
			refresh();
			finishPending();
		} else {
			say(r.error === 'auth' ? 'Log in on Profile first' : 'Create failed');
		}
	}

	function onKeydown(e) {
		if (e.key === 'Escape' && $pendingAdd) cancelPending();
	}
</script>

<svelte:window
	on:keydown={onKeydown}
	on:dragstart={() => (dragging = true)}
	on:dragend={() => ((dragging = false), (dragOverId = null))}
	on:drop={() => (dragging = false)}
/>

{#if $playlistsPanelOpen}
	<aside class="dock" class:picking={$pendingAdd} aria-label="Playlists">
		<div class="head">
			<h2>Playlists</h2>
			<div class="head-actions">
				<button class="icon-btn" aria-label="Refresh playlists" title="Refresh" on:click={refresh} disabled={!$access_token || loading}><Icon name="refresh" size={15} /></button>
				<button class="icon-btn" aria-label="Close playlists" on:click={() => ($playlistsPanelOpen = false)}><Icon name="x" size={15} /></button>
			</div>
		</div>

		{#if $pendingAdd}
			<div class="pending">
				<span>Adding <strong>{$pendingAdd.label}</strong>. Pick a playlist.</span>
				<button class="icon-btn" aria-label="Cancel adding" on:click={cancelPending}><Icon name="x" size={14} /></button>
			</div>
		{/if}

		{#if !$access_token}
			<p class="state">Log in on the Profile page to see your playlists.</p>
		{:else if loading}
			<div class="grid" aria-busy="true">
				{#each Array(6) as _}
					<div class="tile"><div class="cover skeleton" /><div class="skeleton line" /></div>
				{/each}
			</div>
		{:else if error === 'server'}
			<p class="state">Couldn't load playlists. <button class="link" on:click={refresh}>Retry</button></p>
		{:else}
			<div class="tools">
				<input type="search" placeholder="Search playlists" aria-label="Search playlists" bind:value={search} />
				<button class="sort" on:click={() => (sortKey = SORTS[(SORTS.indexOf(sortKey) + 1) % SORTS.length])} aria-label="Sort: {sortLabels[sortKey]}">{sortLabels[sortKey]}</button>
			</div>
			<p class="hint">{dragging ? 'Drop on a playlist to add the song.' : 'Drag any song onto a playlist to add it.'}</p>

			<div class="grid">
				<button class="tile" on:click={() => (showNameModal = true)}>
					<div class="cover new"><Icon name="plus" size={22} /></div>
					<div class="name">New playlist</div>
				</button>

				{#each visiblePlaylists as pl (pl.id)}
					<div
						class="tile"
						class:dragging
						class:over={dragOverId === pl.id}
						role="button"
						tabindex="0"
						on:click={() => onTileClick(pl)}
						on:keydown={(e) => e.key === 'Enter' && onTileClick(pl)}
						on:dragover|preventDefault={() => (dragOverId = pl.id)}
						on:dragleave={() => (dragOverId = null)}
						on:drop|preventDefault={(e) => handleDrop(e, pl)}
					>
						{#if pl.image}
							<img class="cover" src={pl.image} alt="" loading="lazy" />
						{:else}
							<div class="cover blank"><Icon name="music" size={22} /></div>
						{/if}
						<div class="meta">
							<div class="name" title={pl.name}>{pl.name}</div>
							<div class="count">{pl.track_count} songs</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</aside>
{/if}

{#if showNameModal}
	<PlaylistNameModal onSave={onCreate} onCancel={() => (showNameModal = false)} />
{/if}

<style>
	.dock {
		position: fixed;
		top: var(--header-height);
		right: 0;
		bottom: calc(var(--mini-h, 0px) + var(--tab-h, 0px));
		z-index: 30;
		width: var(--panel-width);
		display: flex;
		flex-direction: column;
		border-left: 1px solid var(--border-subtle);
		background: var(--surface-raised);
		animation: bbin 0.2s var(--ease);
	}

	.dock.picking {
		box-shadow: inset 0 0 0 2px var(--accent);
	}

	.head {
		flex: none;
		height: 52px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 10px 0 18px;
		border-bottom: 1px solid var(--border-subtle);
	}

	h2 {
		margin: 0;
		font-size: calc(15px * var(--text-scale, 1));
		font-weight: 600;
	}

	.head-actions {
		display: flex;
		gap: 2px;
	}

	.head .icon-btn {
		width: 30px;
		height: 30px;
	}

	.pending {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 12px 14px 0;
		padding: 8px 6px 8px 12px;
		border-radius: 10px;
		background: var(--accent-tint);
		border: 1px solid var(--accent-tint-border);
		color: var(--accent-tint-text);
		font-size: calc(13px * var(--text-scale, 1));
	}

	.pending span {
		flex: 1;
		min-width: 0;
	}

	.pending .icon-btn {
		width: 28px;
		height: 28px;
		color: inherit;
	}

	.state {
		margin: 0;
		padding: 18px;
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.link {
		padding: 0;
		border: none;
		background: none;
		color: var(--accent);
		font: inherit;
		cursor: pointer;
	}

	.tools {
		display: flex;
		gap: 8px;
		padding: 12px 14px;
	}

	.tools input,
	.sort {
		height: 34px;
		border-radius: 9px;
		border: 1px solid rgba(255, 255, 255, 0.08);
		background: var(--surface-1);
		font-size: calc(13px * var(--text-scale, 1));
	}

	.tools input {
		flex: 1;
		min-width: 0;
		padding: 0 12px;
		color: var(--text-primary);
	}

	.tools input:focus {
		outline: none;
		border-color: var(--accent-tint-border);
	}

	.sort {
		padding: 0 10px;
		color: rgba(243, 243, 245, 0.7);
		font-weight: 500;
		font-size: calc(12px * var(--text-scale, 1));
		cursor: pointer;
	}

	.hint {
		margin: 0;
		padding: 0 18px 8px;
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.grid {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overflow-x: hidden;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 14px 12px;
		align-content: start;
		padding: 4px 14px 14px;
	}

	.tile {
		display: flex;
		flex-direction: column;
		gap: 8px;
		min-width: 0;
		padding: 0;
		border: none;
		background: none;
		color: var(--text-primary);
		text-align: left;
		font: inherit;
		cursor: pointer;
	}

	.cover {
		display: grid;
		place-items: center;
		width: 100%;
		aspect-ratio: 1;
		border-radius: 10px;
		object-fit: cover;
		background: var(--surface-1);
		color: var(--text-subtle);
		outline: 2px solid transparent;
		outline-offset: 2px;
		transition: transform 0.15s var(--ease), outline-color 0.15s var(--ease);
	}

	.cover.new {
		background: none;
		border: 1px dashed rgba(255, 255, 255, 0.16);
		color: rgba(243, 243, 245, 0.5);
	}

	.tile:hover .cover {
		transform: scale(1.02);
	}

	.tile.dragging .cover {
		outline: 1px dashed rgba(var(--accent-rgb), 0.5);
	}

	.tile.over .cover {
		outline: 2px solid var(--accent);
		transform: scale(1.03);
	}

	.meta {
		min-width: 0;
	}

	.name {
		font-size: calc(13px * var(--text-scale, 1));
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.count {
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.line {
		height: 12px;
		width: 70%;
	}

	:global([data-bp='phone']) .dock {
		width: 100%;
	}
</style>
