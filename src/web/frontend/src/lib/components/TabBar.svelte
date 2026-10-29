<script>
	// Phone-only bottom tab bar (F5): the header nav's four pages, thumb-reachable.
	import { page } from '../../stores.js';
	import { navLinks } from '$lib/nav.js';
	import Icon from './Icon.svelte';
	import { getDJ } from '$lib/dj/instance.js';

	const player = getDJ()?.player;
	$: playing = !!($player?.state?.active && $player.state.is_playing);
</script>

<nav aria-label="Main">
	{#each navLinks as link}
		<a class:active={$page === link.page} aria-current={$page === link.page ? 'page' : undefined} href={link.href}>
			<Icon name={link.icon} size={20} />
			<span>{link.label}</span>
			{#if link.page === 'DJ' && playing}<i class="live" aria-label="(playing)" />{/if}
		</a>
	{/each}
</nav>

<style>
	nav {
		position: fixed;
		left: 0;
		right: 0;
		bottom: 0;
		z-index: 45;
		height: var(--tab-h);
		display: none;
		padding-bottom: env(safe-area-inset-bottom, 0px);
		border-top: 1px solid var(--border-subtle);
		background: rgba(13, 13, 16, 0.92);
		-webkit-backdrop-filter: blur(20px);
		backdrop-filter: blur(20px);
	}

	:global([data-bp='phone']) nav {
		display: flex;
	}

	a {
		position: relative;
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 3px;
		color: var(--text-muted);
		font-size: calc(10.5px * var(--text-scale, 1));
		font-weight: 500;
		transition: color var(--transition);
	}

	a.active {
		color: var(--text-primary);
	}

	a.active :global(.icon) {
		color: var(--accent);
	}

	.live {
		position: absolute;
		top: 8px;
		left: calc(50% + 8px);
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--accent);
	}
</style>
