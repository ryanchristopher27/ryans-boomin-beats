<script>
	import Icon from '../Icon.svelte';
	import SongRow from '../ui/SongRow.svelte';
	import { asSong, djContext } from './context.js';

	/** @type {any} */
	export let dj;
	/** @type {{id: string, title: string, artists: string[], image: string, reason: string}} */
	export let pick;
	export let queued = false;
	export let compact = false;

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

<SongRow
	title={pick.title}
	artists={pick.artists}
	image={pick.image}
	reason={pick.reason}
	{compact}
	previewSong={pick}
	selected={$selected?.id === pick.id}
	note={MISS[status] ?? ''}
	noteTone="warning"
	onOpen={() => selected.set(asSong(pick))}
	openLabel="Show the profile of {pick.title}"
	onAdd={status === 'not_on_spotify' || status === 'explicit' ? null : add}
	added={done}
	busy={status === 'adding'}
	addLabel="Queue"
>
	<svelte:fragment slot="actions">
		<button class="row-btn" bind:this={anchor} popovertarget={menuId} aria-label="More options for {pick.title}" title="More options">
			<Icon name="dots" size={16} />
		</button>
		<div class="menu" id={menuId} popover="auto" bind:this={menu} on:toggle={place}>
			<button on:click={() => avoid('song')}>Never suggest this song</button>
			{#if pick.artists[0]}<button on:click={() => avoid('artist')}>Never suggest {pick.artists[0]}</button>{/if}
		</div>
	</svelte:fragment>
</SongRow>

<style>
	.menu {
		position: fixed;
		inset: auto;
		margin: 0;
		padding: 4px;
		min-width: 200px;
		background: var(--popover);
		-webkit-backdrop-filter: blur(30px);
		backdrop-filter: blur(30px);
		color: var(--text-primary);
		border: 1px solid var(--border-control);
		border-radius: 12px;
		box-shadow: var(--shadow-pop);
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
		font-size: calc(13px * var(--text-scale, 1));
		border-radius: 8px;
		cursor: pointer;
	}

	.menu button:hover,
	.menu button:focus-visible {
		background: var(--hover);
	}
</style>
