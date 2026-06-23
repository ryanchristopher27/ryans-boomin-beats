<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import SongCard from './SongCard.svelte';
	import PlaylistNameModal from './PlaylistNameModal.svelte';
	import { access_token } from '../../stores.js';

	export let playlist = [];
	export let requested = 0;
	export let onSongExplore = null;
	export let onClear = null;

	let checkedIds = new Set();
	let showModal = false;
	let modalMode = 'all'; // 'all' | 'selected'
	let savedPlaylistUrl = '';
	let actionError = '';
	let queueSuccess = false;

	$: dedupedPlaylist = playlist.filter((s, i, arr) => arr.findIndex(x => x.spotify.id === s.spotify.id) === i);
	$: hasChecked = checkedIds.size > 0;
	$: allIds = dedupedPlaylist.map(s => s.spotify.id);
	$: selectedIds = allIds.filter(id => checkedIds.has(id));

	function onToggle(id, checked) {
		const next = new Set(checkedIds);
		checked ? next.add(id) : next.delete(id);
		checkedIds = next;
	}

	function openModal(mode) {
		modalMode = mode;
		showModal = true;
	}

	async function savePlaylist(name) {
		showModal = false;
		actionError = '';
		const ids = modalMode === 'all' ? allIds : selectedIds;
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/create-playlist/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name, track_ids: ids, access_token: $access_token }),
			});
			const data = await res.json();
			if (res.status === 401) {
				actionError = 'Log in to Spotify on the Profile page to save playlists.';
			} else if (data.playlist_url) {
				savedPlaylistUrl = data.playlist_url;
			} else {
				actionError = data.detail || 'Failed to create playlist.';
			}
		} catch (e) {
			actionError = 'Could not reach the server.';
		}
	}

	async function queueAll() {
		actionError = '';
		queueSuccess = false;
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/queue/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ track_ids: allIds, access_token: $access_token }),
			});
			const data = await res.json();
			if (res.status === 401) {
				actionError = 'Log in to Spotify on the Profile page to queue songs.';
			} else if (data.error === 'no_active_device') {
				actionError = 'Open Spotify on a device first, then try again.';
			} else {
				queueSuccess = true;
			}
		} catch (e) {
			actionError = 'Could not reach the server.';
		}
	}
</script>

{#if showModal}
	<PlaylistNameModal onSave={savePlaylist} onCancel={() => showModal = false} />
{/if}

{#if playlist.length > 0}
	<div class="result-container">
		{#if requested > 0 && playlist.length < requested}
			<div class="short-notice">
				Could only confirm {playlist.length} of {requested} songs on Spotify.
			</div>
		{/if}

		<div class="song-list">
			{#each dedupedPlaylist as song (song.spotify.id)}
				<SongCard
					{song}
					checked={checkedIds.has(song.spotify.id)}
					onToggle={onToggle}
					onExplore={onSongExplore}
				/>
				<hr class="divider" />
			{/each}
		</div>

		<div class="action-bar">
			<button class="action-btn" on:click={() => openModal('all')}>
				Add All as Playlist
			</button>
			<button class="action-btn" on:click={queueAll}>
				Queue All
			</button>
			<button class="action-btn" on:click={() => openModal('selected')} disabled={!hasChecked}>
				Add Selected as Playlist
			</button>
			{#if onClear}
				<button class="action-btn clear-btn" on:click={onClear}>
					Clear
				</button>
			{/if}
		</div>

		{#if actionError}
			<div class="action-error">{actionError}</div>
		{/if}

		{#if queueSuccess}
			<div class="action-success">Queued! Open Spotify to hear your playlist.</div>
		{/if}

		{#if savedPlaylistUrl}
			<div class="action-success">
				Playlist saved! <a href={savedPlaylistUrl} target="_blank" rel="noreferrer">Open in Spotify →</a>
			</div>
		{/if}
	</div>
{/if}

<style>
	.result-container {
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-lg);
		padding: 18px;
		animation: fadeIn 0.3s ease;
	}

	.short-notice {
		font-size: 0.8rem;
		color: rgba(255, 200, 100, 0.8);
		margin-bottom: 12px;
		text-align: center;
	}

	.song-list {
		margin-bottom: 16px;
	}

	.divider {
		border: none;
		border-top: 1px solid var(--border-subtle);
		margin: 0;
	}

	.action-bar {
		display: flex;
		gap: 10px;
		flex-wrap: wrap;
		justify-content: center;
		padding-top: 12px;
	}

	.action-btn {
		height: 38px;
		padding: 0 18px;
		background-color: var(--surface-2);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
		transition: border-color var(--transition), background-color var(--transition);
	}

	.action-btn:hover:not(:disabled) {
		border-color: var(--accent);
	}

	.action-btn:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.clear-btn {
		border-color: rgba(255, 107, 107, 0.4);
		color: rgba(255, 107, 107, 0.85);
		background-color: transparent;
	}

	.clear-btn:hover {
		background-color: rgba(255, 107, 107, 0.12);
		border-color: #ff6b6b;
		color: #ff6b6b;
	}

	.action-error {
		color: #ff6b6b;
		font-size: 0.8rem;
		text-align: center;
		margin-top: 10px;
	}

	.action-success {
		color: #6bffb8;
		font-size: 0.8rem;
		text-align: center;
		margin-top: 10px;
	}

	.action-success a {
		color: var(--accent);
	}
</style>
