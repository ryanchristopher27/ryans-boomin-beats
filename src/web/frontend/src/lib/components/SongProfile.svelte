<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import TagPill from './TagPill.svelte';
	import { exploreSession } from '../../stores.js';

	export let song = null;
	export let onDiscover = (selection) => {};

	let loading = false;

	$: songKey = song ? `${song.title}::${song.artists?.[0] ?? song.artist ?? ''}` : null;
	$: if (songKey) ensureProfile(songKey, song);

	$: profile = $exploreSession.profile;
	$: analysisFields = profile ? parseAnalysis(profile.analysis) : [];
	$: selectedTags = new Set($exploreSession.selectedTags);
	$: selectedAspects = new Set($exploreSession.selectedAspects);
	$: totalSelected = selectedTags.size + selectedAspects.size;

	async function ensureProfile(key, s) {
		// Already loaded this exact song — use the cache, do NOT re-query.
		if ($exploreSession.key === key && $exploreSession.profile) return;
		loading = true;
		$exploreSession = { key, profile: null, selectedTags: [], selectedAspects: [] };
		try {
			const artist = s.artists?.[0] ?? s.artist ?? '';
			const params = new URLSearchParams({ title: s.title, artist });
			const res = await fetch(`${PUBLIC_API_URL}/song/profile/?${params}`, { credentials: 'include' });
			const data = await res.json();
			$exploreSession = { key, profile: data, selectedTags: [], selectedAspects: [] };
		} catch {
			$exploreSession = { key, profile: null, selectedTags: [], selectedAspects: [] };
		} finally {
			loading = false;
		}
	}

	function toggleTag(tagName, isSelected) {
		const set = new Set($exploreSession.selectedTags);
		isSelected ? set.add(tagName) : set.delete(tagName);
		$exploreSession = { ...$exploreSession, selectedTags: Array.from(set) };
	}

	function toggleAspect(label) {
		const set = new Set($exploreSession.selectedAspects);
		set.has(label) ? set.delete(label) : set.add(label);
		$exploreSession = { ...$exploreSession, selectedAspects: Array.from(set) };
	}

	function handleDiscover() {
		onDiscover({
			tags: [...$exploreSession.selectedTags],
			aspects: analysisFields.filter(f => $exploreSession.selectedAspects.includes(f.label)),
		});
	}

	function parseAnalysis(raw) {
		if (!raw) return [];
		return raw
			.split('\n')
			.map(line => line.trim())
			.filter(line => line.includes(':'))
			.map(line => {
				const i = line.indexOf(':');
				return { label: line.slice(0, i).trim(), value: line.slice(i + 1).trim() };
			})
			.filter(f => f.label && f.value);
	}
</script>

{#if loading}
	<div class="profile-container">
		<div class="loading">Loading profile...</div>
	</div>
{:else if profile}
	<div class="profile-container">
		<div class="profile-header">
			<div class="song-title">{profile.title}</div>
			<div class="song-artist">{profile.artist}</div>
			{#if profile.listeners > 0}
				<div class="listeners">{profile.listeners.toLocaleString()} listeners on Last.fm</div>
			{/if}
		</div>

		{#if profile.tags.length > 0}
			<div class="section">
				<div class="section-label">Tags · tap to select</div>
				<div class="tag-pills">
					{#each profile.tags as tag}
						<TagPill
							tag={tag.name}
							selected={selectedTags.has(tag.name)}
							onToggle={toggleTag}
						/>
					{/each}
				</div>
			</div>
		{/if}

		{#if analysisFields.length > 0}
			<div class="section">
				<div class="section-label">Analysis · tap an aspect to select</div>
				{#each analysisFields as field}
					<button
						type="button"
						class="analysis-field"
						class:selected={selectedAspects.has(field.label)}
						on:click={() => toggleAspect(field.label)}
					>
						<span class="field-label">{field.label}</span>
						<span class="field-value">{field.value}</span>
					</button>
				{/each}
			</div>
		{:else}
			<div class="no-llm">Connect an AI account via ⚙ to see a song analysis and discover similar songs.</div>
		{/if}

		<button
			class="discover-btn"
			on:click={handleDiscover}
			disabled={totalSelected === 0}
		>
			Discover Similar Songs
			{#if totalSelected > 0}
				· {totalSelected} selected
			{/if}
		</button>
		{#if totalSelected === 0 && (profile.tags.length > 0 || analysisFields.length > 0)}
			<div class="discover-hint">Select one or more tags or aspects above to discover similar songs.</div>
		{/if}
	</div>
{/if}

<style>
	.profile-container {
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-lg);
		padding: 28px;
		margin-top: 20px;
		animation: fadeIn 0.3s ease;
	}

	.loading {
		text-align: center;
		color: var(--text-subtle);
		padding: 40px;
		font-size: 0.85rem;
	}

	.profile-header {
		margin-bottom: 28px;
	}

	.song-title {
		font-size: 1.6rem;
		font-weight: 700;
		color: var(--text-primary);
		letter-spacing: -0.01em;
	}

	.song-artist {
		font-size: 1rem;
		color: var(--text-muted);
		margin-top: 4px;
	}

	.listeners {
		font-size: 0.75rem;
		color: var(--text-subtle);
		margin-top: 8px;
	}

	.section {
		margin-bottom: 28px;
	}

	.section-label {
		font-size: 0.68rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		font-weight: 700;
		color: var(--text-subtle);
		margin-bottom: 12px;
	}

	.tag-pills {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.analysis-field {
		display: flex;
		gap: 12px;
		width: 100%;
		margin-bottom: 8px;
		padding: 10px 12px;
		font-size: 0.85rem;
		line-height: 1.55;
		text-align: left;
		background-color: var(--surface-0);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: border-color var(--transition), background-color var(--transition);
		font-family: inherit;
	}

	.analysis-field:hover {
		border-color: var(--accent);
	}

	.analysis-field.selected {
		border-color: var(--accent);
		background-color: rgba(var(--accent-rgb), 0.1);
	}

	.field-label {
		color: var(--accent);
		font-weight: 600;
		min-width: 150px;
		flex-shrink: 0;
	}

	.field-value {
		color: var(--text-muted);
	}

	.discover-hint {
		text-align: center;
		color: var(--text-subtle);
		font-size: 0.75rem;
		margin-top: 10px;
	}

	.no-llm {
		font-size: 0.8rem;
		color: var(--text-subtle);
		font-style: italic;
		margin-bottom: 20px;
	}

	.discover-btn {
		width: 100%;
		height: 46px;
		background: var(--brand-gradient);
		color: var(--surface-0);
		border: none;
		border-radius: var(--radius);
		font-weight: 700;
		font-size: 0.85rem;
		cursor: pointer;
		transition: opacity var(--transition), filter var(--transition);
	}

	.discover-btn:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.discover-btn:hover:not(:disabled) {
		filter: brightness(1.1);
	}
</style>
