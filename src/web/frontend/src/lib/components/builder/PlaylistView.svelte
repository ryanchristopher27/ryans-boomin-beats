<script>
	// The Builder's playlist column (R4): a cover-mosaic hero, Save / Queue /
	// Add to a playlist, and the songs.
	import { djSetRequest, pendingAdd, playlistsPanelOpen } from '../../../stores.js';
	import { goto } from '$app/navigation';
	import { createPlaylist, getSavedStates, queueTracks, rememberSongs, setTrackSaved } from '$lib/playlistActions.js';
	import { coverHue } from '$lib/dj/ambience.js';
	import { playlistMeta } from '$lib/builder.js';
	import { say } from '$lib/toast.js';
	import { cleanFilter, cleanOnly } from '$lib/clean.js';
	import SongRow from '../ui/SongRow.svelte';
	import PlaylistNameModal from '../PlaylistNameModal.svelte';
	import Icon from '../Icon.svelte';

	/** `{ spotify, reason }[]` */
	export let tracks = [];
	export let requested = 0;
	export let name = '';
	export let prompt = '';
	export let aiLabel = '';
	/** The first build is running: skeleton rows. */
	export let building = false;
	/** A refine is running: the list dims. */
	export let refining = false;
	export let onOpen = (song) => {};

	$: unique = tracks.filter((s, i, arr) => arr.findIndex((x) => x.spotify.id === s.spotify.id) === i);
	$: ({ shown: songs, hidden } = cleanFilter(unique, $cleanOnly));
	// Results are Deezer-checked (Q3); their ids resolve to Spotify only when used.
	$: rememberSongs(songs.map((s) => s.spotify));
	$: ids = songs.map((s) => s.spotify.id);
	$: covers = songs.map((s) => s.spotify.image).filter(Boolean).slice(0, 4);
	let hue = 285;
	$: coverHue(covers[0], name).then((h) => (hue = h));

	let saved = {};
	let savedKey = '';
	$: loadSaved(ids);
	async function loadSaved(keys) {
		const key = keys.join(',');
		if (key === savedKey || !keys.length) return;
		savedKey = key;
		saved = await getSavedStates(keys);
	}

	async function toggleSaved(id) {
		const next = !saved[id];
		saved = { ...saved, [id]: next };
		const r = await setTrackSaved(id, next);
		if (r.error) {
			saved = { ...saved, [id]: !next };
			say(r.error === 'reconnect' ? 'Reconnect Spotify on Profile to save songs.' : r.error === 'not_on_spotify' ? "That song isn't on Spotify." : "Couldn't update Liked Songs.");
		}
	}

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

	let naming = false;
	async function save(title) {
		naming = false;
		const r = await createPlaylist(title, ids);
		if (r.ok) say(r.missing ? `Saved ${title}. ${r.missing} song${r.missing > 1 ? "s weren't" : " wasn't"} on Spotify.` : `Saved ${title} to Spotify.`);
		else say(r.error === 'auth' ? 'Log in to Spotify on the Profile page first.' : "Couldn't save the playlist.");
	}

	// F3h: the DJ page resolves these and appends them to Up next.
	function startSet() {
		$djSetRequest = songs.map((s) => s.spotify);
		goto('/dj/');
	}

	function addToPlaylist() {
		$pendingAdd = { trackIds: ids, label: `${ids.length} songs`, transient: !$playlistsPanelOpen };
		$playlistsPanelOpen = true;
	}
</script>

