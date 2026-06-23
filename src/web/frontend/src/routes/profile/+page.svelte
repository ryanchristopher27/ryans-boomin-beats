<script>
    import { onMount } from 'svelte';
    import { PUBLIC_API_URL } from '$env/static/public';
    import { BoominBeatsLogo } from "$lib";

    import { page, user, access_token} from '../../stores.js'

    let token = $access_token;

    let user_profile = {};
    let top_artists = [];
    let top_tracks = [];

    let possible_number_of_tops = [10, 25, 50];
    let number_of_tops = 10;

    let possible_time_periods = ['short_term', 'medium_term', 'long_term'];
    let time_period = 'short_term';
    let time_period_object = {'short_term': '1 Month', 'medium_term': '6 Months', 'long_term': 'All Time'}

    let logged_in = false;

    const CLIENT_ID = 'a700071d47504ba68082a5a59d2b0bc0';
    const SPOTIFY_AUTHORIZE_ENDPOINT = 'https://accounts.spotify.com/authorize';
    const REDIRECT_URI = 'http://127.0.0.1:5173/profile';
    const SCOPES = 'user-top-read playlist-read-private playlist-modify-private playlist-modify-public user-modify-playback-state';

    // PKCE helpers
    function generateCodeVerifier(length = 128) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
        const array = new Uint8Array(length);
        crypto.getRandomValues(array);
        return Array.from(array).map(b => chars[b % chars.length]).join('');
    }

    async function generateCodeChallenge(verifier) {
        const data = new TextEncoder().encode(verifier);
        const digest = await crypto.subtle.digest('SHA-256', data);
        return btoa(String.fromCharCode(...new Uint8Array(digest)))
            .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    }

    // Token storage helpers
    function saveTokens(tokenData) {
        localStorage.setItem('spotify_access_token', tokenData.access_token);
        localStorage.setItem('spotify_refresh_token', tokenData.refresh_token);
        localStorage.setItem('spotify_expires_at', Date.now() + tokenData.expires_in * 1000);
    }

    function loadStoredToken() {
        const accessToken = localStorage.getItem('spotify_access_token');
        const refreshToken = localStorage.getItem('spotify_refresh_token');
        const expiresAt = parseInt(localStorage.getItem('spotify_expires_at') || '0');
        if (!accessToken) return null;
        return { accessToken, refreshToken, expiresAt };
    }

    function clearStoredTokens() {
        localStorage.removeItem('spotify_access_token');
        localStorage.removeItem('spotify_refresh_token');
        localStorage.removeItem('spotify_expires_at');
    }

    function handleLogout() {
        clearStoredTokens();
        $access_token = '';
        token = '';
        logged_in = false;
    }

    async function exchangeCodeForToken(code, verifier) {
        const res = await fetch('https://accounts.spotify.com/api/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                code,
                redirect_uri: REDIRECT_URI,
                client_id: CLIENT_ID,
                code_verifier: verifier,
            }),
        });
        return res.json();
    }

    async function refreshAccessToken(refreshToken) {
        const res = await fetch('https://accounts.spotify.com/api/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                grant_type: 'refresh_token',
                refresh_token: refreshToken,
                client_id: CLIENT_ID,
            }),
        });
        return res.json();
    }

    onMount(async () => {
        $page = 'Profile';

        // Check if returning from Spotify OAuth
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

        // Check localStorage for a stored session
        const stored = loadStoredToken();
        if (stored) {
            if (Date.now() < stored.expiresAt) {
                // Token still valid
                token = stored.accessToken;
                $access_token = token;
                getProfile();
            } else if (stored.refreshToken) {
                // Token expired — refresh silently
                const tokenData = await refreshAccessToken(stored.refreshToken);
                if (tokenData.access_token) {
                    saveTokens(tokenData);
                    token = tokenData.access_token;
                    $access_token = token;
                    getProfile();
                } else {
                    // Refresh failed — clear stored tokens and show login
                    clearStoredTokens();
                }
            } else {
                clearStoredTokens();
            }
        }
    });

    const handleLogin = async () => {
        if (typeof window === 'undefined') return;
        const verifier = generateCodeVerifier();
        const challenge = await generateCodeChallenge(verifier);
        sessionStorage.setItem('spotify_pkce_verifier', verifier);
        const params = new URLSearchParams({
            client_id: CLIENT_ID,
            response_type: 'code',
            redirect_uri: REDIRECT_URI,
            scope: SCOPES,
            code_challenge_method: 'S256',
            code_challenge: challenge,
            show_dialog: 'true',
        });
        window.location = `${SPOTIFY_AUTHORIZE_ENDPOINT}?${params}`;
    };

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
            // $logged_in = true;

		} catch (error) {
			// Handle any errors that occurred during the fetch request.
			console.error('Error fetching data:', error);
		}
    }

    function millisToMinutesAndSeconds(millis) {
        let minutes = Math.floor(millis / 60000);
        let seconds = ((millis % 60000) / 1000).toFixed(0);
        return (seconds == 60 ? (minutes+1) + ":00" : minutes + ":" + (Number(seconds) < 10 ? "0" : "") + seconds
        );    
    }

    let setNumberOfTops = (number) => {
		number_of_tops = number;
        getProfile()
	}
    
    let setTimePeriod = (time) => {
        time_period = time;
        getProfile()
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
    <div class='top-parameters-div'>
        <div class='number-of-tops-div'>
			{#each possible_number_of_tops as num}
			{#if num === number_of_tops}
			<button class='number-of-tops-button-selected' on:click={() => {setNumberOfTops(num)}}>{num}</button>
			{:else}
			<button class='number-of-tops-button' on:click={() => {setNumberOfTops(num)}}>{num}</button>
			{/if}
			{/each}
		</div>
        <div class='time-period-div'>
			{#each possible_time_periods as time}
			{#if time === time_period}
			<button class='time-period-button-selected' on:click={() => {setTimePeriod(time)}}>{time_period_object[time]}</button>
			{:else}
			<button class='time-period-button' on:click={() => {setTimePeriod(time)}}>{time_period_object[time]}</button>
			{/if}
			{/each}
		</div>
    </div>
    <div class='top-div'>
        <div class='top-list-card'>
            <div class='top-list-header'>Top Artists</div>
            <div class='col-desc'>
                <div class='cell-num'>#</div>
                <div class='cell-img-spacer'></div>
                <div class='cell-main'>Artist</div>
                <div class='cell-side'>Genres</div>
                <div class='cell-trail'>Popularity</div>
            </div>
            {#each top_artists as artist, i}
                <div class='list-row'>
                    <div class='cell-num'>{i+1}</div>
                    <img src={artist.images[0].url} alt={artist.name} class="row-img"/>
                    <div class='cell-main row-name'>{artist.name}</div>
                    <div class='cell-side row-sub'>{artist.genres}</div>
                    <div class='cell-trail row-sub'>{artist.popularity}</div>
                </div>
            {/each}
        </div>
        <div class='top-list-card'>
            <div class='top-list-header'>Top Tracks</div>
            <div class='col-desc'>
                <div class='cell-num'>#</div>
                <div class='cell-img-spacer'></div>
                <div class='cell-main'>Title</div>
                <div class='cell-side'>Album</div>
                <div class='cell-trail'>Duration</div>
            </div>
            {#each top_tracks as track, i}
                <div class='list-row'>
                    <div class='cell-num'>{i+1}</div>
                    <img src={track.image} alt={track.album} class="row-img"/>
                    <div class='cell-main track-main'>
                        <div class='row-name'>{track.title}</div>
                        <div class='row-sub track-artists'>
                            {#if track.explicit}<span class='explicit-badge'>E</span>{/if}
                            {track.artists.join(', ')}
                        </div>
                    </div>
                    <div class='cell-side row-sub'>{track.album}</div>
                    <div class='cell-trail row-sub'>{millisToMinutesAndSeconds(Number(track.duration_ms))}</div>
                </div>
            {/each}
        </div>
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

    /* --- Parameter selectors --- */
    .top-parameters-div {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 28px;
        background-color: var(--surface-1);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 16px;
        margin-top: 16px;
    }

    .number-of-tops-div, .time-period-div {
        display: flex;
        gap: 8px;
        align-items: center;
    }

    .number-of-tops-button, .time-period-button,
    .number-of-tops-button-selected, .time-period-button-selected {
        height: 34px;
        padding: 0 16px;
        border-radius: var(--radius);
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition: border-color var(--transition), color var(--transition),
            background-color var(--transition);
    }

    .number-of-tops-button, .time-period-button {
        background-color: var(--surface-2);
        color: var(--text-muted);
        border: 1px solid var(--border-subtle);
    }

    .number-of-tops-button:hover, .time-period-button:hover {
        border-color: var(--accent);
        color: var(--text-primary);
    }

    .number-of-tops-button-selected, .time-period-button-selected {
        background-color: var(--accent);
        color: var(--surface-0);
        border: 1px solid var(--accent);
    }

    /* --- Top lists --- */
    .top-div {
        display: flex;
        gap: 16px;
        margin-top: 16px;
    }

    .top-list-card {
        flex: 1;
        min-width: 0;
        background-color: var(--surface-1);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 8px 8px 14px;
    }

    .top-list-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--text-primary);
        padding: 14px 14px 10px;
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

    .track-main {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .track-artists {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .explicit-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        height: 16px;
        min-width: 16px;
        padding: 0 3px;
        font-size: 0.6rem;
        font-weight: 700;
        background-color: var(--text-subtle);
        color: var(--surface-0);
        border-radius: 3px;
        flex-shrink: 0;
    }
</style>