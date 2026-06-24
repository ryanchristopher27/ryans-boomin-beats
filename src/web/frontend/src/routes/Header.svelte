<script>
	import { page, llmConfig, playlistsPanelOpen } from '../stores.js';
	import { BoominBeatsLogo } from '$lib';
	import LLMSettingsPanel from '$lib/components/LLMSettingsPanel.svelte';

	const navLinks = [
		{ label: 'Explore', href: '/', page: 'Explore' },
		{ label: 'Playlist Builder', href: '/playlist-builder/', page: 'Playlist Builder' },
		{ label: 'Profile', href: '/profile/', page: 'Profile' },
	];

	let settingsOpen = false;
</script>

<header>
	<div class="header-bar">
		<div class="logo-div">
			<img src={BoominBeatsLogo} alt="Boomin Beats" id="boomin-beats-logo" />
		</div>

		<nav>
			{#each navLinks as link}
				<a class="nav-link" class:active={$page === link.page} href={link.href}>
					{link.label}
				</a>
			{/each}
		</nav>

		<div class="header-actions">
			<button
				class="playlists-toggle"
				class:active={$playlistsPanelOpen}
				on:click={() => ($playlistsPanelOpen = !$playlistsPanelOpen)}
				title="Playlists"
			>
				Playlists
			</button>
			<button
				class="settings-toggle"
				class:connected={$llmConfig.connected}
				on:click={() => (settingsOpen = !settingsOpen)}
				title="AI Settings"
			>
				<span class="settings-icon">⚙</span>
				{#if $llmConfig.connected}
					<span class="connected-dot"></span>
				{/if}
			</button>
		</div>
	</div>

	{#if settingsOpen}
		<div class="settings-popover">
			<LLMSettingsPanel onClose={() => (settingsOpen = false)} />
		</div>
	{/if}
</header>

<style>
	header {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		z-index: 50;
		display: flex;
		justify-content: center;
		padding: 12px var(--primary-spacing);
		box-sizing: border-box;
		background: linear-gradient(180deg, var(--surface-0) 60%, transparent 100%);
	}

	.header-bar {
		display: flex;
		align-items: center;
		height: 56px;
		width: 100%;
		min-width: 800px;
		padding: 0 16px;
		box-sizing: border-box;
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-lg);
	}

	.logo-div {
		display: flex;
		align-items: center;
		min-width: 50px;
	}

	#boomin-beats-logo {
		height: 38px;
		border-radius: var(--radius-sm);
		display: block;
	}

	nav {
		display: flex;
		justify-content: center;
		align-items: center;
		gap: 8px;
		flex: 1;
	}

	.nav-link {
		display: flex;
		align-items: center;
		height: 34px;
		padding: 0 18px;
		border-radius: 17px;
		color: var(--text-muted);
		font-weight: 600;
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		text-decoration: none;
		transition: color var(--transition), background-color var(--transition);
	}

	.nav-link:hover {
		color: var(--text-primary);
		background-color: var(--surface-2);
	}

	.nav-link.active {
		background: var(--brand-gradient);
		color: var(--surface-0);
		font-weight: 700;
	}

	.nav-link.active:hover {
		color: var(--surface-0);
	}

	.header-actions {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 10px;
		min-width: 50px;
	}

	.playlists-toggle {
		height: 34px;
		padding: 0 14px;
		background: none;
		border: 1px solid var(--border-subtle);
		border-radius: 17px;
		color: var(--text-muted);
		font-weight: 600;
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		cursor: pointer;
		white-space: nowrap;
		transition: color var(--transition), background-color var(--transition), border-color var(--transition);
	}

	.playlists-toggle:hover {
		color: var(--text-primary);
		border-color: var(--accent);
	}

	.playlists-toggle.active {
		background: var(--brand-gradient);
		color: var(--surface-0);
		border-color: transparent;
	}

	.settings-toggle {
		position: relative;
		background: none;
		border: 1px solid var(--border-subtle);
		border-radius: 50%;
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		padding: 0;
		transition: border-color var(--transition), background-color var(--transition);
	}

	.settings-toggle:hover {
		border-color: var(--accent);
		background-color: var(--surface-2);
	}

	.settings-toggle.connected {
		border-color: var(--accent);
	}

	.settings-icon {
		font-size: 1rem;
		color: var(--text-muted);
		line-height: 1;
		transition: color var(--transition);
	}

	.settings-toggle:hover .settings-icon {
		color: var(--accent);
	}

	.connected-dot {
		position: absolute;
		top: -2px;
		right: -2px;
		width: 9px;
		height: 9px;
		background-color: #6bffb8;
		border-radius: 50%;
		border: 2px solid var(--surface-1);
	}

	.settings-popover {
		position: absolute;
		top: calc(100% - 4px);
		right: 30px;
		z-index: 50;
	}
</style>
