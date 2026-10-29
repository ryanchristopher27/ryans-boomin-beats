<script>
	import { openSettings } from '$lib/settings.js';
	import { relayFetch } from '$lib/llmRelay.js';
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { PUBLIC_API_URL } from '$env/static/public';
	import {
		page,
		selectedSong,
		discoveryPlaylist,
		discoveryRequested,
		exploreSession,
		exploreTrail,
		builderRequest
	} from '../stores.js';
	import { llmHeaders } from '$lib/llmHeaders.js';
	import { spotifyHeaders } from '$lib/spotifyHeaders.js';
	import { queueTracks, rememberSongs } from '$lib/playlistActions.js';
	import { coverHue, nameHue } from '$lib/dj/ambience.js';
	import { builderPrompt, discoverPrompt, extendTrail, parseAnalysis } from '$lib/explore.js';
	import { say } from '$lib/toast.js';
	import SongSearch from '$lib/components/SongSearch.svelte';
	import SongProfile from '$lib/components/SongProfile.svelte';
	import TopTrackSeeds from '$lib/components/TopTrackSeeds.svelte';
	import Recipe from '$lib/components/explore/Recipe.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const MOODS = ['Late night drive', 'Sunday morning coffee', 'Pregame energy', 'Deep focus, no lyrics'];

	let discovering = false;
	let discoverError = '';
	let idleSearch;
	let queueing = false;

	onMount(() => {
		$page = 'Explore';
	});

	// --- Idle: the hero takes the hovered top track's hue ---
	let hovered = null;
	let heroHue = 235;
	async function hoverTrack(t) {
		hovered = t;
		const h = await coverHue(t.image, t.title);
		if (hovered === t) heroHue = h;
	}

	// --- Song page ---
	$: song = $selectedSong;
	let songHue = 235;
	$: if (song) coverHue(song.image, song.title).then((h) => (songHue = h));
	// A song restored from before the Path existed still gets its crumb.
	$: crumbs = $exploreTrail.length ? $exploreTrail : song ? [song] : [];
	$: profile = $exploreSession.profile;
	$: aspects = parseAnalysis(profile?.analysis);
	$: picked = [
		...$exploreSession.selectedTags.map((label) => ({ kind: /** @type {'tag'} */ ('tag'), label })),
		...$exploreSession.selectedAspects.map((label) => ({ kind: /** @type {'aspect'} */ ('aspect'), label }))
	];

	async function show(s) {
		$selectedSong = s;
		$discoveryPlaylist = [];
		$discoveryRequested = 0;
		discoverError = '';
		await tick();
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}

	/** A new start (search or a top track): the Path begins again. */
	function start(s) {
		rememberSongs([s]);
		$exploreTrail = [s];
		show(s);
	}

	/** Opened from the results: the Path grows from the current song. */
	function exploreFrom(s) {
		$exploreTrail = extendTrail($exploreTrail, song?.id, s);
		show(s);
	}

	async function newSearch() {
		$selectedSong = null;
		$discoveryPlaylist = [];
		$discoveryRequested = 0;
		await tick();
		idleSearch?.focus();
	}

	function removePick(kind, label) {
		const key = kind === 'tag' ? 'selectedTags' : 'selectedAspects';
		$exploreSession = { ...$exploreSession, [key]: $exploreSession[key].filter((x) => x !== label) };
	}

	async function find() {
		if (!song || !picked.length) return;
		discovering = true;
		discoverError = '';
		const chosen = aspects.filter((a) => $exploreSession.selectedAspects.includes(a.label));
		try {
			const res = await relayFetch(`${PUBLIC_API_URL}/llm/generate-playlist/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', ...spotifyHeaders(), ...llmHeaders() },
				body: JSON.stringify({ prompt: discoverPrompt(song, $exploreSession.selectedTags, chosen), messages: [], count: 12 })
			});
			if (res.status === 401) {
				discoverError = 'Add an AI key in Settings to find similar songs.';
				return;
			}
			const data = await res.json();
			$discoveryPlaylist = data.playlist ?? [];
			$discoveryRequested = data.requested ?? 12;
		} catch {
			discoverError = 'Could not reach the server.';
		} finally {
			discovering = false;
		}
	}

	function buildFromRecipe() {
		$builderRequest = builderPrompt(song, picked.map((p) => p.label));
		goto('/playlist-builder/');
	}

	function mood(m) {
		$builderRequest = m;
		goto('/playlist-builder/');
	}

	async function queueSong() {
		queueing = true;
		const r = await queueTracks([song.id]);
		queueing = false;
		say(r.message);
	}

	const stats = (p) =>
		p?.listeners > 0 ? `${p.listeners.toLocaleString()} listeners${p.play_count > 0 ? ` · ${p.play_count.toLocaleString()} plays` : ''} on Last.fm` : '';
</script>

<svelte:head>
	<title>{song ? `${song.title} · Explore` : 'Explore'} · Boomin Beats</title>
	<meta name="description" content="Explore songs and discover new music" />
</svelte:head>

{#if !song}
	<div class="bleed">
		<section class="hero" style:--h={heroHue}>
			<div class="hero-inner">
				<p class="eyebrow">Explore{hovered ? ` · ${hovered.title}` : ''}</p>
				<h1>What are you in the mood for?</h1>
				<div class="search">
					<SongSearch bind:this={idleSearch} variant="hero" onSelect={start} />
				</div>
				<div class="moods">
					{#each MOODS as m}
						<button class="chip mood" on:click={() => mood(m)}>{m}</button>
					{/each}
				</div>
			</div>
		</section>
		<div class="below">
			<TopTrackSeeds onSelect={start} onHover={hoverTrack} />
		</div>
	</div>
{:else}
	<div class="bleed">
		<div class="pathbar">
			<button class="square" on:click={newSearch} aria-label="Back to Explore"><Icon name="back" size={16} /></button>
			<span class="path-label mono">Path</span>
			<ol class="trail">
				{#each crumbs as t, i (t.id)}
					<li>
						{#if i > 0}<span class="sep" aria-hidden="true">→</span>{/if}
						<button class="crumb" class:current={t.id === song.id} aria-current={t.id === song.id ? 'step' : undefined} on:click={() => show(t)}>
							{#if t.image}<img src={t.image} alt="" />{:else}<span class="dot" style:--h={nameHue(t.title)} />{/if}
							{t.title}
						</button>
					</li>
				{/each}
			</ol>
			<button class="btn small new" on:click={newSearch}><Icon name="search" size={14} /> New search</button>
		</div>

		<section class="song-hero" style:--h={songHue}>
			<div class="song-hero-inner">
				{#key song.id}
					{#if song.image}
						<img class="big-cover" src={song.image} alt="" />
					{:else}
						<div class="big-cover blank mono" style:--h={nameHue(song.title)}>{song.title.slice(0, 2).toUpperCase()}</div>
					{/if}
				{/key}
				<div class="song-meta">
					<p class="eyebrow">Song</p>
					<h1>{profile?.title ?? song.title}</h1>
					<p class="artist">{profile?.artist ?? song.artists?.join(', ') ?? ''}</p>
					{#if stats(profile)}<p class="stats mono">{stats(profile)}</p>{/if}
				</div>
				<div class="song-actions">
					<button class="btn white pill" on:click={queueSong} disabled={queueing}>
						<Icon name="plus" size={15} /> Add to queue
					</button>
				</div>
			</div>
		</section>

		<div class="columns">
			<SongProfile {song} />
			<div class="recipe-col">
				<Recipe
					title={song.title}
					{picked}
					loading={discovering}
					error={discoverError}
					results={$discoveryPlaylist}
					requested={$discoveryRequested}
					onFind={find}
					onBuild={buildFromRecipe}
					onRemove={removePick}
					onOpen={exploreFrom}
				/>
				{#if discoverError.startsWith('Add an AI key')}
					<button class="btn small key" on:click={() => openSettings('ai')}>Open AI settings</button>
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	/* Explore's heroes run edge to edge, under the page padding. */
	.bleed {
		margin: calc(var(--primary-spacing) * -1) calc(var(--primary-spacing) * -1) 0;
		min-width: 0;
	}

	.eyebrow {
		margin: 0;
		font-family: var(--font-mono);
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		color: rgba(243, 243, 245, 0.6);
	}

	/* --- Idle --- */
	.hero {
		padding: 11vh 32px 56px;
		background: radial-gradient(90% 120% at 50% 0%, oklch(0.32 0.08 var(--h)) 0%, oklch(0.16 0.03 var(--h)) 55%, var(--surface-0) 100%);
	}

	.hero-inner {
		max-width: 880px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 22px;
		text-align: center;
	}

	h1 {
		margin: 0;
		font-size: calc(clamp(44px, 9vw, 84px) * var(--text-scale, 1));
		font-weight: 700;
		line-height: 0.95;
		letter-spacing: -0.05em;
		text-wrap: balance;
	}

	.search {
		position: relative;
		z-index: 5;
		width: 100%;
		max-width: 680px;
		margin-top: 10px;
	}

	.moods {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 8px;
	}

	.mood {
		height: 34px;
		padding: 0 14px;
		border-color: rgba(255, 255, 255, 0.14);
		background: rgba(10, 10, 12, 0.35);
	}

	.mood:hover {
		background: rgba(255, 255, 255, 0.08);
	}

	.below {
		max-width: 1240px;
		margin: 0 auto;
		padding: 8px 32px 64px;
	}

	/* --- Song page --- */
	.pathbar {
		position: sticky;
		top: var(--header-height);
		z-index: 20;
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 28px;
		background: rgba(10, 10, 12, 0.92);
		-webkit-backdrop-filter: blur(20px);
		backdrop-filter: blur(20px);
		border-bottom: 1px solid rgba(255, 255, 255, 0.06);
	}

	.square {
		flex: none;
		width: 34px;
		height: 34px;
		display: grid;
		place-items: center;
		padding: 0;
		border-radius: 9px;
		border: 1px solid rgba(255, 255, 255, 0.08);
		background: var(--surface-1);
		color: var(--text-primary);
		cursor: pointer;
	}

	.square:hover {
		background: var(--surface-2);
	}

	.path-label {
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		color: var(--text-subtle);
	}

	.trail {
		flex: 1;
		min-width: 0;
		display: flex;
		align-items: center;
		gap: 6px;
		margin: 0;
		padding: 0;
		list-style: none;
		overflow-x: auto;
		scrollbar-width: none;
	}

	.trail li {
		flex: none;
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.sep {
		font-size: calc(12px * var(--text-scale, 1));
		color: rgba(243, 243, 245, 0.25);
	}

	.crumb {
		height: 28px;
		display: flex;
		align-items: center;
		gap: 7px;
		padding: 0 10px 0 4px;
		border-radius: 8px;
		border: 1px solid transparent;
		background: transparent;
		color: var(--text-muted);
		font: inherit;
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		white-space: nowrap;
		cursor: pointer;
	}

	.crumb:hover {
		background: var(--hover);
		color: var(--text-primary);
	}

	.crumb.current {
		border-color: var(--border-strong);
		background: var(--surface-active);
		color: var(--text-primary);
	}

	.crumb img,
	.dot {
		width: 20px;
		height: 20px;
		border-radius: 5px;
		object-fit: cover;
	}

	.dot {
		background: linear-gradient(140deg, oklch(0.66 0.12 var(--h)), oklch(0.32 0.08 calc(var(--h) + 45)));
	}

	.new {
		flex: none;
		border-color: rgba(255, 255, 255, 0.08);
		background: var(--surface-1);
		color: var(--text-muted);
	}

	.song-hero {
		padding: 56px 28px 40px;
		background: linear-gradient(180deg, oklch(0.3 0.07 var(--h)) 0%, oklch(0.18 0.03 var(--h)) 60%, var(--surface-0) 100%);
	}

	.song-hero-inner {
		max-width: 1240px;
		margin: 0 auto;
		display: flex;
		align-items: flex-end;
		gap: 32px;
		flex-wrap: wrap;
	}

	.big-cover {
		flex: none;
		width: 232px;
		height: 232px;
		border-radius: 14px;
		object-fit: cover;
		box-shadow: 0 30px 80px rgba(0, 0, 0, 0.45);
		animation: bbpop 0.55s var(--ease);
	}

	.big-cover.blank {
		display: grid;
		place-items: center;
		background: linear-gradient(140deg, oklch(0.66 0.12 var(--h)), oklch(0.32 0.08 calc(var(--h) + 45)));
		font-size: calc(40px * var(--text-scale, 1));
		font-weight: 600;
		color: rgba(255, 255, 255, 0.8);
	}

	.song-meta {
		flex: 1;
		min-width: 300px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.song-meta h1 {
		font-size: calc(clamp(40px, 8vw, 76px) * var(--text-scale, 1));
		letter-spacing: -0.045em;
	}

	.artist {
		margin: 0;
		font-size: calc(20px * var(--text-scale, 1));
		font-weight: 500;
		color: rgba(243, 243, 245, 0.8);
	}

	.stats {
		margin: 0;
		font-size: calc(13px * var(--text-scale, 1));
		color: rgba(243, 243, 245, 0.5);
	}

	.song-actions {
		display: flex;
		gap: 8px;
	}

	.pill {
		height: 44px;
		padding: 0 20px;
		border-radius: 999px;
		font-size: calc(14px * var(--text-scale, 1));
	}

	.columns {
		max-width: 1296px;
		margin: 0 auto;
		padding: 24px 28px 64px;
		display: grid;
		grid-template-columns: minmax(0, 1.35fr) minmax(340px, 1fr);
		gap: 24px;
		align-items: start;
	}

	/* The recipe stays in view under the header and Path bar. */
	.recipe-col {
		position: sticky;
		top: calc(var(--header-height) + 76px);
		display: flex;
		flex-direction: column;
		gap: 8px;
		max-height: calc(100vh - var(--header-height) - 100px - var(--mini-h, 0px) - var(--tab-h, 0px));
		min-height: 0;
	}

	.recipe-col > :global(.recipe) {
		flex: 1;
	}

	.key {
		align-self: flex-start;
	}

	:global([data-narrow]) .columns {
		grid-template-columns: minmax(0, 1fr);
	}
	:global([data-narrow]) .recipe-col {
		position: static;
		max-height: none;
	}

	:global([data-bp='phone']) .hero {
		padding: 8vh 16px 40px;
	}
	:global([data-bp='phone']) .below,
	:global([data-bp='phone']) .columns {
		padding-left: 16px;
		padding-right: 16px;
	}
	:global([data-bp='phone']) .pathbar {
		padding: 10px 16px;
	}
	:global([data-bp='phone']) .big-cover {
		width: 160px;
		height: 160px;
	}
</style>
