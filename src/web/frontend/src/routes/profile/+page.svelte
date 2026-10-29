<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { PUBLIC_API_URL } from '$env/static/public';
	import { page, access_token, selectedSong, exploreTrail, discoveryPlaylist, builderRequest } from '../../stores.js';
	import { bearer } from '$lib/spotifyHeaders.js';
	import { beginLogin, logoutSpotify, hydrateToken, exchangeCodeForToken, saveTokens } from '$lib/spotifyAuth.js';
	import { getSavedStates, queueTracks, setTrackSaved } from '$lib/playlistActions.js';
	import { PERIOD_LABELS, insights, peakHour, summaryParts } from '$lib/profile.js';
	import { nameHue } from '$lib/dj/ambience.js';
	import { say } from '$lib/toast.js';
	import { onboarding } from '$lib/onboarding.js';
	import DashboardModule from '$lib/components/DashboardModule.svelte';
	import TrendChart from '$lib/components/TrendChart.svelte';
	import ColumnChart from '$lib/components/ColumnChart.svelte';
	import Heatmap from '$lib/components/Heatmap.svelte';
	import SongRow from '$lib/components/ui/SongRow.svelte';
	import Blobs from '$lib/components/ui/Blobs.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let token = $access_token;
	let user_profile = null;
	let top_artists = [];
	let top_tracks = [];
	let loading = false;
	let error = '';
	const NUM_TOPS = 50;
	const PERIODS = ['short_term', 'medium_term', 'long_term'];
	let time_period = 'short_term';

	/** @type {null | 'tracks' | 'artists' | 'genres' | 'eras' | 'taste' | 'clock'} */
	let expanded = null;
	const toggle = (id) => (expanded = expanded === id ? null : id);
	// Reactive, so the template's {#if shows(...)} re-runs when `expanded` changes.
	$: shows = (id) => !expanded || expanded === id;

	onMount(async () => {
		$page = 'Profile';
		// Returning from the Spotify OAuth redirect.
		const code = new URLSearchParams(window.location.search).get('code');
		if (code) {
			const verifier = sessionStorage.getItem('spotify_pkce_verifier');
			if (verifier) {
				const tokenData = await exchangeCodeForToken(code, verifier);
				if (tokenData.access_token) {
					saveTokens(tokenData);
					token = tokenData.access_token;
					$access_token = token;
				}
				sessionStorage.removeItem('spotify_pkce_verifier');
				window.history.replaceState({}, '', '/profile');
				getProfile();
			}
			return;
		}
		// Otherwise hydrate from a stored session (shared app-wide helper).
		if (await hydrateToken()) {
			token = $access_token;
			getProfile();
		}
	});

	async function getProfile() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`${PUBLIC_API_URL}/get-profile/?num_tops=${NUM_TOPS}&time_period=${time_period}`, { headers: bearer(token) });
			if (!res.ok) throw new Error(`profile ${res.status}`);
			const data = await res.json();
			user_profile = data.profile;
			top_artists = data.top_artists ?? [];
			top_tracks = data.top_tracks ?? [];
			fetchTasteOverTime();
			fetchRecentlyPlayed();
		} catch {
			error = "Couldn't load your profile. Try again in a moment.";
		} finally {
			loading = false;
		}
	}

	function setPeriod(p) {
		if (p === time_period) return;
		time_period = p;
		getProfile();
	}

	function logOut() {
		logoutSpotify();
		token = '';
		user_profile = null;
		$onboarding = 1;
	}

	// --- Taste over time ---
	let tasteData = null;
	let tasteLoaded = false;
	async function fetchTasteOverTime() {
		if (tasteLoaded || !token) return;
		tasteLoaded = true;
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/taste-over-time/`, { headers: bearer(token) });
			if (res.ok) tasteData = await res.json();
		} catch {
			/* the module just doesn't show */
		}
	}
	$: eraYears = (tasteData?.release_year || []).filter((y) => y > 0);
	$: eraMin = eraYears.length ? Math.min(...eraYears) - 2 : 2000;
	$: eraMax = eraYears.length ? Math.max(...eraYears) + 2 : 2025;
	$: audioSeries = tasteData?.audio_features ? Object.entries(tasteData.audio_features).map(([name, values]) => ({ name, values })) : [];

	// --- Listening clock (recently played → hour/day counts, local time) ---
	let recentData = null;
	let recentLoaded = false;
	let recentNeedsReauth = false;
	async function fetchRecentlyPlayed() {
		if (recentLoaded || !token) return;
		recentLoaded = true;
		try {
			const res = await fetch(`${PUBLIC_API_URL}/spotify/recently-played/`, { headers: bearer(token) });
			if (res.status === 403) recentNeedsReauth = true;
			else if (res.ok) recentData = await res.json();
		} catch {
			/* the module just doesn't show */
		}
	}
	const HOUR_TICKS = { 0: '12a', 6: '6a', 12: '12p', 18: '6p' };
	const DAY_ORDER = [1, 2, 3, 4, 5, 6, 0]; // Mon … Sun
	const DAY_INITIAL = { 0: 'S', 1: 'M', 2: 'T', 3: 'W', 4: 'T', 5: 'F', 6: 'S' };
	const DAY_NAME = { 0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat' };
	$: hourCounts = countBy(recentData, (d) => d.getHours(), 24);
	$: hourCells = hourCounts.map((value, h) => ({ value, label: `${h}:00`, tick: HOUR_TICKS[h] || '' }));
	$: dayCells = ((c) => DAY_ORDER.map((day) => ({ value: c[day], label: DAY_NAME[day], tick: DAY_INITIAL[day] })))(countBy(recentData, (d) => d.getDay(), 7));
	function countBy(d, key, n) {
		const counts = new Array(n).fill(0);
		(d?.played_at || []).forEach((ts) => counts[key(new Date(ts))]++);
		return counts;
	}

	function fmtDur(ms) {
		if (!ms) return '—';
		const s = Math.round(ms / 1000);
		return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
	}

	// --- Genres: rank-weighted aggregation of top artists' genres ---
	$: genreRanked = rankGenres(top_artists);
	$: genreTotal = genreRanked.reduce((s, g) => s + g.weight, 0);
	$: genreBars = genreRanked.slice(0, 8).map((g) => ({ label: g.genre, pct: Math.round((100 * g.weight) / (genreTotal || 1)), w: (100 * g.weight) / (genreRanked[0]?.weight || 1) }));
	$: genreDiversity = diversityIndex(genreRanked.map((g) => g.weight));
	function rankGenres(artists) {
		if (!artists?.length) return [];
		const weights = {};
		artists.forEach((a, i) => (a.genres || []).forEach((g) => (weights[g] = (weights[g] || 0) + artists.length - i))); // higher-ranked artists weigh more
		return Object.entries(weights).sort((a, b) => b[1] - a[1]).map(([genre, weight]) => ({ genre, weight }));
	}
	// Normalized Shannon entropy of genre weights → 0–100 ("focused" vs "varied").
	function diversityIndex(weights) {
		const total = weights.reduce((a, b) => a + b, 0);
		if (!total || weights.length < 2) return 0;
		const entropy = -weights.reduce((a, w) => a + (w / total) * Math.log(w / total), 0);
		return Math.round((100 * entropy) / Math.log(weights.length));
	}

	// --- Decades (from top tracks' release dates) ---
	$: decadeData = decadeBuckets(top_tracks);
	function decadeBuckets(tracks) {
		const counts = {};
		for (const t of tracks) {
			const y = parseInt((t.release_date || '').slice(0, 4), 10);
			if (y) counts[Math.floor(y / 10) * 10] = (counts[Math.floor(y / 10) * 10] || 0) + 1;
		}
		return Object.keys(counts).sort((a, b) => Number(a) - Number(b)).map((d) => ({ label: `${d}s`, value: counts[d] }));
	}

	// --- Summary and insights ---
	$: facts = { period: time_period, genres: genreRanked.map((g) => g.genre), decades: decadeData, peak: peakHour(hourCounts), topArtist: top_artists[0]?.name };
	$: summary = summaryParts(facts);
	$: cards = insights(facts);
	$: fresh = !!user_profile && !loading && !top_tracks.length && !top_artists.length;

	function act(card) {
		if (card.kind === 'build') {
			$builderRequest = card.prompt;
			goto('/playlist-builder/');
		} else goto(`/dj/?preset=${card.preset}`);
	}

	// --- Top tracks ---
	let saved = {};
	let savedKey = '';
	$: loadSaved(top_tracks.map((t) => t.id));
	async function loadSaved(ids) {
		const key = ids.join(',');
		if (!ids.length || key === savedKey) return;
		savedKey = key;
		saved = await getSavedStates(ids);
	}
	async function toggleSaved(id) {
		const next = !saved[id];
		saved = { ...saved, [id]: next };
		const r = await setTrackSaved(id, next);
		if (r.error) {
			saved = { ...saved, [id]: !next };
			say(r.error === 'reconnect' ? 'Reconnect Spotify to save songs: log out, then log in.' : "Couldn't update Liked Songs.");
		}
	}

	let queued = new Set();
	async function queue(id) {
		const r = await queueTracks([id]);
		if (r.ok) queued = new Set(queued).add(id);
		say(r.message);
	}

	function explore(t) {
		$selectedSong = { title: t.title, artists: t.artists, id: t.id, image: t.image };
		$exploreTrail = [$selectedSong];
		$discoveryPlaylist = [];
		goto('/');
	}

	$: avatar = user_profile?.images?.[0]?.url ?? '';
	$: initials = (user_profile?.display_name ?? '').split(/\s+/).slice(0, 2).map((w) => w[0] ?? '').join('').toUpperCase();
</script>

<svelte:head>
	<title>Profile · Boomin Beats</title>
	<meta name="description" content="Your listening, summarised" />
</svelte:head>

<div class="bleed">
	{#if !$access_token}
		<div class="signin">
			<Blobs hue={235} hero />
			<div class="signin-card glass">
				<h1>Your listening, at a glance.</h1>
				<p>Connect Spotify to see your top tracks, artists, genres and eras, and to build playlists from them.</p>
				<button class="btn primary big" on:click={beginLogin}>Connect Spotify</button>
			</div>
		</div>
	{:else}
		<Blobs hue={235} hero />
		<div class="content">
			<header class="who">
				{#if avatar}
					<img class="avatar" src={avatar} alt="" />
				{:else}
					<span class="avatar blank" style:--h={nameHue(user_profile?.display_name ?? '')}>{initials}</span>
				{/if}
				<div class="name">
					<h1>{user_profile?.display_name ?? (loading ? ' ' : 'Your profile')}</h1>
					{#if user_profile}<p class="mono">{user_profile.followers?.total ?? 0} followers · Spotify</p>{/if}
				</div>
				<div class="segmented periods" role="radiogroup" aria-label="Time period">
					{#each PERIODS as p}
						<button role="radio" aria-checked={time_period === p} class:active={time_period === p} on:click={() => setPeriod(p)}>{PERIOD_LABELS[p]}</button>
					{/each}
				</div>
				<button class="btn small" on:click={logOut}><Icon name="logout" size={14} /> Log out</button>
			</header>

			{#if error}
				<p class="error" role="alert">{error} <button class="link" on:click={getProfile}>Retry</button></p>
			{/if}

			{#if user_profile}
				<p class="summary">
					{#each summary as part}{#if part.strong}<strong>{part.text}</strong>{:else}{part.text}{/if}{/each}
				</p>
			{/if}

			{#if fresh}
				<div class="fresh glass">
					<h2>Nothing to show yet</h2>
					<p>Spotify shares top tracks and artists after a few days of listening. Until then, start from a song or let the DJ run tonight.</p>
					<div class="fresh-actions">
						<a class="btn primary" href="/">Explore a song</a>
						<a class="btn" href="/dj/">Start a DJ set</a>
					</div>
				</div>
			{:else if cards.length}
				<div class="insights">
					{#each cards as card, i}
						<button class="insight glass" style:animation-delay="{i * 60}ms" on:click={() => act(card)}>
							<span class="insight-label">{card.label}</span>
							<span class="insight-value">{card.value}</span>
							<span class="insight-action">{card.action} <span aria-hidden="true">→</span></span>
						</button>
					{/each}
				</div>
			{/if}

			{#if !fresh && (user_profile || loading)}
				<div class="grid" class:has-expanded={!!expanded} class:dim={loading}>
					{#if shows('tracks')}
						<div class="m tall" style:--span={expanded ? 12 : 5}>
							<DashboardModule title="Top tracks" expanded={expanded === 'tracks'} onToggleExpand={() => toggle('tracks')}>
								{#each top_tracks as t, i (t.id)}
									<SongRow
										compact
										index={i + 1}
										title={t.title}
										artists={t.artists}
										image={t.image}
										duration={t.duration_ms}
										dragId={t.id}
										onOpen={() => explore(t)}
										openLabel="Explore {t.title}"
										onAdd={() => queue(t.id)}
										added={queued.has(t.id)}
									>
										<button slot="actions" class="row-btn heart" class:on={saved[t.id]} on:click|stopPropagation={() => toggleSaved(t.id)} aria-pressed={!!saved[t.id]} aria-label={saved[t.id] ? `Remove ${t.title} from Liked Songs` : `Save ${t.title} to Liked Songs`}>
											<Icon name="heart" size={14} filled={saved[t.id]} />
										</button>
									</SongRow>
								{/each}
							</DashboardModule>
						</div>
					{/if}

					{#if shows('artists')}
						<div class="m tall" style:--span={expanded ? 12 : 4}>
							<DashboardModule title="Top artists" expanded={expanded === 'artists'} onToggleExpand={() => toggle('artists')}>
								<ol class="artists">
									{#each top_artists as a, i (a.name)}
										<li>
											<span class="rank mono">{i + 1}</span>
											{#if a.images?.[0]?.url}<img src={a.images[0].url} alt="" loading="lazy" />{:else}<span class="artist-blank" style:--h={nameHue(a.name)}>{a.name.slice(0, 1)}</span>{/if}
											<span class="artist-text">
												<span class="artist-name">{a.name}</span>
												<span class="artist-genres">{(a.genres || []).join(', ')}</span>
											</span>
										</li>
									{/each}
								</ol>
							</DashboardModule>
						</div>
					{/if}

					{#if shows('genres') && genreBars.length}
						<div class="m tall" style:--span={expanded ? 12 : 3}>
							<DashboardModule title="Top genres" expanded={expanded === 'genres'} onToggleExpand={() => toggle('genres')}>
								<div class="pad">
									<div class="diversity">
										<span class="div-word">{genreDiversity >= 66 ? 'Eclectic' : genreDiversity >= 33 ? 'Balanced' : 'Focused'}</span>
										<span class="div-sub">taste diversity · {genreDiversity}/100</span>
									</div>
									{#each genreBars as g, i}
										<div class="gbar">
											<div class="gbar-head"><span>{g.label}</span><span class="mono">{g.pct}%</span></div>
											<div class="gtrack"><div class="gfill" style:transform="scaleX({g.w / 100})" style:opacity={1 - i * 0.08} /></div>
										</div>
									{/each}
								</div>
							</DashboardModule>
						</div>
					{/if}

					{#if shows('eras') && decadeData.length}
						<div class="m short" style:--span={expanded ? 12 : 3}>
							<DashboardModule title="Eras" expanded={expanded === 'eras'} onToggleExpand={() => toggle('eras')}>
								<div class="pad chart"><ColumnChart items={decadeData} /></div>
							</DashboardModule>
						</div>
					{/if}

					{#if shows('taste') && tasteData}
						<div class="m short" style:--span={expanded ? 12 : 5}>
							<DashboardModule title="Taste over time" expanded={expanded === 'taste'} onToggleExpand={() => toggle('taste')}>
								<div class="pad">
									{#if audioSeries.length}
										<TrendChart labels={tasteData.timeframes} series={audioSeries} min={0} max={100} />
									{:else}
										<TrendChart labels={tasteData.timeframes} series={[{ name: 'Release year', values: tasteData.release_year }]} min={eraMin} max={eraMax} />
									{/if}
									<dl class="stats">
										{#each tasteData.timeframes as tf, i}
											<div><dt>{tf}</dt><dd class="mono">{fmtDur(tasteData.avg_duration_ms[i])} · {tasteData.explicit_pct[i]}% explicit</dd></div>
										{/each}
									</dl>
								</div>
							</DashboardModule>
						</div>
					{/if}

					{#if shows('clock') && (recentData?.count > 0 || recentNeedsReauth)}
						<div class="m short" style:--span={expanded ? 12 : 4}>
							<DashboardModule title="Listening clock" expanded={expanded === 'clock'} onToggleExpand={() => toggle('clock')}>
								<div class="pad clock">
									{#if recentNeedsReauth}
										<p class="note">Reconnect Spotify (log out, then log in) to see your listening history.</p>
									{:else}
										<p class="clock-label mono">BY HOUR</p>
										<Heatmap cells={hourCells} />
										<p class="clock-label mono">BY DAY</p>
										<Heatmap cells={dayCells} />
										<p class="note">Based on your last {recentData.count} plays (Spotify's limit).</p>
									{/if}
								</div>
							</DashboardModule>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.bleed {
		position: relative;
		margin: calc(var(--primary-spacing) * -1) calc(var(--primary-spacing) * -1) 0;
		min-height: calc(100vh - var(--header-height));
		overflow-x: hidden;
	}

	.content {
		position: relative;
		z-index: 1;
		max-width: 1320px;
		margin: 0 auto;
		padding: 40px 28px 48px;
		display: flex;
		flex-direction: column;
		gap: 24px;
	}

	/* --- Signed out --- */
	.signin {
		position: relative;
		display: grid;
		place-items: center;
		min-height: calc(100vh - var(--header-height));
		padding: 16px;
	}

	.signin-card {
		position: relative;
		z-index: 1;
		max-width: 520px;
		padding: 32px;
		border-radius: 20px;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 14px;
	}

	.signin-card h1 {
		margin: 0;
		font-size: calc(36px * var(--text-scale, 1));
		font-weight: 700;
		letter-spacing: -0.035em;
		line-height: 1.05;
	}

	.signin-card p {
		margin: 0;
		font-size: calc(15px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.big {
		height: 46px;
		padding: 0 20px;
		border-radius: 11px;
		font-size: calc(14px * var(--text-scale, 1));
	}

	/* --- Header --- */
	.who {
		display: flex;
		align-items: center;
		gap: 20px;
		flex-wrap: wrap;
	}

	.avatar {
		flex: none;
		width: 88px;
		height: 88px;
		border-radius: 50%;
		object-fit: cover;
		box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4);
	}

	.avatar.blank {
		display: grid;
		place-items: center;
		background: linear-gradient(140deg, oklch(0.62 0.1 var(--h)), oklch(0.32 0.08 calc(var(--h) + 50)));
		font-size: calc(22px * var(--text-scale, 1));
		font-weight: 600;
	}

	.name {
		flex: 1;
		min-width: 240px;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	h1 {
		margin: 0;
		font-size: calc(clamp(32px, 5vw, 56px) * var(--text-scale, 1));
		font-weight: 700;
		line-height: 1;
		letter-spacing: -0.04em;
	}

	.name p {
		margin: 0;
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.periods button {
		height: 32px;
		padding: 0 14px;
	}

	.error {
		margin: 0;
		color: var(--danger-text);
		font-size: calc(14px * var(--text-scale, 1));
	}

	.link {
		padding: 0;
		border: none;
		background: none;
		color: var(--accent);
		font: inherit;
		cursor: pointer;
	}

	.summary {
		margin: 0;
		max-width: 880px;
		font-size: calc(22px * var(--text-scale, 1));
		font-weight: 500;
		line-height: 1.45;
		letter-spacing: -0.015em;
		color: rgba(243, 243, 245, 0.55);
		text-wrap: pretty;
	}

	.summary strong {
		font-weight: 500;
		color: var(--text-primary);
	}

	/* --- Insights --- */
	.insights {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
		gap: 12px;
	}

	.insight {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 16px;
		border-radius: 16px;
		color: var(--text-primary);
		font: inherit;
		text-align: left;
		white-space: normal;
		cursor: pointer;
		transition: border-color 0.15s, transform 0.2s var(--ease);
		animation: bbin 0.4s var(--ease) both;
	}

	.insight:hover {
		border-color: rgba(var(--accent-rgb), 0.4);
		transform: translateY(-2px);
	}

	.insight-label {
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		color: rgba(243, 243, 245, 0.5);
	}

	.insight-value {
		font-size: calc(20px * var(--text-scale, 1));
		font-weight: 600;
		line-height: 1.2;
		letter-spacing: -0.02em;
		text-wrap: balance;
	}

	.insight-action {
		font-size: calc(13px * var(--text-scale, 1));
		font-weight: 500;
		color: var(--accent);
	}

	.fresh {
		max-width: 620px;
		padding: 28px;
		border-radius: 16px;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 14px;
	}

	.fresh h2 {
		margin: 0;
		font-size: calc(18px * var(--text-scale, 1));
		font-weight: 600;
	}

	.fresh p {
		margin: 0;
		font-size: calc(14px * var(--text-scale, 1));
		line-height: 1.55;
		color: var(--text-muted);
	}

	.fresh-actions {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
	}

	/* --- Module grid: 12 columns; expand makes one module the whole row --- */
	.grid {
		display: grid;
		grid-template-columns: repeat(12, minmax(0, 1fr));
		gap: 16px;
		transition: opacity 0.2s var(--ease);
	}

	.grid.dim {
		opacity: 0.5;
	}

	.m {
		grid-column: span var(--span);
		min-width: 0;
	}

	.m.tall {
		height: 520px;
	}

	.m.short {
		height: 300px;
	}

	.has-expanded .m {
		height: calc(100vh - var(--header-height) - var(--mini-h, 0px) - var(--tab-h, 0px) - 120px);
		min-height: 420px;
	}

	.heart.on {
		color: var(--accent);
	}

	.artists {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.artists li {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px 10px;
		border-radius: 10px;
	}

	.artists li:hover {
		background: rgba(255, 255, 255, 0.045);
	}

	.rank {
		flex: none;
		width: 20px;
		text-align: right;
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		color: var(--text-subtle);
	}

	.artists img,
	.artist-blank {
		flex: none;
		width: 40px;
		height: 40px;
		border-radius: 50%;
		object-fit: cover;
	}

	.artist-blank {
		display: grid;
		place-items: center;
		background: linear-gradient(140deg, oklch(0.66 0.12 var(--h)), oklch(0.32 0.08 calc(var(--h) + 45)));
		font-size: calc(13px * var(--text-scale, 1));
		font-weight: 600;
	}

	.artist-text {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}

	.artist-name {
		font-size: calc(14px * var(--text-scale, 1));
		font-weight: 500;
	}

	.artist-genres {
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.pad {
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 14px;
	}

	.diversity {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.div-word {
		font-size: calc(30px * var(--text-scale, 1));
		font-weight: 700;
		letter-spacing: -0.03em;
	}

	.div-sub {
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.gbar {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}

	.gbar-head {
		display: flex;
		justify-content: space-between;
		gap: 8px;
		font-size: calc(13px * var(--text-scale, 1));
	}

	.gbar-head .mono {
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.gtrack {
		height: 6px;
		border-radius: 6px;
		background: rgba(255, 255, 255, 0.06);
	}

	.gfill {
		height: 100%;
		border-radius: 6px;
		background: var(--accent);
		transform-origin: left;
		transition: transform 0.25s var(--ease);
	}

	.stats {
		display: flex;
		flex-direction: column;
		gap: 6px;
		margin: 0;
	}

	.stats div {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		font-size: calc(12px * var(--text-scale, 1));
	}

	.stats dt {
		color: var(--text-muted);
	}

	.stats dd {
		margin: 0;
		color: rgba(243, 243, 245, 0.65);
	}

	.clock-label {
		margin: 0;
		font-size: calc(11px * var(--text-scale, 1));
		letter-spacing: 0.04em;
		color: var(--text-subtle);
	}

	.note {
		margin: 0;
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	:global([data-narrow]) .m {
		grid-column: span 6;
	}
	:global([data-narrow]) .has-expanded .m {
		grid-column: span 12;
	}

	:global([data-bp='phone']) .content {
		padding: 20px 16px 40px;
	}
	:global([data-bp='phone']) .m {
		grid-column: span 12;
	}
	:global([data-bp='phone']) .summary {
		font-size: calc(18px * var(--text-scale, 1));
	}
</style>
