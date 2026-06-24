<script>
	import { onMount } from 'svelte';
	import Header from './Header.svelte';
	import PlaylistsPanel from '$lib/components/PlaylistsPanel.svelte';
	import { hydrateToken } from '$lib/spotifyAuth.js';
	import { playlistsPanelOpen } from '../stores.js';
	import './styles.css';

	// Load the Spotify session app-wide so account actions work on every page,
	// not just Profile. Skips the OAuth callback (handled by the Profile page).
	onMount(() => {
		if (!new URLSearchParams(window.location.search).has('code')) {
			hydrateToken();
		}
	});
</script>

<div class="app" class:panel-open={$playlistsPanelOpen}>
	<Header />

	<main>
		<slot />
	</main>

	<PlaylistsPanel />
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
		box-sizing: border-box;
		background-color: var(--surface-0);
		transition: margin-right 0.2s ease;
	}

	/* Make room for the docked Playlists panel (width + its right margin). */
	.app.panel-open main {
		margin-right: calc(var(--panel-width) + var(--primary-spacing));
	}

	/* footer {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		padding: 12px;
	}

	footer a {
		font-weight: bold;
	}

	@media (min-width: 480px) {
		footer {
			padding: 12px 0;
		}
	} */
</style>
