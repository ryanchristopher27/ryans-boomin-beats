<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import TagPill from './TagPill.svelte';

	export let song = null;
	export let onDiscover = (tags) => {};

	let profile = null;
	let loading = false;
	let selectedTags = new Set();

	$: if (song) loadProfile(song);

	async function loadProfile(s) {
		loading = true;
		profile = null;
		selectedTags = new Set();
		try {
			const artist = s.artists?.[0] ?? s.artist ?? '';
			const params = new URLSearchParams({ title: s.title, artist });
			const res = await fetch(`${PUBLIC_API_URL}/song/profile/?${params}`, { credentials: 'include' });
			profile = await res.json();
		} catch {
			profile = null;
		} finally {
			loading = false;
		}
	}

	function toggleTag(tagName, isSelected) {
		const next = new Set(selectedTags);
		isSelected ? next.add(tagName) : next.delete(tagName);
		selectedTags = next;
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
				<div class="section-label">Select aspects to explore</div>
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

		{#if profile.analysis}
			<div class="section">
				<div class="section-label">Analysis</div>
				{#each parseAnalysis(profile.analysis) as field}
					<div class="analysis-field">
						<span class="field-label">{field.label}</span>
						<span class="field-value">{field.value}</span>
					</div>
				{/each}
			</div>
		{:else}
			<div class="no-llm">Connect an AI account via ⚙ to see a song analysis.</div>
		{/if}

		<button
			class="discover-btn"
			on:click={() => onDiscover(Array.from(selectedTags))}
			disabled={selectedTags.size === 0}
		>
			Discover Similar Songs
			{#if selectedTags.size > 0}
				· {selectedTags.size} aspect{selectedTags.size > 1 ? 's' : ''} selected
			{/if}
		</button>
	</div>
{/if}

<style>
	.profile-container {
		background-color: var(--color-dark-gray);
		border-radius: 20px;
		padding: 24px;
		margin-top: 20px;
	}

	.loading {
		text-align: center;
		color: rgba(94, 201, 255, 0.4);
		padding: 40px;
		font-size: 0.85rem;
	}

	.profile-header {
		margin-bottom: 24px;
	}

	.song-title {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--color-light-blue);
	}

	.song-artist {
		font-size: 1rem;
		color: rgba(94, 201, 255, 0.7);
		margin-top: 4px;
	}

	.listeners {
		font-size: 0.75rem;
		color: rgba(255, 255, 255, 0.35);
		margin-top: 6px;
	}

	.section {
		margin-bottom: 24px;
	}

	.section-label {
		font-size: 0.68rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		font-weight: 700;
		color: rgba(94, 201, 255, 0.45);
		margin-bottom: 10px;
	}

	.tag-pills {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.analysis-field {
		display: flex;
		gap: 12px;
		margin-bottom: 10px;
		font-size: 0.85rem;
		line-height: 1.5;
	}

	.field-label {
		color: var(--color-light-blue);
		font-weight: 700;
		min-width: 150px;
		flex-shrink: 0;
	}

	.field-value {
		color: rgba(255, 255, 255, 0.8);
	}

	.no-llm {
		font-size: 0.8rem;
		color: rgba(94, 201, 255, 0.35);
		font-style: italic;
		margin-bottom: 20px;
	}

	.discover-btn {
		width: 100%;
		height: 42px;
		background-color: var(--color-light-blue);
		color: var(--color-dark-gray);
		border: 2px solid var(--color-light-blue);
		border-radius: 10px;
		font-weight: 700;
		font-size: 0.85rem;
		cursor: pointer;
	}

	.discover-btn:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.discover-btn:hover:not(:disabled) {
		border-color: var(--color-purple);
	}
</style>
