<script>
	import { PUBLIC_API_URL } from '$env/static/public';

	export let onSelect = (song) => {};
	export let placeholder = 'Search for a song...';

	let searchValue = '';
	let tracks = [];
	let trackTitles = [];

	async function searchSongs() {
		if (!searchValue.trim()) { tracks = []; return; }
		try {
			const res = await fetch(`${PUBLIC_API_URL}/search/?searchValue=${encodeURIComponent(searchValue)}`);
			if (!res.ok) return;
			const data = await res.json();
			tracks = data.tracks ?? [];
			trackTitles = tracks.map(t => t.title);
		} catch {
			tracks = [];
		}
	}

	function selectTrack(title) {
		const idx = trackTitles.indexOf(title);
		if (idx === -1) return;
		const song = tracks[idx];
		searchValue = title;
		tracks = [];
		trackTitles = [];
		onSelect(song);
	}
</script>

<div class="search-container">
	<input
		class="searchbar"
		list="song-search-datalist"
		{placeholder}
		bind:value={searchValue}
		on:input={searchSongs}
		on:change={() => selectTrack(searchValue)}
	/>
	<datalist id="song-search-datalist">
		{#each tracks as track}
			<option value={track.title}>{track.title} — {track.artists[0]}</option>
		{/each}
	</datalist>
</div>

<style>
	.search-container {
		width: 100%;
	}

	.searchbar {
		width: 100%;
		box-sizing: border-box;
		height: 40px;
		background-color: var(--color-dark-gray);
		color: var(--color-light-blue);
		border: 2px solid var(--color-light-blue);
		border-radius: 10px;
		padding: 0 14px;
		font-size: 0.9rem;
	}

	.searchbar::placeholder {
		color: rgba(94, 201, 255, 0.4);
	}
</style>
