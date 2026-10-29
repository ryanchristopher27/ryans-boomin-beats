<script>
	// ⌘K / Ctrl+K command palette (F4): songs (recent, then type-ahead search) and
	// Go to. On the DJ page a song joins Up next; elsewhere it opens in Explore.
	import { tick } from 'svelte';
	import { get } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { PUBLIC_API_URL } from '$env/static/public';
	import { paletteOpen, exploreTrail, selectedSong, discoveryPlaylist, llmSettingsOpen } from '../../stores.js';
	import { settingsTab } from '$lib/settings.js';
	import { getDJ } from '$lib/dj/instance.js';
	import { say } from '$lib/toast.js';
	import { spotifyHeaders } from '$lib/spotifyHeaders.js';
	import { buildItems, countLabel, moveSelection, recentSongs, MIN_QUERY } from '$lib/palette.js';
	import SongRow from './ui/SongRow.svelte';
	import Icon from './Icon.svelte';

	let wasOpen = false;
	let query = '';
	let input;
	let results = [];
	let recent = [];
	let active = 0;
	let opener = null;
	/** The query `results` answers, for the no-match message. */
	let searched = '';
	let timer;
	const listId = 'palette-list';

	$: if ($paletteOpen) opened();
	$: items = buildItems(query, { recent, results });
	$: if (active >= items.length) active = Math.max(items.length - 1, 0);
	$: songItems = items.filter((i) => i.kind === 'song');
	$: pageItems = items.filter((i) => i.kind === 'page');

	function opened() {
		if (wasOpen) return;
		wasOpen = true;
		opener = document.activeElement;
		query = '';
		results = [];
		searched = '';
		active = 0;
		const dj = getDJ();
		recent = recentSongs(get(exploreTrail), dj ? get(dj.doc).recent : []);
		tick().then(() => input?.focus());
	}

	function close() {
		clearTimeout(timer);
		$paletteOpen = false;
		wasOpen = false;
		const el = opener;
		opener = null;
		tick().then(() => el?.focus?.());
	}

	function onWindowKey(e) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			if ($paletteOpen) close();
			// Not over another dialog (Save tonight's set, first run): it would open underneath.
			else if (!document.querySelector('[role=dialog]')) $paletteOpen = true;
		} else if ($paletteOpen && e.key === 'Escape') {
			// The input handles Esc itself; this catches it after a click elsewhere in the palette took focus.
			close();
		}
	}

	// Same endpoint and pacing as the other type-ahead (SongSearch): Deezer/Last.fm
	// backed, so no Spotify quota per keystroke. Wait for a pause and 3+ characters.
	function onInput() {
		clearTimeout(timer);
		active = 0;
		const q = query.trim();
		if (q.length < MIN_QUERY) {
			results = [];
			searched = '';
			return;
		}
		timer = setTimeout(async () => {
			try {
				const res = await fetch(`${PUBLIC_API_URL}/search/?searchValue=${encodeURIComponent(q)}`, { headers: spotifyHeaders() });
				if (!res.ok || q !== query.trim()) return;
				results = ((await res.json()).tracks ?? []).slice(0, 6);
				searched = q;
			} catch {
				results = [];
			}
		}, 350);
	}

	function onKeydown(e) {
		if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
			e.preventDefault();
			active = moveSelection(active, e.key, items.length);
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (items[active]) choose(items[active]);
		} else if (e.key === 'Escape') {
			e.preventDefault();
			close();
		} else if (e.key === 'Tab') {
			e.preventDefault(); // the input is the only stop
		} else return;
		// The DJ page maps arrows to moves and Esc to cancel editing; keep them out of it.
		e.stopPropagation();
	}

	async function choose(item) {
		close();
		if (item.kind === 'page') {
			if (item.page.href) return goto(item.page.href);
			$settingsTab = 'general';
			$llmSettingsOpen = true;
			return;
		}
		const song = item.song;
		const dj = getDJ();
		if (dj && location.pathname.startsWith('/dj')) {
			const r = await dj.addPick(song);
			say(r.ok ? `Added ${song.title} to Up next.` : r.reason === 'not_on_spotify' ? `${song.title} isn't on Spotify.` : r.reason === 'explicit' ? `Only an explicit version of ${song.title} is on Spotify.` : "Couldn't add that right now.");
			return;
		}
		$selectedSong = { title: song.title, artists: song.artists, id: song.id, image: song.image, isrc: song.isrc };
		$exploreTrail = [$selectedSong];
		$discoveryPlaylist = [];
		goto('/');
	}
