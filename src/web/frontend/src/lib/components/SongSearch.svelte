<script>
	import { PUBLIC_API_URL } from '$env/static/public';

	export let onSelect = (song) => {};
	export let placeholder = 'Search for a song...';

	let searchValue = '';
	let tracks = [];
	let open = false;
	let activeIndex = -1;
	let debounceTimer;

	function onInput() {
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(searchSongs, 220);
	}

	async function searchSongs() {
		const q = searchValue.trim();
		if (!q) {
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
	/>

	{#if open}
		<ul class="suggestions">
			{#each tracks as track, i}
				<li>
					<button
						type="button"
						class="suggestion"
						class:active={i === activeIndex}
						on:mousedown|preventDefault={() => choose(track)}
						on:mouseenter={() => (activeIndex = i)}
					>
						{#if track.image}
							<img class="suggestion-img" src={track.image} alt="" />
						{:else}
							<div class="suggestion-img placeholder"></div>
						{/if}
						<div class="suggestion-text">
							<div class="suggestion-title">{track.title}</div>
							<div class="suggestion-artist">{track.artists.join(', ')}</div>
						</div>
					</button>
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
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
		z-index: 60;
		max-height: 380px;
		overflow-y: auto;
		animation: fadeIn 0.15s ease;
	}

	.suggestion {
		display: flex;
		align-items: center;
		gap: 12px;
		width: 100%;
		padding: 8px 10px;
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		text-align: left;
		transition: background-color var(--transition);
	}

	.suggestion.active {
		background-color: var(--surface-2);
	}

	.suggestion-img {
		width: 40px;
		height: 40px;
		border-radius: var(--radius-sm);
		object-fit: cover;
		flex-shrink: 0;
	}

	.suggestion-img.placeholder {
		background-color: var(--surface-2);
	}

	.suggestion-text {
		min-width: 0;
		flex: 1;
	}

	.suggestion-title {
		color: var(--text-primary);
		font-size: 0.88rem;
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.suggestion-artist {
		color: var(--text-muted);
		font-size: 0.78rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
</style>
