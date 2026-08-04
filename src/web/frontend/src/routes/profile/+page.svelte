<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { PUBLIC_API_URL } from '$env/static/public';
    import BoominBeatsLogo from '$lib/images/BoominBeatsLogo.jpg';
    import SongCard from '$lib/components/SongCard.svelte';
    import SongRadar from '$lib/components/SongRadar.svelte';
    import DashboardModule from '$lib/components/DashboardModule.svelte';
    import TrendChart from '$lib/components/TrendChart.svelte';
    import BarChart from '$lib/components/BarChart.svelte';
    import ColumnChart from '$lib/components/ColumnChart.svelte';
    import Heatmap from '$lib/components/Heatmap.svelte';

    let expandedModule = null; // 'genres' | 'taste' | 'tracks' | 'artists' | null
    const toggleModule = (id) => { expandedModule = expandedModule === id ? null : id; };

    let tasteData = null;
    let tasteLoaded = false;
    async function fetchTasteOverTime() {
        if (tasteLoaded || !token) return;
        tasteLoaded = true;
        try {
            const res = await fetch(`${PUBLIC_API_URL}/spotify/taste-over-time/?access_token=${token}`);
            if (res.ok) tasteData = await res.json();
        } catch { /* ignore */ }
    }

    // Listening clock (recently-played → hour/day histograms, local time)
    let recentData = null;
    let recentLoaded = false;
    let recentNeedsReauth = false;
    async function fetchRecentlyPlayed() {
        if (recentLoaded || !token) return;
        recentLoaded = true;
        try {
            const res = await fetch(`${PUBLIC_API_URL}/spotify/recently-played/?access_token=${token}`);
            if (res.status === 403) { recentNeedsReauth = true; return; }
            if (res.ok) recentData = await res.json();
        } catch { /* ignore */ }
    }

    const HOUR_TICKS = { 0: '12a', 6: '6a', 12: '12p', 18: '6p' };
    const DAY_ORDER = [1, 2, 3, 4, 5, 6, 0]; // Mon … Sun
    const DAY_INITIAL = { 0: 'S', 1: 'M', 2: 'T', 3: 'W', 4: 'T', 5: 'F', 6: 'S' };
    const DAY_NAME = { 0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat' };

    $: hourCells = buildHourCells(recentData);
    $: dayCells = buildDayCells(recentData);
    function buildHourCells(d) {
        const counts = new Array(24).fill(0);
        (d?.played_at || []).forEach((ts) => { counts[new Date(ts).getHours()]++; });
        return counts.map((v, h) => ({ value: v, label: `${h}:00`, tick: HOUR_TICKS[h] || '' }));
    }
    function buildDayCells(d) {
        const counts = new Array(7).fill(0);
        (d?.played_at || []).forEach((ts) => { counts[new Date(ts).getDay()]++; });
        return DAY_ORDER.map((day) => ({ value: counts[day], label: DAY_NAME[day], tick: DAY_INITIAL[day] }));
    }

    $: eraYears = (tasteData?.release_year || []).filter((y) => y > 0);
    $: eraMin = eraYears.length ? Math.min(...eraYears) - 2 : 2000;
    $: eraMax = eraYears.length ? Math.max(...eraYears) + 2 : 2025;
    $: audioSeries = tasteData?.audio_features
        ? Object.entries(tasteData.audio_features).map(([name, values]) => ({ name, values }))
        : [];

    function fmtDur(ms) {
        if (!ms) return '—';
        const m = Math.floor(ms / 60000);
        const s = Math.round((ms % 60000) / 1000);
        return `${m}:${s < 10 ? '0' : ''}${s}`;
    }

    import { page, user, access_token, selectedSong } from '../../stores.js'
    import { beginLogin, logoutSpotify, hydrateToken, exchangeCodeForToken, saveTokens } from '$lib/spotifyAuth.js';
    import { getSavedStates, setTrackSaved } from '$lib/playlistActions.js';

    let savedMap = {};
    let savedKey = '';

    let token = $access_token;

    let user_profile = {};
    let top_artists = [];
    let top_tracks = [];

    let number_of_tops = 50;

    let possible_time_periods = ['short_term', 'medium_term', 'long_term'];
    let time_period = 'short_term';
    let time_period_object = {'short_term': '1 Month', 'medium_term': '6 Months', 'long_term': 'All Time'}

    let logged_in = false;

    function handleLogout() {
        logoutSpotify();
        token = '';
        logged_in = false;
    }

    onMount(async () => {
        $page = 'Profile';

        // Returning from the Spotify OAuth redirect.
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
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
        const ok = await hydrateToken();
        if (ok) {
            token = $access_token;
            getProfile();
        }
    });

    const handleLogin = () => beginLogin();

    async function getProfile() {
        console.log('Get Profile Test 1')
        try {
            console.log('Get Profile Test In Try')
			// let url = `${PUBLIC_API_URL}/account-analysis/?access_token=${access_token}`
			let url = `${PUBLIC_API_URL}/get-profile/?access_token=${token}&num_tops=${number_of_tops}&time_period=${time_period}`

            console.log('Fetching User Profile')
			const response = await fetch(url, {
                method: 'GET',
                mode: 'cors',
            })

			if (!response.ok) {
				throw new Error('Network response was not ok.');
			}

			const jsonResponse = await response.json();
			user_profile = jsonResponse.profile;
            top_artists = jsonResponse.top_artists;
            top_tracks = jsonResponse.top_tracks;
            console.log(user_profile);
            console.log(top_artists);
            console.log(top_tracks);
            logged_in = true;
            fetchTasteOverTime();
            fetchRecentlyPlayed();
            // $logged_in = true;

		} catch (error) {
			// Handle any errors that occurred during the fetch request.
			console.error('Error fetching data:', error);
		}
    }

    let setTimePeriod = (time) => {
        time_period = time;
        getProfile()
	}

    // --- Genres: rank-weighted aggregation of top artists' genres ---
    $: genreRanked = rankGenres(top_artists);                                  // full sorted [{genre, weight}]
    $: genreAxes = genreRanked.slice(0, 6).map((g) => ({ label: trunc(g.genre, 16), value: g.weight }));
    $: genreBars = genreRanked.slice(0, 8).map((g) => ({ label: g.genre, value: g.weight }));
    $: genreDiversity = diversityIndex(genreRanked.map((g) => g.weight));

    function rankGenres(artists) {
        if (!artists || !artists.length) return [];
        const weights = {};
        const N = artists.length;
        artists.forEach((a, i) => {
            const w = N - i; // earlier (higher-ranked) artists weigh more
            (a.genres || []).forEach((g) => { weights[g] = (weights[g] || 0) + w; });
        });
        return Object.entries(weights).sort((a, b) => b[1] - a[1]).map(([genre, weight]) => ({ genre, weight }));
    }
    function trunc(s, n) { return s.length > n ? s.slice(0, n - 1) + '…' : s; }
    // Normalized Shannon entropy of genre weights → 0–100 ("focused" vs "varied").
    function diversityIndex(weights) {
        const total = weights.reduce((a, b) => a + b, 0);
        if (!total || weights.length < 2) return 0;
        const probs = weights.map((w) => w / total);
        const entropy = -probs.reduce((a, p) => a + (p > 0 ? p * Math.log(p) : 0), 0);
        return Math.round((100 * entropy) / Math.log(weights.length));
    }

    // --- Decade distribution (from top tracks' release dates) ---
    $: decadeData = decadeBuckets(top_tracks || []);
    function decadeBuckets(tracks) {
        const counts = {};
        for (const t of tracks) {
            const y = parseInt((t.release_date || '').slice(0, 4), 10);
            if (!y) continue;
            const dec = Math.floor(y / 10) * 10;
            counts[dec] = (counts[dec] || 0) + 1;
        }
        return Object.keys(counts).sort((a, b) => a - b).map((d) => ({ label: `${d}s`, value: counts[d] }));
    }

    // --- Top tracks rendered via SongCard (adapter from flat shape) ---
    $: trackCards = (top_tracks || []).map(toSongCardShape);
    function toSongCardShape(track) {
        return {
            spotify: {
                id: track.id,
                title: track.title,
                artists: track.artists,
                album: track.album,
                image: track.image,
                track_url: track.track_url,
                duration_ms: track.duration_ms,
            },
        };
    }

    $: maybeCheckSaved(trackCards);
    async function maybeCheckSaved(cards) {
        const ids = cards.map((c) => c.spotify.id);
        const key = ids.join(',');
        if (!ids.length || key === savedKey) return;
        savedKey = key;
        savedMap = await getSavedStates(ids);
    }

    async function handleSaveToggle(id, newSaved) {
        savedMap = { ...savedMap, [id]: newSaved };
        const r = await setTrackSaved(id, newSaved);
        if (r.error) savedMap = { ...savedMap, [id]: !newSaved };
    }

    function exploreTrack(song) {
        $selectedSong = { title: song.title, artists: song.artists, id: song.id, image: song.image };
        goto('/');
    }

</script>

<svelte:head>
	<title>Profile</title>
	<meta name="Profile" content="Profile" />
</svelte:head>

<div class='profile-body'>
    <!-- <div class='login-form'>
        <label for='username'>Username</label>
        <input class='username-input' id='username' placeholder="Username..." bind:value={username}/>

        <label for='password'>Password</label>
        <input class='password-input' id='password' placeholder="Password..." bind:value={password}/>
    </div> -->
    <!-- {#if $logged_in === false} -->
    {#if logged_in === false}
    <div class='login-button-div'>
        <button on:click={handleLogin} class='login-button'>Login with Spotify</button>
    </div>
    {:else}
    <div class='profile-div'>
        <div class='profile-image-div'>
            {#if user_profile.images.length === 0}
            <img src={BoominBeatsLogo} alt="Italian Trulli" class="profile-image">
            {:else}
            <img src={user_profile.images[1].url} alt="Italian Trulli" class="profile-image">
            {/if}
        </div>
        <div class='profile-name-div'>
            {user_profile.display_name}
        </div>
        <div class='followers-div'>
            Followers: {user_profile.followers.total}
        </div>
        <div class='logout-div'>
            <button on:click={handleLogout} class='logout-button'>Log Out</button>
        </div>
    </div>
    <div class='controls-bar'>
        <div class='control-group'>
            <span class='control-label'>Period</span>
            {#each possible_time_periods as time}
                <button class='chip' class:active={time === time_period} on:click={() => setTimePeriod(time)}>{time_period_object[time]}</button>
            {/each}
        </div>
    </div>

    {@const visualsExpanded = ['genres', 'eras', 'taste', 'clock'].includes(expandedModule)}
    <div class='dashboard' class:has-expanded={expandedModule}>
        {#if !expandedModule || expandedModule === 'tracks'}
            <div class='col col-tracks' class:full={expandedModule === 'tracks'}>
                <DashboardModule title="Top Tracks" fullHeight expanded={expandedModule === 'tracks'} onToggleExpand={() => toggleModule('tracks')}>
                    {#each trackCards as card (card.spotify.id)}
                        <SongCard
                            song={card}
                            saved={savedMap[card.spotify.id] || false}
                            onSaveToggle={handleSaveToggle}
                            onExplore={exploreTrack}
                        />
                    {/each}
                </DashboardModule>
            </div>
        {/if}

        {#if !expandedModule || expandedModule === 'artists'}
            <div class='col col-artists' class:full={expandedModule === 'artists'}>
                <DashboardModule title="Top Artists" fullHeight expanded={expandedModule === 'artists'} onToggleExpand={() => toggleModule('artists')}>
                    <div class='col-desc'>
                        <div class='cell-num'>#</div>
                        <div class='cell-img-spacer'></div>
                        <div class='cell-main'>Artist</div>
                        <div class='cell-side'>Genres</div>
                    </div>
                    {#each top_artists as artist, i}
                        <div class='list-row'>
                            <div class='cell-num'>{i+1}</div>
                            <img src={artist.images[0].url} alt={artist.name} class="row-img"/>
                            <div class='cell-main row-name'>{artist.name}</div>
                            <div class='cell-side row-sub'>{artist.genres}</div>
                        </div>
                    {/each}
                </DashboardModule>
            </div>
        {/if}

        {#if !expandedModule || visualsExpanded}
            <div class='col col-visuals' class:full={visualsExpanded}>
                {#if (!expandedModule || expandedModule === 'genres') && genreAxes.length >= 3}
                    <DashboardModule title="Top Genres" scroll={false} expanded={expandedModule === 'genres'} onToggleExpand={() => toggleModule('genres')}>
                        <div class='genre-body'>
                            <SongRadar axes={genreAxes} showValue={false} ariaLabel="Top genres" />
                            <div class='genre-extra'>
                                <div class='diversity'>
                                    <span class='diversity-label'>Diversity</span>
                                    <span class='diversity-val'>{genreDiversity}</span>
                                    <span class='diversity-cap'>{genreDiversity >= 66 ? 'eclectic' : genreDiversity >= 33 ? 'balanced' : 'focused'}</span>
                                </div>
                                <BarChart items={genreBars} />
                            </div>
                        </div>
                    </DashboardModule>
                {/if}

                {#if (!expandedModule || expandedModule === 'eras') && decadeData.length}
                    <DashboardModule title="Eras" scroll={false} expanded={expandedModule === 'eras'} onToggleExpand={() => toggleModule('eras')}>
                        <div class='chart-body'>
                            <ColumnChart items={decadeData} />
                        </div>
                    </DashboardModule>
                {/if}

                {#if (!expandedModule || expandedModule === 'taste') && tasteData}
                    <DashboardModule title="Taste over time" scroll={false} expanded={expandedModule === 'taste'} onToggleExpand={() => toggleModule('taste')}>
                        <div class='taste-body'>
                            {#if audioSeries.length}
                                <TrendChart labels={tasteData.timeframes} series={audioSeries} min={0} max={100} />
                            {:else}
                                <TrendChart labels={tasteData.timeframes} series={[{ name: 'Release year', values: tasteData.release_year }]} min={eraMin} max={eraMax} />
                            {/if}
                            <div class='stat-trends'>
                                {#if audioSeries.length}
                                    <div class='stat-row'>
                                        <span class='era-label'>Era</span>
                                        {#each tasteData.timeframes as tf, i}<span class='era-point'>{tf} <strong>{tasteData.release_year[i] || '—'}</strong></span>{/each}
                                    </div>
                                {/if}
                                <div class='stat-row'>
                                    <span class='era-label'>Avg length</span>
                                    {#each tasteData.timeframes as tf, i}<span class='era-point'>{tf} <strong>{fmtDur(tasteData.avg_duration_ms[i])}</strong></span>{/each}
                                </div>
                                <div class='stat-row'>
                                    <span class='era-label'>Explicit</span>
                                    {#each tasteData.timeframes as tf, i}<span class='era-point'>{tf} <strong>{tasteData.explicit_pct[i]}%</strong></span>{/each}
                                </div>
                            </div>
                        </div>
                    </DashboardModule>
                {/if}

                {#if (!expandedModule || expandedModule === 'clock') && (recentData?.count > 0 || recentNeedsReauth)}
                    <DashboardModule title="Listening clock" scroll={false} expanded={expandedModule === 'clock'} onToggleExpand={() => toggleModule('clock')}>
                        <div class='clock-body'>
                            {#if recentNeedsReauth}
                                <div class='clock-note'>Reconnect Spotify (Log Out → Log in) to enable your listening history.</div>
                            {:else if recentData?.count > 0}
                                <div class='clock-section'>
                                    <div class='clock-section-label'>By hour of day</div>
                                    <Heatmap cells={hourCells} />
                                </div>
                                <div class='clock-section'>
                                    <div class='clock-section-label'>By day of week</div>
                                    <Heatmap cells={dayCells} />
                                </div>
                                <div class='clock-note'>Based on your last {recentData.count} plays (Spotify's max).</div>
                            {/if}
                        </div>
                    </DashboardModule>
                {/if}
            </div>
        {/if}
    </div>
    {/if}

</div>

<style>
    .profile-body {
        margin-top: 88px;
    }

    /* --- Login --- */
    .login-button-div {
        display: flex;
        width: 40%;
        min-width: 320px;
        background-color: var(--surface-1);
        border: 1px solid var(--border-subtle);
        height: 120px;
        border-radius: var(--radius-lg);
        margin: 40px auto;
        align-items: center;
        justify-content: center;
    }

    .login-button {
        height: 44px;
        padding: 0 24px;
        background: var(--brand-gradient);
        color: var(--surface-0);
        border: none;
        border-radius: var(--radius);
        font-weight: 700;
        font-size: 0.9rem;
        cursor: pointer;
        transition: filter var(--transition);
    }

    .login-button:hover {
        filter: brightness(1.1);
    }

    /* --- Profile header card --- */
    .profile-div {
        display: flex;
        align-items: center;
        gap: 24px;
        background-color: var(--surface-1);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 22px 28px;
    }

    .profile-image-div {
        flex-shrink: 0;
    }

    .profile-image {
        width: 88px;
        height: 88px;
        border-radius: 50%;
        object-fit: cover;
        display: block;
    }

    .profile-name-div {
        flex: 1;
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: var(--text-primary);
    }

    .followers-div {
        color: var(--text-muted);
        font-size: 0.9rem;
    }

    .logout-div {
        margin-left: 8px;
    }

    .logout-button {
        height: 36px;
        padding: 0 16px;
        background-color: var(--surface-2);
        color: var(--text-primary);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius);
        cursor: pointer;
        font-size: 0.8rem;
        transition: border-color var(--transition);
    }

    .logout-button:hover {
        border-color: var(--accent);
    }

    /* --- Controls toolbar --- */
    .controls-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 24px;
        align-items: center;
        margin-top: 16px;
        padding: 10px 16px;
        background-color: var(--surface-1);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
    }

    .control-group {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .control-label {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-subtle);
        margin-right: 4px;
    }

    .chip {
        height: 28px;
        padding: 0 12px;
        background-color: var(--surface-2);
        color: var(--text-muted);
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        font-size: 0.75rem;
        font-weight: 600;
        cursor: pointer;
        transition: border-color var(--transition), color var(--transition),
            background-color var(--transition);
    }

    .chip:hover {
        border-color: var(--accent);
        color: var(--text-primary);
    }

    .chip.active {
        background-color: var(--accent);
        border-color: var(--accent);
        color: var(--surface-0);
    }

    /* --- Modular dashboard (3 columns: tracks | artists | stacked visuals) --- */
    .dashboard {
        display: flex;
        gap: 16px;
        align-items: flex-start;
        margin-top: 16px;
    }

    .col {
        min-width: 0;
    }

    .col-tracks {
        flex: 1.5;
    }

    .col-artists {
        flex: 1;
    }

    .col-visuals {
        flex: 1.15;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    /* When a module is expanded, its column fills the row. */
    .dashboard.has-expanded .col.full {
        flex: 1 1 100%;
        width: 100%;
    }

    .genre-body {
        max-width: 380px;
        margin: 0 auto;
        padding-top: 8px;
    }

    .genre-extra {
        margin-top: 18px;
        padding-top: 16px;
        border-top: 1px solid var(--border-subtle);
    }

    .diversity {
        display: flex;
        align-items: baseline;
        gap: 8px;
        margin-bottom: 14px;
    }

    .diversity-label {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-subtle);
    }

    .diversity-val {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    .diversity-cap {
        font-size: 0.78rem;
        color: var(--text-muted);
    }

    .chart-body {
        padding: 10px 12px 4px;
    }

    .clock-body {
        padding: 10px 12px 4px;
    }

    .clock-section {
        margin-bottom: 18px;
    }

    .clock-section-label {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        color: var(--text-subtle);
        margin-bottom: 8px;
    }

    .clock-note {
        font-size: 0.72rem;
        color: var(--text-subtle);
        margin-top: 8px;
    }

    .taste-body {
        padding: 8px 10px 0;
    }

    .stat-trends {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 14px;
        padding-top: 12px;
        border-top: 1px solid var(--border-subtle);
    }

    .stat-row {
        display: flex;
        flex-wrap: wrap;
        align-items: baseline;
        gap: 6px 14px;
        font-size: 0.78rem;
        color: var(--text-muted);
    }

    .era-label {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-subtle);
    }

    .era-point strong {
        color: var(--text-primary);
        font-weight: 700;
    }

    .col-desc, .list-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 0 14px;
    }

    .col-desc {
        height: 32px;
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-subtle);
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 6px;
    }

    .list-row {
        height: 56px;
        border-radius: var(--radius-sm);
        transition: background-color var(--transition);
    }

    .list-row:hover {
        background-color: var(--surface-2);
    }

    .cell-num {
        width: 20px;
        flex-shrink: 0;
        text-align: right;
        color: var(--text-subtle);
        font-size: 0.85rem;
    }

    .cell-img-spacer, .row-img {
        width: 44px;
        flex-shrink: 0;
    }

    .row-img {
        height: 44px;
        border-radius: var(--radius-sm);
        object-fit: cover;
    }

    .cell-main {
        flex: 1;
        min-width: 0;
    }

    .cell-side {
        width: 28%;
        flex-shrink: 0;
        min-width: 0;
    }

    .cell-trail {
        width: 72px;
        flex-shrink: 0;
        text-align: right;
    }

    .row-name {
        color: var(--text-primary);
        font-weight: 600;
        font-size: 0.88rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .row-sub {
        color: var(--text-muted);
        font-size: 0.8rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

</style>