</script>

<svelte:window on:keydown={onWindowKey} />

{#if $paletteOpen}
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<div class="scrim" on:click={close} />
	<div class="palette" role="dialog" aria-modal="true" aria-label="Command palette">
		<div class="field">
			<Icon name="search" size={16} />
			<input
				bind:this={input}
				bind:value={query}
				on:input={onInput}
				on:keydown={onKeydown}
				placeholder="Search songs or jump to a page…"
				aria-label="Search songs or jump to a page"
				autocomplete="off"
				role="combobox"
				aria-expanded="true"
				aria-controls={listId}
				aria-activedescendant={items.length ? `${listId}-${active}` : undefined}
			/>
			<kbd class="mono">Esc</kbd>
		</div>
		<div class="body" id={listId} role="listbox" aria-label="Results">
			{#if songItems.length}
				<div class="group" role="presentation">{query.trim() ? 'Songs' : 'Recent'}</div>
				{#each songItems as item, i (item.song.id ?? item.song.title + i)}
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					<div id="{listId}-{i}" class="opt" class:active={i === active} role="option" tabindex="-1" aria-selected={i === active} on:mousedown|preventDefault on:click={() => choose(item)} on:mouseenter={() => (active = i)}>
						<SongRow compact title={item.song.title} artists={item.song.artists} image={item.song.image} />
					</div>
				{/each}
			{:else if searched && searched === query.trim()}
				<p class="none" role="presentation">No songs match “{searched}”. Try an artist name.</p>
			{/if}
			{#if pageItems.length}
				<div class="group" role="presentation">Go to</div>
				{#each pageItems as item, j}
					{@const i = songItems.length + j}
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					<div id="{listId}-{i}" class="opt page" class:active={i === active} role="option" tabindex="-1" aria-selected={i === active} on:mousedown|preventDefault on:click={() => choose(item)} on:mouseenter={() => (active = i)}>
						<Icon name={item.page.icon} size={16} />
						{item.page.label}
					</div>
				{/each}
			{/if}
		</div>
		<div class="sr" role="status" aria-live="polite">{countLabel(items)}</div>
	</div>
{/if}

<style>
	.scrim {
		position: fixed;
		inset: 0;
		z-index: 70;
		background: rgba(0, 0, 0, 0.35);
	}

	.palette {
		position: fixed;
		z-index: 71;
		top: 14vh;
		left: 50%;
		transform: translateX(-50%);
		width: min(620px, calc(100vw - 32px));
		max-height: 72vh;
		display: flex;
		flex-direction: column;
		border-radius: 18px;
		background: var(--popover);
		-webkit-backdrop-filter: blur(30px);
		backdrop-filter: blur(30px);
		border: 1px solid var(--border-control);
		box-shadow: var(--shadow-pop);
		overflow: hidden;
		animation: bbin 0.18s var(--ease);
	}

	.field {
		flex: none;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 0 16px;
		height: 54px;
		border-bottom: 1px solid var(--border-subtle);
		color: var(--text-subtle);
	}

	input {
		flex: 1;
		min-width: 0;
		height: 100%;
		border: none;
		background: none;
		color: var(--text-primary);
		font: inherit;
		font-size: calc(15px * var(--text-scale, 1));
	}

	input::placeholder {
		color: var(--text-subtle);
	}

	input:focus {
		outline: none;
	}

	kbd {
		padding: 2px 6px;
		border-radius: 5px;
		border: 1px solid var(--border-control);
		font-size: calc(11px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.body {
		overflow-y: auto;
		padding: 6px;
	}

	.group {
		padding: 10px 10px 4px;
		font-size: calc(11px * var(--text-scale, 1));
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-subtle);
	}

	.opt {
		border-radius: var(--radius-row);
		cursor: pointer;
	}

	.opt.active {
		background: var(--hover);
	}

	/* The active option replaces the row's own hover. */
	.opt :global(.row:hover) {
		background: none;
	}

	.opt.page {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 9px 10px;
		font-size: calc(14px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.opt.page.active {
		color: var(--text-primary);
	}

	.none {
		margin: 0;
		padding: 12px 10px;
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.sr {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
		white-space: nowrap;
	}
</style>
