<script>
	// Explore's "Your recipe" column (R3): what you picked, Find similar songs,
	// the Builder hand-off, and the results.
	import { pendingAdd, playlistsPanelOpen } from '../../../stores.js';
	import { queueTracks, rememberSongs } from '$lib/playlistActions.js';
	import { say } from '$lib/toast.js';
	import { cleanFilter, cleanOnly } from '$lib/clean.js';
	import SongRow from '../ui/SongRow.svelte';
	import Icon from '../Icon.svelte';

	export let title = '';
	/** @type {{ kind: 'tag' | 'aspect', label: string }[]} */
	export let picked = [];
	export let loading = false;
	export let error = '';
	/** The discovery results: `{ spotify, reason }[]`. */
	export let results = [];
	export let requested = 0;
	export let onFind = () => {};
	export let onBuild = () => {};
	export let onRemove = (kind, label) => {};
	export let onOpen = (song) => {};

	$: unique = results.filter((s, i, arr) => arr.findIndex((x) => x.spotify.id === s.spotify.id) === i);
	$: ({ shown: songs, hidden } = cleanFilter(unique, $cleanOnly));
	// Results are Deezer-checked (Q3); their ids resolve to Spotify only when used.
	$: rememberSongs(songs.map((s) => s.spotify));
	$: ids = songs.map((s) => s.spotify.id);

	let queued = new Set();
	let busy = new Set();

	async function queue(id) {
		busy = new Set(busy).add(id);
		const r = await queueTracks([id]);
		busy.delete(id);
		busy = busy;
		if (r.ok) queued = new Set(queued).add(id);
		say(r.message);
	}

	async function queueAll() {
		const r = await queueTracks(ids);
		if (r.ok) queued = new Set(ids);
		say(r.message);
	}

	// "Save as playlist" picks a playlist (or New playlist) in the panel.
	function save() {
		$pendingAdd = { trackIds: ids, label: `${ids.length} songs like ${title}`, transient: !$playlistsPanelOpen };
		$playlistsPanelOpen = true;
	}
</script>

<aside class="recipe" aria-label="Your recipe">
	<div class="top">
		<div class="head">
			<h2>Your recipe</h2>
			<span class="count mono">{picked.length} picked</span>
		</div>
		{#if picked.length}
			<div class="picks">
				{#each picked as p (p.kind + p.label)}
					<button class="pick" on:click={() => onRemove(p.kind, p.label)} aria-label="Remove {p.label}">{p.label}<Icon name="x" size={12} /></button>
				{/each}
			</div>
		{:else}
			<p class="hint">Pick tags or things the AI hears. We'll find songs that share them.</p>
		{/if}
		<button class="btn gradient find" on:click={onFind} disabled={!picked.length || loading}>
			{#if loading}<span class="spinner" aria-hidden="true" />{/if}
			{loading ? 'Finding songs…' : 'Find 12 similar songs'}
		</button>
		{#if picked.length}
			<button class="btn build" on:click={onBuild}>Build a playlist from this recipe <span class="arrow">→</span></button>
		{/if}
		{#if error}<p class="error" role="alert">{error}</p>{/if}
	</div>

	<div class="results">
		{#if loading}
			{#each Array(6) as _}
				<div class="skel-row" aria-hidden="true">
					<div class="skeleton cover" />
					<div class="lines"><div class="skeleton" style:width="55%" /><div class="skeleton" style:width="35%" /></div>
				</div>
			{/each}
		{:else if songs.length}
			<div class="results-head">
				<span>{songs.length} songs like {title}</span>
				<span class="links">
					<button class="link" on:click={queueAll}>Queue all</button>
					<button class="link" on:click={save}>Save as playlist</button>
				</span>
			</div>
			{#if hidden}<p class="short">Clean only: {hidden} explicit song{hidden > 1 ? 's' : ''} hidden.</p>{/if}
			{#if requested > 0 && songs.length < requested}
				<p class="short">Could only confirm {songs.length} of {requested} songs on Spotify.</p>
			{/if}
			{#each songs as s (s.spotify.id)}
				<SongRow
					title={s.spotify.title}
					artists={s.spotify.artists}
					image={s.spotify.image}
					reason={s.reason ?? ''}
					dragId={s.spotify.id}
					onOpen={() => onOpen(s.spotify)}
					openLabel="Explore {s.spotify.title}"
					onAdd={() => queue(s.spotify.id)}
					added={queued.has(s.spotify.id)}
					busy={busy.has(s.spotify.id)}
				/>
			{/each}
			<p class="drag-hint">Click a song to explore from it, or drag it onto a playlist.</p>
		{:else}
			<p class="empty">Similar songs show up here. Click one to explore from it.</p>
		{/if}
	</div>
</aside>

<style>
	.recipe {
		display: flex;
		flex-direction: column;
		min-height: 0;
		border-radius: 16px;
		background: var(--surface-1);
		border: 1px solid var(--border-subtle);
	}

	.top {
		display: flex;
		flex-direction: column;
		gap: 12px;
		padding: 20px 20px 16px;
		border-bottom: 1px solid var(--border-subtle);
	}

	.head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
	}

	h2 {
		margin: 0;
		font-size: calc(16px * var(--text-scale, 1));
		font-weight: 600;
	}

	.count {
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.hint {
		margin: 0;
		font-size: calc(14px * var(--text-scale, 1));
		line-height: 1.5;
		color: rgba(243, 243, 245, 0.5);
	}

	.picks {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.pick {
		height: 28px;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 0 6px 0 10px;
		border: none;
		border-radius: 7px;
		background: rgba(var(--accent-rgb), 0.12);
		color: var(--accent-tint-text);
		font: inherit;
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		cursor: pointer;
	}

	.pick:hover {
		background: rgba(var(--accent-rgb), 0.2);
	}

	.find {
		height: 44px;
		border-radius: 11px;
		font-size: calc(14px * var(--text-scale, 1));
		gap: 10px;
	}

	.find:disabled {
		opacity: 1;
		background: var(--surface-active);
		color: var(--text-subtle);
	}

	.build {
		height: 38px;
		border-radius: 11px;
		border-color: var(--border-control);
	}

	.arrow {
		color: var(--text-subtle);
	}

	.error {
		margin: 0;
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--danger-text);
	}

	.results {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 8px;
	}

	.results-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 8px;
		padding: 6px 10px 8px;
		font-size: calc(13px * var(--text-scale, 1));
		font-weight: 500;
		color: var(--text-muted);
	}

	.links {
		display: flex;
		gap: 12px;
		flex: none;
	}

	.link {
		padding: 0;
		border: none;
		background: none;
		color: var(--accent);
		font: inherit;
		font-size: calc(13px * var(--text-scale, 1));
		font-weight: 500;
		cursor: pointer;
	}

	.link:hover {
		color: var(--accent-hover);
	}

	.short,
	.drag-hint {
		margin: 4px 10px 8px;
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.empty {
		margin: 0;
		padding: 28px 16px;
		text-align: center;
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.skel-row {
		display: flex;
		gap: 12px;
		align-items: center;
		padding: 8px 10px;
	}

	.skel-row .cover {
		width: 40px;
		height: 40px;
		border-radius: 7px;
	}

	.lines {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.lines .skeleton {
		height: 10px;
		border-radius: 4px;
	}

	.spinner {
		width: 16px;
		height: 16px;
		border-radius: 50%;
		border: 2px solid rgba(255, 255, 255, 0.35);
		border-top-color: #fff;
		animation: bbspin 0.7s linear infinite;
	}
</style>
