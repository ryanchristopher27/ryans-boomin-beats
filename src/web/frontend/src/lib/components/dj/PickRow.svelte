<script>
	import Icon from './Icon.svelte';

	/** @type {any} */
	export let dj;
	/** @type {{id: string, title: string, artists: string[], image: string, reason: string}} */
	export let pick;
	export let queued = false;

	const menuId = `pick-menu-${Math.random().toString(36).slice(2)}`;
	let menu;
	let anchor;
	let justAdded = false;

	// The menu lives in the top layer (popover), so the widget's scroll box can't
	// clip it; place it under the button when it opens.
	function place(e) {
		if (e.newState !== 'open') return;
		const r = anchor.getBoundingClientRect();
		menu.style.top = `${r.bottom + 4}px`;
		menu.style.left = `${Math.max(8, r.right - menu.offsetWidth)}px`;
	}

	async function add() {
		justAdded = true;
		await dj.add(pick);
	}

	function avoid(what) {
		menu.hidePopover();
		if (what === 'song') dj.avoidTrack(pick);
		else dj.avoidArtist(pick.artists[0]);
		dj.loadSuggestions(undefined, true);
	}
</script>

<div class="pick">
	<img src={pick.image} alt="" width="44" height="44" loading="lazy" />
	<div class="text">
		<p class="title">{pick.title}</p>
		<p class="artist">{pick.artists.join(', ')}</p>
		<p class="reason" title={pick.reason}>{pick.reason}</p>
	</div>
	<button class="icon-btn" bind:this={anchor} popovertarget={menuId} aria-label="More options for {pick.title}" title="More options">
		<Icon name="dots" size={18} />
	</button>
	<button class="icon-btn add" class:done={queued || justAdded} on:click={add} disabled={queued || justAdded} aria-label={queued || justAdded ? `${pick.title} is queued` : `Queue ${pick.title}`}>
		<Icon name={queued || justAdded ? 'check' : 'plus'} size={18} />
	</button>
	<div class="menu" id={menuId} popover="auto" bind:this={menu} on:toggle={place}>
		<button on:click={() => avoid('song')}>Never suggest this song</button>
		{#if pick.artists[0]}<button on:click={() => avoid('artist')}>Never suggest {pick.artists[0]}</button>{/if}
	</div>
</div>

<style>
	.pick {
		display: grid;
		grid-template-columns: 44px minmax(0, 1fr) auto auto;
		align-items: start;
		gap: 4px 12px;
		padding: 10px 0;
	}

	img {
		border-radius: 4px;
		object-fit: cover;
		background: var(--surface-2);
	}

	p {
		margin: 0;
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
