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
        <div class='top-artists-div'>
            <div class='top-artists-header-div'>
                Top Artists
            </div>
            <hr class='track-splitter'>
            <div class='col-desc'>
                <div class='col-num'>#</div>
                <div class='col-artist'>Artist</div>
                <div class='col-genres'>Genres</div>
                <div class='col-popularity'>Popularity</div>
            </div>
            <hr class='track-splitter'>
            {#each top_artists as artist, i}
                <div class='top-artist-div'>
                    <div class='number-div'>
                        {i+1}
                    </div>
                    <img src={artist.images[0].url} alt="{artist.album}" class="artist-image"/>
                    <div class='artist-name-div'>
                        {artist.name}
                    </div>
                    <div class='artist-genres-div'>
                        {artist.genres}
                    </div>
                    <div class='artist-popularity-div'>
                        {artist.popularity}
                    </div>
                </div>
                {#if i != top_artists.length-1}
                    <hr class='track-splitter'>
                {/if}
            {/each}
        </div>
        <div class='top-tracks-div'>
            <div class='top-tracks-header-div'>
                Top Tracks
            </div>
            <hr class='track-splitter'>
            <div class='col-desc'>
                <div class='col-num'>#</div>
                <div class='col-title'>Title</div>
                <div class='col-album'>Album</div>
                <div class='col-duration'>Duration</div>
            </div>
            <hr class='track-splitter'>
            {#each top_tracks as track, i}
                <div class='top-track-div'>
                    <div class='number-div'>
                        {i+1}
                    </div>
                    <img src={track.image} alt="{track.album}" class="track-image"/>
                    <div class='title-artist-div'>
                        <div class='title-div'>
                            {track.title}
                        </div>
                        <div class='artist-div'>
                            {#if track.explicit === true}
                                <div class='explicit-div'>
                                    E
                                </div>
                            {/if}
                            {#each track.artists as artist, i}
                                <div class='each-artist-div'>
                                    {#if i === track.artists.length - 1}
                                        {artist}
                                    {:else}
                                        {artist},
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    </div>
                    <div class='album-div'>
                        {track.album}
                    </div>
                    <div class='duration-div'>
                        {millisToMinutesAndSeconds(Number(track.duration_ms))}
                    </div>
                </div>
                {#if i != top_tracks.length-1}
                    <hr class='track-splitter'>
                {/if}
            <!-- <iframe style="border-radius:12px" src={`https://open.spotify.com/embed/track/${track.id}?utm_source=generator&theme=0`} width="100%" height="152" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe> -->
            <!-- <iframe style="border-radius:12px" src={`https://open.spotify.com/embed/track/${track.id}?utm_source=generator`} width="100%" height="76" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe> -->
            {/each}
        </div>
    </div>
    {/if}

</div>

<style>
    .login-button-div {
        display: flex;
        width: 40%;
        background-color: var(--color-dark-gray);
        height: 80px;
        border-radius: 20px;
        margin: auto;
        align-items: center;
        justify-content: center;
    }

    .login-button {
        height: 30px;
		background-color: var(--color-dark-gray);
		color: var(--color-light-blue);
		border: 2px solid var(--color-light-blue);
		border-radius: 10px;
    }

    .profile-body {
        margin-top: 70px;
    }

    .profile-div {
        height: 120px;
        display: flex;
        align-items: center;
        background-color: var(--color-dark-gray);
        border-radius: 20px;
    }

    .profile-image-div {
        width: 20%;
    }

    .profile-image {
        width: 100px;
        height: 100px;
        border-radius: 5px;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }

    .profile-name-div {
        width: 40%;
        text-align: center;
        font-size: 30px;
    }

    .followers-div {
        width: 30%;
        text-align: center;
        font-size: 20px;
    }

    .logout-div {
        width: 10%;
        display: flex;
        justify-content: center;
    }

    .logout-button {
        height: 30px;
        padding: 0 14px;
        background-color: var(--color-dark-gray);
        color: var(--color-light-blue);
        border: 2px solid var(--color-light-blue);
        border-radius: 10px;
        cursor: pointer;
        font-size: 0.8rem;
    }

    .logout-button:hover {
        border-color: var(--color-purple);
        color: var(--color-purple);
    }

    .top-parameters-div {
        width: 100%;
		background-color: var(--color-dark-gray);
		border-radius: 20px;
		padding-top: 10px;
		padding-bottom: 10px;
		margin-top: 20px;
    }

    .number-of-tops-div, .time-period-div {
		display: flex;
		width: 80%;
		min-width: 640px;

		margin: 20px 0 20px 10%;
	}

	.number-of-tops-button, .time-period-button {
		height: 30px;
		width: 10%;
		margin-left: 15%;
		background-color: var(--color-dark-gray);
		color: var(--color-light-blue);
		border: 2px solid var(--color-light-blue);
		border-radius: 10px;
	}

	.number-of-tops-button-selected, .time-period-button-selected {
		height: 30px;
		width: 10%;
		margin-left: 15%;
		background-color: var(--color-light-blue);
		color: var(--color-dark-gray);
		border: 2px solid var(--color-light-blue);
		border-radius: 10px;
	}

    .login-button:hover, .number-of-tops-button:hover, .time-period-button:hover, .number-of-tops-button-selected:hover, .time-period-button-selected:hover {
        border-color: var(--color-purple);
        color: var(--color-purple)
    }

    .top-div {
        display: flex;
        margin-top: 20px;
    }

    .top-artists-div {
        width: 49%;
        margin-right: 1%;
        background-color: var(--color-dark-gray);
        border-radius: 20px;
        padding-bottom: 10px;
    }

    .top-artists-header-div {
        height: 40px;
        align-items: center;
        text-align: center;
        font-size: 30px;
        margin: 10px auto;
    }

    .top-artist-div {
        /* display: flex;
        align-content: center;
        justify-content: center; */
        display: flex;
        height: 64px;
        align-items: center;
    }

    .artist-image {
        height: 64px;
        width: 64px;
    }

    .top-tracks-div {
        width: 49%;
        margin-left: 1%;
        background-color: var(--color-dark-gray);
        border-radius: 20px;
        padding-bottom: 10px;
    }

    .top-tracks-header-div {
        height: 40px;
        align-items: center;
        text-align: center;
        font-size: 30px;
        margin: 10px auto;
    }

    .top-track-div {
        display: flex;
        height: 64px;
        align-items: center;
    }

    .number-div {
        width: 5%;
        align-items: center;
        text-align: center;
    }

    .title-artist-div {
        width: 40%;
        white-space: nowrap;
        overflow: hidden;
        padding: 0 10px;
    }

    .artist-name-div {
        width: 33%;
        white-space: nowrap;
        overflow: hidden;
        padding: 0 10px;
        font-weight: bold;
    }

    .title-div {
        display: table-cell;
        height: 40px;
        width: 100%;
        vertical-align: middle;
        font-weight: bold;
        /* text-align: center; */
    }

    .artist-div {
        display: flex;
        height: 24px;
        width: 100%;
        vertical-align: middle;
        align-items: center;
        /* text-align: center; */
    }

    .explicit-div {
        height: 15px;
        width: 15px;
        margin-right: 5px;
        text-align: center;
        font-size: 12px;
        background-color: white;
        color: var(--color-dark-gray);
        border-radius: 2px;
    }

    .each-artist-div {
        margin-right: 10px;
    }

    .album-div {
        width: 25%;
        padding: 0 10px;
        vertical-align: middle;
        text-align: center;
        white-space: nowrap;
        overflow: hidden;
    }

    .artist-genres-div {
        width: 32%;
        padding: 0 10px;
        vertical-align: middle;
        text-align: center;
        white-space: nowrap;
        overflow: hidden;
    }

    .duration-div, .artist-popularity-div {
        width: 20%;
        padding: 0 10px;
        vertical-align: middle;
        text-align: center;
    }

    .col-desc {
        display: flex;
        height: 1rem;
    }

    .col-num {
        width: 5%;
        text-align: center;
    }

    .col-artist {
        width: 40%;
        text-align: center;
    }

    .col-genres {
        width: 34%;
        text-align: center;
    }

    .col-title{
        width: 47%;
        text-align: center;
    }
    .col-album{
        width: 27%;
        text-align: center;
    }
    .col-duration, .col-popularity {
        width: 21%;
        text-align: center;
    }

    .track-splitter {
        color: white;
        width: 95%;
    }
</style>