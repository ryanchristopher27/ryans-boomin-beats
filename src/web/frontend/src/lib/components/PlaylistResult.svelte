<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import SongCard from './SongCard.svelte';
	import { access_token, pendingAdd, playlistsPanelOpen } from '../../stores.js';
	import { spotifyHeaders } from '../spotifyHeaders.js';
	import { getSavedStates, rememberSongs, setTrackSaved, toSpotifyIds } from '$lib/playlistActions.js';

	export let playlist = [];
	export let requested = 0;
	export let onSongExplore = null;
	export let onClear = null;
	export let coverImage = null;
	export let coverTitle = '';
	export let coverSubtitle = '';

	let checkedIds = new Set();
	let actionError = '';
	let queueSuccess = false;
	let savedMap = {};
	let savedKey = '';

	$: dedupedPlaylist = playlist.filter((s, i, arr) => arr.findIndex(x => x.spotify.id === s.spotify.id) === i);
	// Results are Deezer-checked (Q3); their ids resolve to Spotify only when used.
	$: rememberSongs(dedupedPlaylist.map((s) => s.spotify));
	$: hasChecked = checkedIds.size > 0;
	$: allIds = dedupedPlaylist.map(s => s.spotify.id);
	$: selectedIds = allIds.filter(id => checkedIds.has(id));
	$: maybeCheckSaved(allIds);

	function onToggle(id, checked) {
		const next = new Set(checkedIds);
		checked ? next.add(id) : next.delete(id);
		checkedIds = next;
	}

	async function maybeCheckSaved(ids) {
		const key = ids.join(',');
		if (key === savedKey || ids.length === 0) return;
		savedKey = key;
		savedMap = await getSavedStates(ids);
	}

	async function handleSaveToggle(id, newSaved) {
		savedMap = { ...savedMap, [id]: newSaved };
		const r = await setTrackSaved(id, newSaved);
		if (r.error) {
			savedMap = { ...savedMap, [id]: !newSaved };
			actionError =
				r.error === 'reconnect'
					? 'Reconnect Spotify on the Profile page to enable saving.'
					: 'Could not update Liked Songs.';
		}
	}

	// Route bulk adds through the Playlists panel ("pick a playlist" mode), where
	// the user can choose an existing playlist or the "New playlist" tile.
	function addBulk(ids) {
		if (!ids.length) return;
		const wasOpen = $playlistsPanelOpen;
		$pendingAdd = {
			trackIds: ids,
			label: `${ids.length} song${ids.length > 1 ? 's' : ''}`,
			transient: !wasOpen,
		};
		$playlistsPanelOpen = true;
	}

	async function queueAll() {
		actionError = '';
		queueSuccess = false;
		try {
			const { ids, missing, error } = await toSpotifyIds(allIds);
			if (error === 'auth') {
				actionError = 'Log in to Spotify on the Profile page to queue songs.';
				return;
			}
			if (error || !ids.length) {
				actionError = error ? "Couldn't look these songs up on Spotify right now." : "None of these songs are on Spotify.";
				return;
			}
			if (missing) actionError = `${missing} song${missing > 1 ? "s aren't" : " isn't"} on Spotify and was skipped.`;
			const res = await fetch(`${PUBLIC_API_URL}/spotify/queue/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', ...spotifyHeaders() },
				body: JSON.stringify({ track_ids: ids }),
			});
			const data = await res.json();
			if (res.status === 401) {
				actionError = 'Log in to Spotify on the Profile page to queue songs.';
			} else if (data.error === 'no_active_device') {
				// The backend reports how many landed before the device dropped,
				// so a partial queue doesn't read as a total failure.
				actionError = data.queued
					? `Queued ${data.queued} before Spotify lost the active device. Start playback, then try again.`
					: 'Open Spotify on a device first, then try again.';
			} else if (data.error === 'premium_required') {
				actionError = 'Queueing requires Spotify Premium.';
			} else if (data.error) {
				// e.g. 'restricted': Spotify refused for a non-Premium reason.
				actionError = data.queued
					? `Queued ${data.queued} before Spotify refused the rest. Try again in a moment.`
					: "Spotify didn't allow queueing right now. Try again in a moment.";
			} else {
				queueSuccess = true;
			}
		} catch (e) {
			actionError = 'Could not reach the server.';
		}
	}
</script>

{#if playlist.length > 0}
	<div class="result-container" class:has-cover={coverImage}>
		{#if coverImage}
			<div class="cover-backdrop" style="background-image: url({coverImage})"></div>
			<div class="cover-scrim"></div>
		{/if}

		<div class="result-content">
			{#if coverImage}
				<div class="cover-header">
					<img class="cover-thumb" src={coverImage} alt="" />
					<div class="cover-meta">
						{#if coverSubtitle}<div class="cover-eyebrow">{coverSubtitle}</div>{/if}
						{#if coverTitle}<div class="cover-title">{coverTitle}</div>{/if}
					</div>
				</div>
			{/if}

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
					saved={savedMap[song.spotify.id] || false}
					onSaveToggle={handleSaveToggle}
				/>
			{/each}
		</div>

		<div class="action-bar">
			<button class="action-btn" on:click={() => addBulk(allIds)}>
				Add All to Playlist
			</button>
			<button class="action-btn" on:click={queueAll}>
				Queue All
			</button>
			<button class="action-btn" on:click={() => addBulk(selectedIds)} disabled={!hasChecked}>
				Add Selected to Playlist
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

		</div>
	</div>
{/if}

<style>
	.result-container {
		position: relative;
		overflow: hidden;
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-lg);
		padding: 18px;
		animation: bbin 0.3s ease;
	}

	.cover-backdrop {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 320px;
		background-size: cover;
		background-position: center;
		filter: blur(44px) saturate(1.3);
		opacity: 0.5;
		transform: scale(1.2);
		-webkit-mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.9) 0%, transparent 100%);
		mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.9) 0%, transparent 100%);
		pointer-events: none;
	}

	.cover-scrim {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 320px;
		background: linear-gradient(180deg, rgba(18, 18, 18, 0.5) 0%, var(--surface-1) 100%);
		pointer-events: none;
	}

	.result-content {
		position: relative;
		z-index: 1;
	}

	.cover-header {
		display: flex;
		align-items: center;
		gap: 16px;
		margin-bottom: 18px;
	}

	.cover-thumb {
		width: 72px;
		height: 72px;
		border-radius: var(--radius);
		object-fit: cover;
		flex-shrink: 0;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
	}

	.cover-meta {
		min-width: 0;
	}

	.cover-eyebrow {
		font-size: 0.68rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		font-weight: 700;
		color: var(--text-subtle);
		margin-bottom: 4px;
	}

	.cover-title {
		font-size: 1.3rem;
		font-weight: 700;
		letter-spacing: -0.01em;
		color: var(--text-primary);
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
