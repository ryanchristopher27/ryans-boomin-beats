<script>
	import { openSettings } from '$lib/settings.js';
	import { relayFetch } from '$lib/llmRelay.js';
	// The Explore song page's left column (R3): Tags, What the AI hears, Sound
	// profile and About. Picks go to exploreSession; the recipe column reads them.
	import { PUBLIC_API_URL } from '$env/static/public';
	import { exploreSession, llmConfig } from '../../stores.js';
	import { llmHeaders } from '../llmHeaders.js';
	import { spotifyHeaders } from '../spotifyHeaders.js';
	import Icon from './Icon.svelte';
	import { parseAnalysis } from '$lib/explore.js';

	const SCORE_ORDER = ['Energy', 'Danceability', 'Positivity', 'Acousticness', 'Intensity', 'Tempo'];

	export let song = null;

	let loading = false;

	$: songKey = song ? `${song.title}::${song.artists?.[0] ?? song.artist ?? ''}` : null;
	$: if (songKey) ensureProfile(songKey, song);

	$: profile = $exploreSession.profile;
	$: analysisFields = profile ? parseAnalysis(profile.analysis) : [];
	$: scores = profile?.scores ? SCORE_ORDER.filter((k) => k in profile.scores).map((k) => ({ label: k, value: Math.round(profile.scores[k] ?? 0) })) : [];
	$: selectedTags = new Set($exploreSession.selectedTags);
	$: selectedAspects = new Set($exploreSession.selectedAspects);

	async function ensureProfile(key, s, force = false) {
		// Already loaded this exact song: use the cache, do NOT re-query.
		if (!force && $exploreSession.key === key && $exploreSession.profile) return;
		loading = true;
		const keep = force ? $exploreSession : { selectedTags: [], selectedAspects: [] };
		$exploreSession = { key, profile: force ? $exploreSession.profile : null, selectedTags: keep.selectedTags, selectedAspects: keep.selectedAspects };
		try {
			const artist = s.artists?.[0] ?? s.artist ?? '';
			const params = new URLSearchParams({ title: s.title, artist });
			const res = await relayFetch(`${PUBLIC_API_URL}/song/profile/?${params}`, { headers: { ...spotifyHeaders(), ...llmHeaders() } });
			const data = await res.json();
			$exploreSession = { ...$exploreSession, key, profile: data };
		} catch {
			if (!force) $exploreSession = { key, profile: null, selectedTags: [], selectedAspects: [] };
		} finally {
			loading = false;
		}
	}

	function toggleTag(name) {
		const set = new Set($exploreSession.selectedTags);
		set.has(name) ? set.delete(name) : set.add(name);
		$exploreSession = { ...$exploreSession, selectedTags: Array.from(set) };
	}

	function toggleAspect(label) {
		const set = new Set($exploreSession.selectedAspects);
		set.has(label) ? set.delete(label) : set.add(label);
		$exploreSession = { ...$exploreSession, selectedAspects: Array.from(set) };
	}
</script>

