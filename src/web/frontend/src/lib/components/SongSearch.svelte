<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import SongRow from './ui/SongRow.svelte';

	export let onSelect = (song) => {};
	export let placeholder = 'Search for a song...';

	let searchValue = '';
	let tracks = [];
	let open = false;
	let activeIndex = -1;
	let debounceTimer;
	const listId = `songs-${Math.random().toString(36).slice(2)}`;

	function onInput() {
		clearTimeout(debounceTimer);
		// Each search spends Spotify's small daily search quota (tracker e2df2d),
		// so wait for a real pause and at least 3 characters.
		debounceTimer = setTimeout(searchSongs, 350);
	}

	async function searchSongs() {
		const q = searchValue.trim();
		if (q.length < 3) {
			tracks = [];
			open = false;
			return;
		}
		try {
			const res = await fetch(`${PUBLIC_API_URL}/search/?searchValue=${encodeURIComponent(q)}`);
			if (!res.ok) return;
			const data = await res.json();
			tracks = (data.tracks ?? []).slice(0, 8);
			activeIndex = -1;
			open = tracks.length > 0;
		} catch {
			tracks = [];
			open = false;
		}
	}

	function choose(track) {
		searchValue = track.title;
		open = false;
		tracks = [];
		onSelect(track);
	}

	function onKeydown(e) {
		if (!open) return;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			activeIndex = Math.min(activeIndex + 1, tracks.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			activeIndex = Math.max(activeIndex - 1, 0);
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (activeIndex >= 0) choose(tracks[activeIndex]);
		} else if (e.key === 'Escape') {
			open = false;
		}
	}

	function onFocus() {
		if (tracks.length > 0) open = true;
	}

	function onBlur() {
		// Delay so a mousedown on a suggestion still registers.
		setTimeout(() => (open = false), 120);
	}
</script>

<div class="search-container">
	<svg class="search-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
		<path
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			d="M21 21l-4.3-4.3M11 19a8 8 0 1 1 0-16 8 8 0 0 1 0 16z"
		/>
	</svg>
	<input
		class="searchbar"
		{placeholder}
		bind:value={searchValue}
		on:input={onInput}
		on:keydown={onKeydown}
		on:focus={onFocus}
		on:blur={onBlur}
		autocomplete="off"
		role="combobox"
		aria-expanded={open}
		aria-controls={listId}
		aria-activedescendant={open && activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
	/>

	{#if open}
		<ul class="suggestions" id={listId} role="listbox">
			{#each tracks as track, i}
				<li
					id="{listId}-{i}"
					role="option"
					aria-selected={i === activeIndex}
					class:active={i === activeIndex}
					on:mousedown|preventDefault={() => choose(track)}
					on:mouseenter={() => (activeIndex = i)}
				>
					<SongRow title={track.title} artists={track.artists} image={track.image} />
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.search-container {
		position: relative;
		width: 100%;
	}

	.search-icon {
		position: absolute;
		left: 16px;
		top: 50%;
		transform: translateY(-50%);
		color: var(--text-subtle);
		pointer-events: none;
	}

	.searchbar {
		width: 100%;
		box-sizing: border-box;
		height: 48px;
		background-color: var(--surface-1);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		padding: 0 18px 0 44px;
		font-size: 0.95rem;
		transition: border-color var(--transition), box-shadow var(--transition);
	}

	.searchbar::placeholder {
		color: var(--text-subtle);
	}

	.searchbar:focus {
		outline: none;
		border-color: var(--accent);
		box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.15);
	}

	.suggestions {
		position: absolute;
		top: calc(100% + 8px);
		left: 0;
		right: 0;
		margin: 0;
		padding: 6px;
		list-style: none;
		background: var(--popover);
		-webkit-backdrop-filter: blur(30px);
		backdrop-filter: blur(30px);
		border: 1px solid var(--border-control);
		border-radius: 16px;
		box-shadow: var(--shadow-pop);
		z-index: 60;
		max-height: 380px;
		overflow-y: auto;
		animation: bbin 0.18s var(--ease);
	}

	li {
		border-radius: var(--radius-row);
		cursor: pointer;
	}

	/* The row's own hover is replaced by the keyboard/mouse active option. */
	li :global(.row:hover) {
		background: none;
	}

	li.active {
		background: var(--hover);
	}
</style>
