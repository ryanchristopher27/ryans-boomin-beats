<script>
	import { page, llmConfig } from '../stores.js';
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
	<div class="header-div">
		<div class="logo-div">
			<img src={BoominBeatsLogo} alt="BoominBeatsLogo" id="boomin-beats-logo"/>
		</div>

		<nav>
			{#each navLinks as link}
			<div class="nav-button-div">
				<a class={$page === link.page ? 'nav-button-active' : 'nav-button'} href={link.href}>
					{link.label}
				</a>
			</div>
			{/each}
		</nav>

		<div class="header-actions">
			<button class="settings-toggle" on:click={() => settingsOpen = !settingsOpen} title="AI Settings">
				<span class="settings-icon">⚙</span>
				{#if $llmConfig.connected}
					<span class="connected-dot"></span>
				{/if}
			</button>
		</div>
	</div>

	{#if settingsOpen}
		<div class="settings-popover">
			<LLMSettingsPanel onClose={() => settingsOpen = false} />
		</div>
	{/if}
</header>

<style>
	header {
		display: flex;
		justify-content: space-between;
		position: fixed;
		top: 0;
		width: 98%;
		min-width: 800px;
		background-color: var(--color-light-blue);
		/* margin: var(--primary-spacing) var(--primary-spacing) 0 var(--primary-spacing); */
		padding: var(--primary-spacing);
	}

	.header-div {
		display: flex;
		align-items: center;
		height: 50px;
		background-color: #242424;
		width: 100%;
		min-width: 800px;
		border-bottom: 2px solid var(--color-light-blue);
		border-radius: 20px;
	}

	.header-actions {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		min-width: 50px;
		margin-right: 10px;
	}

	.settings-toggle {
		position: relative;
		background: none;
		border: 2px solid var(--color-light-blue);
		border-radius: 50%;
		width: 34px;
		height: 34px;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		padding: 0;
	}

	.settings-toggle:hover {
		border-color: var(--color-purple);
	}

	.settings-icon {
		font-size: 1rem;
		color: var(--color-light-blue);
		line-height: 1;
	}

	.connected-dot {
		position: absolute;
		top: -3px;
		right: -3px;
		width: 9px;
		height: 9px;
		background-color: #6bffb8;
		border-radius: 50%;
		border: 1px solid var(--color-dark-gray);
	}

	.settings-popover {
		position: absolute;
		top: calc(100% - 8px);
		right: 15px;
		z-index: 50;
	}

	#boomin-beats-logo {
		height: 40px;
		margin-top: 5px;
		margin-left: 5px;
	}

	.nav-button-div {
		height: 50px;
		/* padding: 10px 0; */
	}

	.nav-button {
		margin: 8px 20px;
		height: 30px;
		border: 2px solid #5ec9ff;
		border-radius: 20px;
	}

	nav {
		display: flex;
		justify-content: center;
		flex: 1;
	}

	nav a {
		display: flex;
		/* height: 40px; */
		align-items: center;
		padding: 0 0.5rem;
		color: var(--color-light-blue);
		font-weight: 700;
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		text-decoration: none;
		transition: color 0.2s linear;
	}

	a:hover {
		/* color: var(--color-dark-gray);
		background-color: var(--color-purple); */
		border-color: var(--color-purple);
	}

	.nav-button-active {
		color: var(--color-dark-gray);
		background-color: var(--color-light-blue);
		margin: 8px 20px;
		height: 30px;
		border: 2px solid #5ec9ff;
		border-radius: 20px;
	}
</style>
