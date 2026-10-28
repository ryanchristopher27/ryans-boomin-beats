<script>
	// The Song profile widget (W4). Linked: it follows the selected song, which
	// is the one playing until a suggestion or queue row is clicked. Uses the
	// same /song/profile/ endpoint and radar as Explore, with widget markup.
	import SongRadar from '../SongRadar.svelte';
	import { djContext } from './context.js';

	/** @type {any} */
	export let dj;
	const { player } = dj;
	const { selected } = djContext();

	const SCORE_ORDER = ['Energy', 'Danceability', 'Positivity', 'Acousticness', 'Intensity', 'Tempo'];
	/** One fetch per song per visit; the profile includes an LLM call. */
	const cache = new Map();

	$: playing = $player.state?.track ?? null;
	$: song = $selected ?? playing;
	$: key = song ? `${song.title}::${song.artists?.[0] ?? ''}` : '';
	// Keyed on the song, not the object: the player poll hands over a new track
	// object every few seconds, which would restart the load each time (review W1).
	let requested = '';
	$: if (key !== requested) {
		requested = key;
		load(key, song);
	}

	/** @type {{status: string, profile: any}} */
	let state = { status: 'idle', profile: null };

	async function load(k, s) {
		if (!k) return (state = { status: 'idle', profile: null });
		if (cache.has(k)) return (state = { status: 'loaded', profile: cache.get(k) });
		state = { status: 'loading', profile: null };
		const params = new URLSearchParams({ title: s.title, artist: s.artists?.[0] ?? '' });
		try {
			const r = await dj.request('GET', `song/profile/?${params}`);
			if (k !== key) return; // the selection moved on
			if (r.status !== 200) return (state = { status: 'failed', profile: null });
			if (cache.size > 30) cache.clear();
			cache.set(k, r.data);
			state = { status: 'loaded', profile: r.data };
		} catch {
			if (k === key) state = { status: 'failed', profile: null };
		}
	}

	const parse = (raw) =>
		(raw ?? '')
			.split('\n')
			.map((l) => l.trim())
			.filter((l) => l.includes(':'))
			.map((l) => ({ label: l.slice(0, l.indexOf(':')).trim(), value: l.slice(l.indexOf(':') + 1).trim() }))
			.filter((f) => f.label && f.value);

	$: p = state.profile;
	$: fields = p ? parse(p.analysis) : [];
	$: axes = p?.scores ? SCORE_ORDER.map((k) => ({ label: k, value: p.scores[k] ?? 0 })) : [];
	$: rateLimited = /rate.?limit|429/i.test(p?.analysis_error ?? '');
	$: following = !$selected || $selected.id === playing?.id;
</script>

<div class="profile">
	{#if !song}
		<p class="empty">Play a song, or click a suggestion or a queued song, to see its profile.</p>
	{:else}
		<div class="head">
			<img src={song.image} alt="" width="56" height="56" />
			<div class="text">
				<p class="title">{song.title}</p>
				<p class="artist">{song.artists?.join(', ')}</p>
				<p class="source">{following ? 'Now playing' : 'Selected'}</p>
			</div>
			{#if !following}
				<button class="btn small" on:click={() => selected.set(null)}>Show now playing</button>
			{/if}
		</div>

		{#if state.status === 'loading'}
			<div class="sk" style="height: 24px; width: 70%" />
			<div class="sk" style="height: 120px" />
		{:else if state.status === 'failed'}
			<p class="empty">Couldn't load this song's profile. <button class="link" on:click={() => load(key, song)}>Try again</button></p>
		{:else if p}
			{#if p.tags?.length}
				<ul class="tags" aria-label="Last.fm tags">
					{#each p.tags.slice(0, 8) as t}<li>{t.name}</li>{/each}
				</ul>
			{/if}
			{#if axes.length}
				<div class="radar"><SongRadar {axes} max={100} ariaLabel="Sound profile of {song.title}" /></div>
			{/if}
			{#if fields.length}
				<dl>
					{#each fields as f}
						<dt>{f.label}</dt>
						<dd>{f.value}</dd>
					{/each}
				</dl>
			{:else if p.analysis_error}
				<p class="note" title={p.analysis_error}>
					{rateLimited ? 'Your AI provider is rate-limiting right now, so there is no analysis yet.' : "The AI analysis didn't come through this time."}
				</p>
			{:else}
				<p class="note">Connect an AI account in AI settings to add an analysis.</p>
			{/if}
			{#if p.wiki_summary}
				<p class="about" title={p.wiki_summary}>{p.wiki_summary}</p>
			{/if}
		{/if}
	{/if}
</div>

<style>
	.profile {
		padding: 14px 16px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.head {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	img {
		border-radius: 6px;
		object-fit: cover;
		background: var(--surface-2);
		flex: none;
	}

	.text {
		flex: 1;
		min-width: 0;
	}

	p {
		margin: 0;
	}

	.title {
		font-size: calc(16px * var(--text-scale, 1));
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.artist,
	.source {
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.source {
		font-size: calc(12px * var(--text-scale, 1));
	}

	.tags {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.tags li {
		font-size: calc(12px * var(--text-scale, 1));
		padding: 3px 9px;
		border-radius: 999px;
		background: var(--surface-2);
		color: var(--text-muted);
	}

	.radar {
		max-width: 260px;
		align-self: center;
		width: 100%;
	}

	dl {
		margin: 0;
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 6px 12px;
		font-size: calc(13px * var(--text-scale, 1));
		line-height: 1.45;
	}

	dt {
		color: var(--text-muted);
	}

	dd {
		margin: 0;
	}

	.about {
		font-size: calc(13px * var(--text-scale, 1));
		line-height: 1.5;
		color: var(--text-muted);
		display: -webkit-box;
		-webkit-line-clamp: 4;
		line-clamp: 4;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.empty,
	.note {
		font-size: calc(13px * var(--text-scale, 1));
		line-height: 1.5;
		color: var(--text-muted);
	}

	.link {
		background: none;
		border: none;
		padding: 0;
		color: var(--accent);
		font: inherit;
		cursor: pointer;
	}

	.sk {
		background: var(--surface-2);
		border-radius: 6px;
	}
</style>
