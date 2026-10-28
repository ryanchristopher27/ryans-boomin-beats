<script>
	import { page, llmConfig, playlistsPanelOpen, llmSettingsOpen } from '../stores.js';
	import BoominBeatsLogo from '$lib/images/BoominBeatsLogo.jpg';
	import LLMSettingsPanel from '$lib/components/LLMSettingsPanel.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { getDJ } from '$lib/dj/instance.js';

	const navLinks = [
		{ label: 'Explore', href: '/', page: 'Explore', icon: 'compass' },
		{ label: 'Builder', href: '/playlist-builder/', page: 'Playlist Builder', icon: 'wand' },
		{ label: 'DJ', href: '/dj/', page: 'DJ', icon: 'disc' },
		{ label: 'Profile', href: '/profile/', page: 'Profile', icon: 'user' }
	];

	// The DJ tab shows a dot while music plays anywhere in the app.
	const player = getDJ()?.player;
	$: playing = !!($player?.state?.active && $player.state.is_playing);
</script>

<header>
	<a class="brand" href="/">
		<img src={BoominBeatsLogo} alt="" width="30" height="30" />
		<span>Boomin Beats</span>
	</a>

	<nav aria-label="Main">
		{#each navLinks as link}
			<a class="nav-link" class:active={$page === link.page} aria-current={$page === link.page ? 'page' : undefined} href={link.href}>
				<Icon name={link.icon} size={15} />
				{link.label}
				{#if link.page === 'DJ' && playing}<span class="live" aria-label="(playing)" />{/if}
			</a>
		{/each}
	</nav>

	<div class="actions">
		<button
			class="btn small"
			class:on={$playlistsPanelOpen}
			aria-pressed={$playlistsPanelOpen}
			on:click={() => ($playlistsPanelOpen = !$playlistsPanelOpen)}
		>
			<Icon name="playlist" size={15} /> Playlists
		</button>
		<button
			class="gear"
			class:on={$llmSettingsOpen}
			on:click={() => ($llmSettingsOpen = !$llmSettingsOpen)}
			aria-label={$llmConfig.connected ? 'Settings (AI connected)' : 'Settings (no AI connected)'}
			aria-expanded={$llmSettingsOpen}
		>
			<Icon name="gear" size={17} />
			<span class="dot" class:connected={$llmConfig.connected} />
		</button>
	</div>
</header>

{#if $llmSettingsOpen}
	<LLMSettingsPanel onClose={() => ($llmSettingsOpen = false)} />
{/if}

<style>
	header {
		position: sticky;
		top: 0;
		z-index: 50;
		height: var(--header-height);
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 0 20px;
		border-bottom: 1px solid var(--border-subtle);
		background: rgba(10, 10, 12, 0.82);
		-webkit-backdrop-filter: blur(20px);
		backdrop-filter: blur(20px);
	}

	.brand {
		width: 220px;
		display: flex;
		align-items: center;
		gap: 10px;
		color: var(--text-primary);
		font-size: 15px;
		font-weight: 600;
		letter-spacing: -0.01em;
	}

	.brand:hover {
		color: var(--text-primary);
	}

	.brand img {
		border-radius: 8px;
		object-fit: cover;
	}

	/* A segmented track, centred between brand and actions. */
	nav {
		display: flex;
		gap: 2px;
		margin: 0 auto;
		padding: 3px;
		border-radius: 11px;
		background: var(--surface-1);
		border: 1px solid rgba(255, 255, 255, 0.06);
	}

	.nav-link {
		height: 32px;
		display: inline-flex;
		align-items: center;
		gap: 7px;
		padding: 0 14px;
		border-radius: 8px;
		color: var(--text-muted);
		font-size: 13px;
		font-weight: 500;
		transition: background-color var(--transition), color var(--transition);
	}

	.nav-link:hover {
		color: var(--text-primary);
	}

	.nav-link.active {
		background: var(--surface-active);
		color: var(--text-primary);
	}

	.nav-link.active :global(.icon) {
		color: var(--accent);
	}

	.live {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--accent);
	}

	.actions {
		width: 220px;
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 8px;
	}

	.actions .btn {
		height: 34px;
		border-color: var(--border-control);
		background: var(--surface-1);
	}

	.actions .btn.on {
		background: var(--surface-active);
		border-color: var(--border-strong);
	}

	.gear {
		position: relative;
		width: 34px;
		height: 34px;
		display: grid;
		place-items: center;
		padding: 0;
		border-radius: 50%;
		border: 1px solid var(--border-control);
		background: var(--surface-1);
		color: var(--text-primary);
		cursor: pointer;
		transition: background-color var(--transition);
	}

	.gear:hover,
	.gear.on {
		background: var(--surface-2);
	}

	.dot {
		position: absolute;
		top: 1px;
		right: 1px;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: rgba(243, 243, 245, 0.3);
		box-shadow: 0 0 0 2px var(--surface-0);
	}

	.dot.connected {
		background: var(--success);
	}

	/* Below desktop the brand and actions shrink to their content. */
	@media (max-width: 1179px) {
		.brand,
		.actions {
			width: auto;
		}
		.brand span {
			display: none;
		}
	}
</style>
