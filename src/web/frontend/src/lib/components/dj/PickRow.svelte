<script>
	import Icon from '../Icon.svelte';
	import { asSong, djContext } from './context.js';

	/** @type {any} */
	export let dj;
	/** @type {{id: string, title: string, artists: string[], image: string, reason: string}} */
	export let pick;
	export let queued = false;

	const { selected } = djContext();
	const menuId = `pick-menu-${Math.random().toString(36).slice(2)}`;
	let menu;
	let anchor;
	/** idle | adding | added | not_on_spotify | explicit | unavailable */
	let status = 'idle';
	$: done = queued || status === 'added';
	const MISS = {
		not_on_spotify: 'Not on Spotify',
		explicit: 'Explicit version only',
		unavailable: "Couldn't add that right now"
	};

	// The menu lives in the top layer (popover), so the widget's scroll box can't
	// clip it; place it under the button when it opens.
	function place(e) {
		if (e.newState !== 'open') return;
		const r = anchor.getBoundingClientRect();
		menu.style.top = `${r.bottom + 4}px`;
		menu.style.left = `${Math.max(8, r.right - menu.offsetWidth)}px`;
	}

	async function add() {
		status = 'adding';
		const r = await dj.addPick(pick);
		status = r.ok ? 'added' : r.reason;
	}

	function avoid(what) {
		menu.hidePopover();
		if (what === 'song') dj.avoidTrack(pick);
		else dj.avoidArtist(pick.artists[0]);
		dj.loadSuggestions(undefined, true);
	}
</script>

<div class="pick" class:selected={$selected?.id === pick.id}>
	<button class="select" on:click={() => selected.set(asSong(pick))} aria-label="Show the profile of {pick.title}">
		<img src={pick.image} alt="" width="44" height="44" loading="lazy" />
		<span class="text">
			<span class="title">{pick.title}</span>
			<span class="artist">{pick.artists.join(', ')}</span>
			{#if MISS[status]}
				<span class="miss" role="status">{MISS[status]}</span>
			{:else}
				<span class="reason" title={pick.reason}>{pick.reason}</span>
			{/if}
		</span>
	</button>
	<button class="icon-btn" bind:this={anchor} popovertarget={menuId} aria-label="More options for {pick.title}" title="More options">
		<Icon name="dots" size={18} />
	</button>
	<button
		class="icon-btn add"
		class:done
		on:click={add}
		disabled={done || status === 'adding' || status === 'not_on_spotify' || status === 'explicit'}
		aria-busy={status === 'adding'}
		aria-label={done ? `${pick.title} is queued` : status === 'adding' ? `Adding ${pick.title}` : `Queue ${pick.title}`}
	>
		{#if status === 'adding'}
			<span class="spinner" aria-hidden="true" />
		{:else}
			<Icon name={done ? 'check' : 'plus'} size={18} />
		{/if}
	</button>
	<div class="menu" id={menuId} popover="auto" bind:this={menu} on:toggle={place}>
		<button on:click={() => avoid('song')}>Never suggest this song</button>
		{#if pick.artists[0]}<button on:click={() => avoid('artist')}>Never suggest {pick.artists[0]}</button>{/if}
	</div>
</div>

<style>
	.pick {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto auto;
		align-items: start;
		gap: 4px;
		padding: 6px 0;
		border-radius: 6px;
	}

	/* Linking: the row the Song profile is showing. */
	.selected {
		background: rgba(var(--accent-rgb), 0.1);
	}

	.select {
		display: grid;
		grid-template-columns: 44px minmax(0, 1fr);
		gap: 12px;
		padding: 4px;
		border: none;
		background: none;
		color: inherit;
		font: inherit;
		text-align: left;
		cursor: pointer;
		border-radius: 6px;
		min-width: 0;
	}

	.text {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	img {
		border-radius: 4px;
		object-fit: cover;
		background: var(--surface-2);
	}

	.title {
		font-size: 14px;
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.artist {
		font-size: 13px;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.reason {
		margin-top: 3px;
		font-size: 13px;
		line-height: 1.4;
		color: var(--text-muted);
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.miss {
		margin-top: 3px;
		font-size: 13px;
		color: var(--warning);
	}

	.spinner {
		width: 16px;
		height: 16px;
		border-radius: 50%;
		border: 2px solid rgba(255, 255, 255, 0.2);
		border-top-color: var(--accent);
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.spinner {
			animation-duration: 2.4s;
		}
	}

	.add.done {
		color: var(--accent);
		opacity: 1;
	}

	.menu {
		position: fixed;
		inset: auto;
		margin: 0;
		padding: 4px;
		min-width: 200px;
		background: var(--surface-2);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
	}

	.menu button {
		display: block;
		width: 100%;
		text-align: left;
		padding: 8px 10px;
		border: none;
		background: none;
		color: inherit;
		font: inherit;
		font-size: 14px;
		border-radius: 6px;
		cursor: pointer;
	}

	.menu button:hover,
	.menu button:focus-visible {
		background: rgba(255, 255, 255, 0.08);
	}
</style>
