<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import { access_token } from '../../stores.js';

	export let onSelect = () => {};

	let tracks = [];
	let loaded = false;
	let loading = false;

	$: if ($access_token && !loaded && !loading) fetchTopTracks();

	async function fetchTopTracks() {
		loading = true;
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/top-tracks/?access_token=${$access_token}&limit=12`);
			if (!res.ok) return;
			const data = await res.json();
			tracks = data.tracks ?? [];
			loaded = true;
		} catch {
			tracks = [];
		} finally {
			loading = false;
		}
	}
</script>

{#if tracks.length > 0}
	<div class="seeds">
		<div class="seeds-label">Or start from your top tracks</div>
		<div class="seeds-grid">
			{#each tracks as track (track.id)}
				<button class="seed" on:click={() => onSelect(track)} title={`${track.title} · ${track.artists.join(', ')}`}>
					{#if track.image}
						<img class="seed-img" src={track.image} alt="" />
					{:else}
						<div class="seed-img placeholder"></div>
					{/if}
					<div class="seed-text">
						<div class="seed-title">{track.title}</div>
						<div class="seed-artist">{track.artists.join(', ')}</div>
					</div>
				</button>
			{/each}
		</div>
	</div>
{/if}

<style>
	.seeds {
		width: 100%;
		max-width: 720px;
		margin: 40px auto 0;
	}

	.seeds-label {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text-subtle);
		text-align: center;
		margin-bottom: 16px;
	}

	.seeds-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 8px;
	}

	.seed {
		display: flex;
		align-items: center;
		gap: 10px;
		min-width: 0;
		padding: 8px 10px;
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		cursor: pointer;
		text-align: left;
		font-family: inherit;
		transition: border-color var(--transition), background-color var(--transition);
	}

	.seed:hover {
		border-color: var(--accent);
		background-color: var(--surface-2);
	}

	.seed-img {
		width: 40px;
		height: 40px;
		border-radius: var(--radius-sm);
		object-fit: cover;
		flex-shrink: 0;
		background-color: var(--surface-2);
	}

	.seed-text {
		min-width: 0;
	}

	.seed-title {
		font-size: 0.82rem;
		font-weight: 600;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.seed-artist {
		font-size: 0.74rem;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
</style>
