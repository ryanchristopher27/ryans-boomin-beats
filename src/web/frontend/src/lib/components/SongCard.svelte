<script>
	// A playlist or top-track song: the shared SongRow with Like, Explore and
	// "add to a playlist" (R2). Clicking the row checks it for bulk actions.
	import { playlistsPanelOpen, pendingAdd } from '../../stores.js';
	import SongRow from './ui/SongRow.svelte';
	import Icon from './Icon.svelte';

	export let song;
	export let checked = false;
	export let onToggle = (id, checked) => {};
	/** @type {null | ((song: any) => void)} */
	export let onExplore = null;
	export let saved = false;
	/** @type {null | ((id: string, saved: boolean) => void)} */
	export let onSaveToggle = null;
	/** @type {number | null} */
	export let index = null;
	export let compact = false;

	$: s = song.spotify;

	// The Playlists panel's "pick a playlist" mode adds this song to the tile
	// you choose (or to a new playlist); it opens just for this when closed.
	function addToPlaylist() {
		const wasOpen = $playlistsPanelOpen;
		$pendingAdd = { trackIds: [s.id], label: s.title, transient: !wasOpen };
		$playlistsPanelOpen = true;
	}
</script>

<SongRow
	title={s.title}
	artists={s.artists}
	image={s.image}
	reason={song.reason ?? ''}
	duration={s.duration_ms}
	{index}
	{compact}
	selected={checked}
	dragId={s.id}
	onOpen={() => onToggle(s.id, !checked)}
	openLabel="{checked ? 'Unselect' : 'Select'} {s.title}"
	onAdd={addToPlaylist}
	addLabel="Add to a playlist"
>
	<svelte:fragment slot="actions">
		{#if onSaveToggle}
			<button
				class="row-btn heart"
				class:saved
				on:click|stopPropagation={() => onSaveToggle?.(s.id, !saved)}
				aria-pressed={saved}
				aria-label={saved ? `Remove ${s.title} from Liked Songs` : `Save ${s.title} to Liked Songs`}
				title={saved ? 'Remove from Liked Songs' : 'Save to Liked Songs'}
			>
				<Icon name="heart" size={15} filled={saved} />
			</button>
		{/if}
		{#if onExplore}
			<button
				class="row-btn"
				on:click|stopPropagation={() => onExplore?.({ title: s.title, artists: s.artists, id: s.id, image: s.image })}
				aria-label="Explore {s.title}"
				title="Explore this song"
			>
				<Icon name="arrow" size={15} />
			</button>
		{/if}
	</svelte:fragment>
</SongRow>

<style>
	.heart.saved {
		color: var(--accent);
	}
</style>
