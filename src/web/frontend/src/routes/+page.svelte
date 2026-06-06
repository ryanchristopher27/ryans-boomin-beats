<script>
	import { onMount } from 'svelte';
	import { PUBLIC_API_URL } from '$env/static/public';
	import { page } from '../stores.js';
	import SongSearch from '$lib/components/SongSearch.svelte';
	import SongProfile from '$lib/components/SongProfile.svelte';
	import PlaylistResult from '$lib/components/PlaylistResult.svelte';

	let selectedSong = null;
	let discoveryPlaylist = [];
	let discoveryRequested = 0;
	let discoveringLoading = false;
	let discoverError = '';

	onMount(() => {
		$page = 'Explore';
	});

	function onSongSelect(song) {
		selectedSong = song;
		discoveryPlaylist = [];
		discoveryRequested = 0;
		discoverError = '';
	}

	async function onDiscover(selectedTags) {
		if (!selectedSong || selectedTags.length === 0) return;
		discoveringLoading = true;
		discoverError = '';

		const tagList = selectedTags.join(', ');
		const artistName = selectedSong.artists?.[0] ?? selectedSong.artist ?? '';
		const prompt = `Using "${selectedSong.title}" by ${artistName} as a reference point, find 12 songs that share these specific qualities: ${tagList}. Focus on these aspects when choosing songs.`;

		try {
			const res = await fetch(`${PUBLIC_API_URL}/llm/generate-playlist/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ prompt, messages: [], count: 12 }),
			});

			if (res.status === 401) {
				discoverError = 'Connect an AI account using the ⚙ icon in the header to discover songs.';
				return;
			}

			const data = await res.json();
			discoveryPlaylist = data.playlist ?? [];
			discoveryRequested = data.requested ?? 12;
		} catch {
			discoverError = 'Could not reach the server.';
		} finally {
			discoveringLoading = false;
		}
	}

	// Exploration chain: clicking a discovery result loads that song's profile
	function onExploreSong(song) {
		selectedSong = { title: song.title, artists: song.artists, id: song.id };
		discoveryPlaylist = [];
		discoveryRequested = 0;
		discoverError = '';
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}
</script>

<svelte:head>
	<title>Explore — Boomin Beats</title>
	<meta name="description" content="Explore songs and discover new music" />
</svelte:head>

<div class="body-div">
	<div class="search-section" class:compact={selectedSong !== null}>
		{#if !selectedSong}
			<div class="idle-heading">What are you in the mood for?</div>
		{/if}
		<div class="search-wrap">
			<SongSearch onSelect={onSongSelect} />
		</div>
	</div>

	{#if selectedSong}
		<SongProfile song={selectedSong} {onDiscover} />

		{#if discoveringLoading}
			<div class="status-notice">Finding songs...</div>
		{/if}

		{#if discoverError}
			<div class="error-notice">{discoverError}</div>
		{/if}

		{#if discoveryPlaylist.length > 0}
			<div class="discovery-header">Similar Songs</div>
			<PlaylistResult
				playlist={discoveryPlaylist}
				requested={discoveryRequested}
				onSongExplore={onExploreSong}
			/>
		{/if}
	{/if}
</div>

<style>
	.body-div {
		min-height: 100vh;
		width: 100%;
		min-width: 800px;
		margin-top: 65px;
		display: flex;
		flex-direction: column;
	}

	.search-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 100px 20px 40px;
		transition: padding 0.25s ease;
	}

	.search-section.compact {
		padding: 20px;
	}

	.idle-heading {
		font-size: 1.8rem;
		font-weight: 700;
		color: var(--color-light-blue);
		margin-bottom: 28px;
		text-align: center;
	}

	.search-wrap {
		width: 60%;
		min-width: 500px;
	}

	.status-notice {
		text-align: center;
		color: rgba(94, 201, 255, 0.45);
		font-size: 0.85rem;
		padding: 20px;
	}

	.error-notice {
		color: #ff6b6b;
		font-size: 0.8rem;
		text-align: center;
		margin-top: 12px;
	}

	.discovery-header {
		font-size: 0.75rem;
		font-weight: 700;
		color: rgba(94, 201, 255, 0.5);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		margin-top: 28px;
		margin-bottom: 10px;
	}
</style>
