<script>
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import Header from './Header.svelte';
	import PlaylistsPanel from '$lib/components/PlaylistsPanel.svelte';
	import MiniPlayer from '$lib/components/dj/MiniPlayer.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Toast from '$lib/components/Toast.svelte';
	import Onboarding from '$lib/components/settings/Onboarding.svelte';
	import { onboarding } from '$lib/onboarding.js';
	import { loadStoredToken } from '$lib/spotifyAuth.js';
	import { hydrateToken } from '$lib/spotifyAuth.js';
	import { getDJ } from '$lib/dj/instance.js';
	import { access_token, playlistsPanelOpen } from '../stores.js';
	import { playbackMotion, textScale } from '$lib/settings.js';
	import './styles.css';

	// Load the Spotify session app-wide so account actions work on every page,
	// not just Profile. Skips the OAuth callback (handled by the Profile page).
	onMount(() => {
		// First run for someone who has never signed in here; existing users skip it.
		if ($onboarding == null) $onboarding = loadStoredToken() ? 0 : 1;
		if (!new URLSearchParams(window.location.search).has('code')) {
			hydrateToken();
		}
		// Keep the Spotify token fresh while the page stays open (review C2);
		// hydrateToken only refreshes within a couple of minutes of expiry.
		const timer = setInterval(() => hydrateToken(), 60 * 1000);
		return () => clearInterval(timer);
	});

	// The DJ engine runs app-wide once signed in, so a driving tab keeps
	// driving (and the mini player stays live) on every page.
	// ...and stops on sign-out instead of polling with no token (review W4).
	$: if (browser) $access_token ? getDJ()?.start() : getDJ()?.stop();

	// General settings apply app-wide: every font-size multiplies --text-scale,
	// and data-motion pauses the playback animations (styles.css).
	$: if (browser) document.documentElement.style.setProperty('--text-scale', String($textScale));
	$: if (browser) document.documentElement.dataset.motion = $playbackMotion ? 'on' : 'off';
</script>

<div class="app" class:panel-open={$playlistsPanelOpen}>
	<a class="skip" href="#main">Skip to content</a>
	<Header />

	<main id="main" tabindex="-1">
		<slot />
	</main>

	<PlaylistsPanel />
	{#if browser}<MiniPlayer />{/if}
	<CommandPalette />
	<Toast />
	{#if browser && $onboarding}<Onboarding />{/if}
</div>

<style>
	.app {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
		background-color: var(--surface-0);
	}

	main {
		flex: 1;
		display: flex;
		flex-direction: column;
		padding: var(--primary-spacing);
		background-color: var(--surface-0);
	}

	main:focus {
		outline: none;
	}

	/* Hidden until a keyboard user tabs to it. */
	.skip {
		position: fixed;
		left: 16px;
		top: 12px;
		z-index: 100;
		padding: 8px 14px;
		border-radius: 9px;
		background: var(--accent);
		color: var(--accent-on);
		font-size: calc(13px * var(--text-scale, 1));
		font-weight: 600;
		transform: translateY(-200%);
	}

	.skip:focus {
		transform: none;
	}

	/* Make room for the docked Playlists panel (it animates in; the page just reflows once). */
	.app.panel-open main {
		margin-right: var(--panel-width);
	}

	@media (max-width: 759px) {
		main {
			padding: 16px;
		}
	}
</style>