{#if loading && !profile}
	<div class="col" aria-busy="true">
		{#each [3, 5, 4] as lines}
			<div class="card">
				<div class="skeleton bar" style:width="30%" />
				{#each Array(lines) as _, i}<div class="skeleton bar" style:width="{90 - i * 12}%" />{/each}
			</div>
		{/each}
	</div>
{:else if profile}
	<div class="col">
		{#if profile.tags?.length}
			<section class="card">
				<div class="card-head">
					<h2>Tags</h2>
					<span class="aside">From Last.fm. Tap to add to your recipe.</span>
				</div>
				<div class="chips">
					{#each profile.tags as tag}
						<button class="chip" class:selected={selectedTags.has(tag.name)} aria-pressed={selectedTags.has(tag.name)} on:click={() => toggleTag(tag.name)}>
							{#if selectedTags.has(tag.name)}<Icon name="check" size={12} />{/if}{tag.name}
						</button>
					{/each}
				</div>
			</section>
		{/if}

		<section class="card">
			<div class="card-head">
				<h2>What the AI hears</h2>
				{#if analysisFields.length}<span class="aside mono">Tap to add</span>{/if}
			</div>
			{#if analysisFields.length}
				<div class="aspects">
					{#each analysisFields as field}
						<button class="aspect" class:on={selectedAspects.has(field.label)} aria-pressed={selectedAspects.has(field.label)} on:click={() => toggleAspect(field.label)}>
							<span class="aspect-head">
								<span class="aspect-label">{field.label}</span>
								<span class="box">{#if selectedAspects.has(field.label)}<Icon name="check" size={11} />{/if}</span>
							</span>
							<span class="aspect-note">{field.value}</span>
						</button>
					{/each}
				</div>
			{:else if !$llmConfig.connected}
				<div class="missing">
					<p>Add an AI key to see a song analysis. Tags still work without one.</p>
					<button class="btn primary small" on:click={() => openSettings('ai')}>Add AI key</button>
				</div>
			{:else}
				<!-- Profiled before an AI was connected (the profile is cached per song). -->
				<div class="missing">
					<p>{loading ? 'Listening…' : 'No analysis for this song yet.'}</p>
					<button class="btn primary small" disabled={loading} on:click={() => ensureProfile(songKey, song, true)}>Get the analysis</button>
				</div>
			{/if}
		</section>

		{#if scores.length || profile.wiki_summary}
			<div class="pair">
				{#if scores.length}
					<section class="card">
						<h2>Sound profile</h2>
						{#each scores as s}
							<div class="score">
								<div class="score-head"><span>{s.label}</span><span class="mono">{s.value}</span></div>
								<div class="track" role="meter" aria-label={s.label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={s.value}><div class="fill" style:width="{s.value}%" /></div>
							</div>
						{/each}
					</section>
				{/if}
				{#if profile.wiki_summary}
					<section class="card">
						<h2>About</h2>
						<p class="about">{profile.wiki_summary}</p>
					</section>
				{/if}
			</div>
		{/if}
	</div>
{/if}

<style>
	.col {
		display: flex;
		flex-direction: column;
		gap: 20px;
		min-width: 0;
	}

	.card {
		display: flex;
		flex-direction: column;
		gap: 12px;
		padding: 20px;
		border-radius: 16px;
		background: var(--surface-1);
		border: 1px solid var(--border-subtle);
		min-width: 0;
	}

	.card-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 12px;
	}

	h2 {
		margin: 0;
		font-size: calc(16px * var(--text-scale, 1));
		font-weight: 600;
	}

	.aside {
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
		text-align: right;
	}

	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.chip {
		font-weight: 500;
	}

	.aspects {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 8px;
	}

	.aspect {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 12px 14px;
		border-radius: 11px;
		border: 1px solid rgba(255, 255, 255, 0.08);
		background: transparent;
		color: var(--text-primary);
		font: inherit;
		text-align: left;
		white-space: normal;
		cursor: pointer;
		transition: border-color var(--transition), background-color var(--transition);
	}

	.aspect:hover {
		border-color: rgba(255, 255, 255, 0.18);
	}

	.aspect.on {
		background: rgba(var(--accent-rgb), 0.08);
		border-color: var(--accent-tint-border);
	}

	.aspect-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}

	.aspect-label {
		font-size: calc(14px * var(--text-scale, 1));
		font-weight: 500;
	}

	.box {
		flex: none;
		width: 16px;
		height: 16px;
		display: grid;
		place-items: center;
		border-radius: 5px;
		border: 1.5px solid rgba(255, 255, 255, 0.25);
		color: var(--accent-on);
	}

	.on .box {
		border-color: var(--accent);
		background: var(--accent);
	}

	.aspect-note {
		font-size: calc(12px * var(--text-scale, 1));
		line-height: 1.4;
		color: rgba(243, 243, 245, 0.5);
	}

	.missing {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: 14px;
		border-radius: 11px;
		border: 1px dashed rgba(255, 255, 255, 0.12);
	}

	.missing p {
		margin: 0;
		font-size: calc(14px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.pair {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
		gap: 20px;
	}

	.score {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}

	.score-head {
		display: flex;
		justify-content: space-between;
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.track {
		height: 4px;
		border-radius: 4px;
		background: rgba(255, 255, 255, 0.07);
		overflow: hidden;
	}

	.fill {
		height: 100%;
		border-radius: 4px;
		background: var(--accent);
	}

	.about {
		margin: 0;
		font-size: calc(14px * var(--text-scale, 1));
		line-height: 1.6;
		color: rgba(243, 243, 245, 0.68);
		text-wrap: pretty;
	}

	.bar {
		height: 12px;
	}

	@media (max-width: 759px) {
		.aspects {
			grid-template-columns: 1fr;
		}
	}
</style>
