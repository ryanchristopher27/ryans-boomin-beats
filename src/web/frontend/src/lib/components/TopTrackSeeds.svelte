<script>
	// Explore's "Start from your top tracks" grid (R3): cover tiles with rank.
	import { PUBLIC_API_URL } from '$env/static/public';
	import { access_token } from '../../stores.js';
	import { spotifyHeaders } from '../spotifyHeaders.js';
	import { nameHue } from '$lib/dj/ambience.js';

	export let onSelect = (track) => {};
	/** The hovered or focused tile tints the hero. */
	export let onHover = (track) => {};

	let tracks = [];
	let loaded = false;
	let loading = false;

	$: if ($access_token && !loaded && !loading) fetchTopTracks();

	async function fetchTopTracks() {
		loading = true;
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/top-tracks/?limit=12`, { headers: spotifyHeaders() });
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

	const initials = (t) => t.title.split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
</script>

{#if $access_token}
	<section class="seeds" aria-labelledby="seeds-title">
		<div class="head">
			<h2 id="seeds-title">Start from your top tracks</h2>
			<a href="/profile/">See profile</a>
		</div>
		{#if loading && !tracks.length}
			<div class="grid" aria-busy="true">
				{#each Array(6) as _}<div class="tile"><div class="skel skeleton" /><div class="skeleton line" /></div>{/each}
			</div>
		{:else if loaded && !tracks.length}
			<p class="fresh">Your top tracks show up after a few days of listening on Spotify. Search for a song or pick a mood to start.</p>
		{:else}
			<div class="grid">
				{#each tracks as track, i (track.id)}
					<button
						class="tile"
						on:click={() => onSelect(track)}
						on:mouseenter={() => onHover(track)}
						on:focus={() => onHover(track)}
						aria-label="Explore {track.title} by {track.artists.join(', ')}"
					>
						<span class="cover" style:--h={nameHue(track.title)}>
							{#if track.image}<img src={track.image} alt="" loading="lazy" />{:else}<span class="mono initials">{initials(track)}</span>{/if}
							<span class="rank mono">{i + 1}</span>
						</span>
						<span class="title">{track.title}</span>
						<span class="artist">{track.artists.join(', ')}</span>
					</button>
				{/each}
			</div>
		{/if}
	</section>
{/if}

<style>
	.seeds {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
	}

	h2 {
		margin: 0;
		font-size: 20px;
		font-weight: 600;
		letter-spacing: -0.02em;
	}

	.head a {
		font-size: 13px;
		font-weight: 500;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
		gap: 22px 16px;
	}

	.tile {
		display: flex;
		flex-direction: column;
		gap: 4px;
		min-width: 0;
		padding: 0;
		border: none;
		background: none;
		color: var(--text-primary);
		font: inherit;
		text-align: left;
		white-space: normal;
		cursor: pointer;
	}

	.cover {
		position: relative;
		display: grid;
		place-items: center;
		width: 100%;
		aspect-ratio: 1;
		margin-bottom: 6px;
		overflow: hidden;
		border-radius: 12px;
		background: linear-gradient(140deg, oklch(0.66 0.12 var(--h)), oklch(0.32 0.08 calc(var(--h) + 45)));
		box-shadow: 0 14px 36px rgba(0, 0, 0, 0.35);
		transition: transform 0.2s var(--ease);
	}

	.tile:hover .cover,
	.tile:focus-visible .cover {
		transform: translateY(-3px);
	}

	.cover img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.initials {
		font-size: 28px;
		font-weight: 600;
		color: rgba(255, 255, 255, 0.82);
	}

	/* The rank sits on the art, over a soft shade so it reads on light covers. */
	.rank {
		position: absolute;
		left: 0;
		top: 0;
		padding: 8px 10px 14px 10px;
		background: radial-gradient(circle at 0 0, rgba(0, 0, 0, 0.45), transparent 70%);
		font-size: 12px;
		font-weight: 500;
		color: rgba(255, 255, 255, 0.85);
	}

	.title,
	.artist {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.title {
		font-size: 14px;
		font-weight: 500;
	}

	.artist {
		font-size: 12px;
		color: rgba(243, 243, 245, 0.55);
	}

	.fresh {
		margin: 0;
		padding: 20px;
		border-radius: 14px;
		border: 1px dashed rgba(255, 255, 255, 0.12);
		font-size: 14px;
		line-height: 1.5;
		color: rgba(243, 243, 245, 0.55);
	}

	.skel {
		aspect-ratio: 1;
		margin-bottom: 6px;
		border-radius: 12px;
	}

	.line {
		height: 12px;
		width: 70%;
	}
</style>