<section class="view" aria-label="Playlist">
	<div class="hero" style:--h={hue}>
		<div class="hero-inner">
			<div class="mosaic" aria-hidden="true">
				{#each Array(4) as _, i}
					{#if covers[i] ?? covers[0]}<img src={covers[i] ?? covers[0]} alt="" />{:else}<span class="blank" style:--h={hue + i * 40} />{/if}
				{/each}
			</div>
			<div class="meta">
				<p class="eyebrow">Playlist · made with {aiLabel}</p>
				<h1>{building ? 'Building…' : name}</h1>
				<p class="sub">{building ? 'Picking songs…' : `${playlistMeta(songs)} · made for “${prompt}”`}</p>
				<div class="actions">
					<button class="btn white pill" on:click={() => (naming = true)} disabled={!ids.length || building}>Save to Spotify</button>
					<button class="btn pill ghost" on:click={queueAll} disabled={!ids.length || building}>Add all to queue</button>
					<button class="btn pill ghost" on:click={addToPlaylist} disabled={!ids.length || building}><Icon name="playlist" size={15} /> Add to a playlist</button>
						<button class="btn pill ghost" on:click={startSet} disabled={!ids.length || building}><Icon name="disc" size={15} /> Start a DJ set</button>
				</div>
			</div>
		</div>
	</div>

	<div class="list-wrap">
		{#if hidden && !building}<p class="short">Clean only: {hidden} explicit song{hidden > 1 ? 's' : ''} hidden.</p>{/if}
		{#if requested > 0 && !building && songs.length && songs.length < requested}
			<p class="short">Found {songs.length} of {requested} songs on Spotify. Refine it to ask for more.</p>
		{/if}
		{#if building}
			<div aria-busy="true">
				{#each [62, 48, 70, 55, 40, 66, 52, 58] as w}
					<div class="skel-row">
						<span class="rank" />
						<span class="skeleton cover" />
						<span class="lines"><span class="skeleton" style:width="{w}%" /><span class="skeleton" style:width="30%" /></span>
					</div>
				{/each}
			</div>
		{:else}
			<div class="list" class:dim={refining}>
				{#each songs as s, i (s.spotify.id)}
					<SongRow
						index={i + 1}
						title={s.spotify.title}
						artists={s.spotify.artists}
						image={s.spotify.image}
						reason={s.reason ?? ''}
						showReason={false}
						duration={s.spotify.duration_ms}
						dragId={s.spotify.id}
						previewSong={s.spotify}
						onOpen={() => onOpen(s.spotify)}
						openLabel="Explore {s.spotify.title}"
						onAdd={() => queue(s.spotify.id)}
						added={queued.has(s.spotify.id)}
						busy={busy.has(s.spotify.id)}
					>
						<button
							slot="actions"
							class="row-btn heart"
							class:on={saved[s.spotify.id]}
							on:click|stopPropagation={() => toggleSaved(s.spotify.id)}
							aria-pressed={!!saved[s.spotify.id]}
							aria-label={saved[s.spotify.id] ? `Remove ${s.spotify.title} from Liked Songs` : `Save ${s.spotify.title} to Liked Songs`}
						>
							<Icon name="heart" size={15} filled={saved[s.spotify.id]} />
						</button>
					</SongRow>
				{/each}
			</div>
			<p class="hint">Click any song to explore from it, or drag it onto a playlist.</p>
		{/if}
	</div>
</section>

{#if naming}
	<PlaylistNameModal initial={name} onSave={save} onCancel={() => (naming = false)} />
{/if}

<style>
	.view {
		min-height: 0;
		height: 100%;
		overflow-y: auto;
		overflow-x: hidden;
	}

	.hero {
		padding: 48px 32px 32px;
		background: linear-gradient(180deg, oklch(0.32 0.08 var(--h)) 0%, oklch(0.18 0.03 var(--h)) 65%, var(--surface-0) 100%);
	}

	.hero-inner {
		max-width: 880px;
		margin: 0 auto;
		display: flex;
		gap: 28px;
		align-items: flex-end;
		flex-wrap: wrap;
	}

	.mosaic {
		flex: none;
		width: 220px;
		height: 220px;
		display: grid;
		grid-template-columns: 1fr 1fr;
		overflow: hidden;
		border-radius: 16px;
		box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5);
	}

	.mosaic img,
	.mosaic .blank {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.blank {
		background: linear-gradient(140deg, oklch(0.66 0.12 var(--h)), oklch(0.32 0.08 calc(var(--h) + 45)));
	}

	.meta {
		flex: 1;
		min-width: 280px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.eyebrow {
		margin: 0;
		font-family: var(--font-mono);
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		color: rgba(243, 243, 245, 0.65);
	}

	h1 {
		margin: 0;
		font-size: calc(clamp(40px, 7vw, 68px) * var(--text-scale, 1));
		font-weight: 700;
		line-height: 0.95;
		letter-spacing: -0.045em;
		text-wrap: balance;
	}

	.sub {
		margin: 0;
		font-size: calc(14px * var(--text-scale, 1));
		color: rgba(243, 243, 245, 0.75);
	}

	.actions {
		display: flex;
		gap: 8px;
		margin-top: 10px;
		flex-wrap: wrap;
	}

	.pill {
		height: 44px;
		padding: 0 18px;
		border-radius: 999px;
		font-size: calc(14px * var(--text-scale, 1));
	}

	.ghost {
		border-color: rgba(255, 255, 255, 0.22);
		background: rgba(0, 0, 0, 0.2);
	}

	.list-wrap {
		max-width: 880px;
		margin: 0 auto;
		padding: 24px 32px 48px;
	}

	.short {
		margin: 0 0 12px;
		padding: 10px 14px;
		border-radius: 10px;
		background: rgba(255, 180, 84, 0.07);
		border: 1px solid rgba(255, 180, 84, 0.2);
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--warning);
	}

	.list {
		display: flex;
		flex-direction: column;
		gap: 2px;
		transition: opacity 0.2s var(--ease);
	}

	.list.dim {
		opacity: 0.4;
		pointer-events: none;
	}

	.heart.on {
		color: var(--accent);
	}

	.hint {
		margin: 16px 0 0;
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.skel-row {
		display: flex;
		gap: 12px;
		align-items: center;
		padding: 8px 10px;
	}

	.skel-row .rank {
		width: 20px;
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

	@media (max-width: 759px) {
		.hero,
		.list-wrap {
			padding-left: 16px;
			padding-right: 16px;
		}
		.mosaic {
			width: 160px;
			height: 160px;
		}
	}
</style>
