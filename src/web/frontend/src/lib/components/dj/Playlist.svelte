<script>
	// Playlist (F3h): one of your playlists to pick from mid-set. Filter it,
	// + adds a song to Up next. Its songs carry Spotify ids, so adding costs no search.
	import { onMount } from 'svelte';
	import { PUBLIC_API_URL } from '$env/static/public';
	import { userPlaylists } from '../../../stores.js';
	import { spotifyHeaders } from '$lib/spotifyHeaders.js';
	import { say } from '$lib/toast.js';
	import SongRow from '../ui/SongRow.svelte';
	import { asSong, djContext } from './context.js';

	/** @type {any} */
	export let dj;
	const { doc } = dj;
	const { selected } = djContext();

	let playlistId = '';
	let tracks = [];
	let filter = '';
	let status = 'idle'; // idle | loading | error
	let added = new Set();

	onMount(async () => {
		if ($userPlaylists.length) return;
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/playlists/`, { headers: spotifyHeaders() });
			if (res.ok) $userPlaylists = (await res.json()).playlists ?? [];
		} catch {
			status = 'error';
		}
	});

	async function open(id) {
		tracks = [];
		filter = '';
		added = new Set();
		if (!id) return;
		status = 'loading';
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/playlist-tracks/?playlist_id=${encodeURIComponent(id)}`, { headers: spotifyHeaders() });
			if (!res.ok) throw new Error(String(res.status));
			tracks = (await res.json()).tracks ?? [];
			status = 'idle';
		} catch {
			status = 'error';
		}
	}

	$: open(playlistId);
	$: q = filter.trim().toLowerCase();
	$: clean = $doc.options.clean;
	$: allowed = clean ? tracks.filter((t) => !t.explicit) : tracks;
	$: shown = q ? allowed.filter((t) => `${t.title} ${t.artists.join(' ')}`.toLowerCase().includes(q)) : allowed;

	async function add(t) {
		added = new Set(added).add(t.id);
		await dj.add(t);
		say(`Added ${t.title} to Up next.`);
	}
</script>

<div class="playlist">
	<div class="pick">
		<select bind:value={playlistId} aria-label="Choose a playlist">
			<option value="">{$userPlaylists.length ? 'Choose a playlist…' : 'Loading your playlists…'}</option>
			{#each $userPlaylists as p (p.id)}
				<option value={p.id}>{p.name} ({p.track_count})</option>
			{/each}
		</select>
		{#if tracks.length}
			<input type="search" placeholder="Filter songs" aria-label="Filter songs" bind:value={filter} />
		{/if}
	</div>

	{#if status === 'loading'}
		<p class="note">Loading songs…</p>
	{:else if status === 'error'}
		<p class="note error">Couldn't load that. Try again in a moment.</p>
	{:else if !playlistId}
		<p class="note">Pick a playlist to queue songs from it.</p>
	{:else if !shown.length}
		<p class="note">{q ? `Nothing matches “${filter.trim()}”.` : 'No songs to show.'}</p>
	{:else}
		{#if clean && allowed.length < tracks.length}
			<p class="note">Clean only: {tracks.length - allowed.length} explicit hidden.</p>
		{/if}
		<ul>
			{#each shown as t (t.id)}
				<li>
					<SongRow
						compact
						title={t.title}
						artists={t.artists}
						image={t.image}
						selected={$selected?.id === t.id}
						onOpen={() => selected.set(asSong(t))}
						openLabel="Show the profile of {t.title}"
						onAdd={() => add(t)}
						addLabel="Add to Up next"
						added={added.has(t.id)}
					/>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.playlist {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 8px 10px 12px;
	}

	.pick {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 0 4px;
	}

	select,
	input {
		width: 100%;
		height: 34px;
		padding: 0 10px;
		border-radius: 9px;
		border: 1px solid var(--border-control);
		background: var(--surface-2, rgba(255, 255, 255, 0.04));
		color: var(--text-primary);
		font: inherit;
		font-size: calc(13px * var(--text-scale, 1));
	}

	select:focus-visible,
	input:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 1px;
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.note {
		margin: 4px 6px 0;
		font-size: calc(13px * var(--text-scale, 1));
		line-height: 1.45;
		color: var(--text-muted);
	}

	.note.error {
		color: var(--danger-text);
	}
</style>
