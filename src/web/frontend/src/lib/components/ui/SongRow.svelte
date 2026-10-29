<script>
	// The one song row (R2, docs/design/redesign-2026-10-27/SongRow.dc.html):
	// rank · cover · title (+ ✦ when the DJ picked it) · artist · reason ·
	// duration · Swap · +/✓. Lists add their own buttons through the `actions`
	// slot. Give it a `previewSong` and the cover previews that song (F2).
	import Icon from '../Icon.svelte';
	import Bars from './Bars.svelte';
	import { preview } from '$lib/preview.js';
	import { nameHue } from '$lib/dj/ambience.js';
	import { compactRows } from '$lib/settings.js';

	export let title = '';
	/** @type {string | string[]} */
	export let artists = [];
	export let image = '';
	export let reason = '';
	/** Off: the reason is only the row's tooltip (the Builder's dense list). */
	export let showReason = true;
	/** Milliseconds; shown when set. */
	export let duration = 0;
	/** @type {number | null} */
	export let index = null;
	export let compact = false;
	/** Linked or checked: tints the row. */
	export let selected = false;
	/** Picked by the DJ (✦). */
	export let dj = false;
	/** A status line in place of the reason, e.g. "Not on Spotify". */
	export let note = '';
	export let noteTone = 'muted';
	/** Not matched on Spotify: red note, Swap instead of +. */
	export let flagged = false;
	export let added = false;
	export let busy = false;
	/** @type {null | (() => void)} */
	export let onOpen = null;
	export let openLabel = '';
	/** @type {null | (() => void)} */
	export let onAdd = null;
	export let addLabel = 'Add to queue';
	/** @type {null | (() => void)} */
	export let onSwap = null;
	/** A Spotify track id: makes the row draggable onto a playlist. */
	export let dragId = '';
	/** The song to preview when the cover is clicked. Off when null.
	 * @type {null | {id: string, title: string, artists: string[], image?: string, isrc?: string | null}} */
	export let previewSong = null;

	// Compact rows (Settings) tighten every list; a list can also ask for it.
	$: previewing = !!previewSong && $preview?.song.id === previewSong.id;
	$: dense = compact || $compactRows;
	$: artistText = Array.isArray(artists) ? artists.join(', ') : artists;
	// A deliberate placeholder when a song has no art: a gradient from the
	// title's hue (the handoff's cover formula) with its initials.
	$: hue = nameHue(title + artistText);
	$: initials = title
		.replace(/\(.*?\)|\[.*?\]/g, '')
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((w) => w[0])
		.join('')
		.toUpperCase();
	$: clock = duration ? `${Math.floor(duration / 60000)}:${String(Math.round((duration % 60000) / 1000)).padStart(2, '0')}` : '';

	function onDragStart(e) {
		e.dataTransfer.setData('application/x-track-id', dragId);
		e.dataTransfer.setData('text/plain', dragId);
		e.dataTransfer.effectAllowed = 'copy';
	}
</script>

<div class="row" class:compact={dense} class:selected class:previewing class:openable={!!onOpen} title={reason || undefined} draggable={dragId ? 'true' : undefined} on:dragstart={dragId ? onDragStart : undefined}>
	<slot name="lead" />
	{#if index != null}<span class="rank mono">{index}</span>{/if}
	{#if previewSong}
		<button class="cover-btn" class:on={previewing} on:mousedown|preventDefault|stopPropagation
			on:click|stopPropagation={() => previewSong && preview.start(previewSong)} aria-label="{previewing ? 'Stop preview of' : 'Preview'} {title}" aria-pressed={previewing} title={previewing ? 'Stop preview' : 'Preview 15 seconds'}>
			{#if image}
				<img class="cover" src={image} alt="" loading="lazy" draggable="false" />
			{:else}
				<span class="cover blank mono" style:--h={hue} aria-hidden="true">{initials}</span>
			{/if}
			{#if previewing}
				<span class="bars"><Bars count={4} height={14} color="#fff" /></span>
			{:else}
				<span class="badge" aria-hidden="true"><Icon name="play" size={8} filled /></span>
			{/if}
		</button>
	{/if}
	<!-- A button only when the row opens something; otherwise plain content. -->
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<svelte:element this={onOpen ? 'button' : 'div'} class="main" on:click={onOpen} aria-label={onOpen ? openLabel || undefined : undefined}>
		{#if !previewSong}
			{#if image}
				<img class="cover" src={image} alt="" loading="lazy" draggable="false" />
			{:else}
				<span class="cover blank mono" style:--h={hue} aria-hidden="true">{initials}</span>
			{/if}
		{/if}
		<span class="text">
			<span class="title-line">
				<span class="title">{title}</span>
				{#if dj}<span class="dj" title="Picked by the DJ" aria-label="(picked by the DJ)">✦</span>{/if}
			</span>
			<span class="artist">{artistText}</span>
			{#if flagged}
				<span class="note danger">Not found on Spotify</span>
			{:else if note}
				<span class="note {noteTone}" role="status">{note}</span>
			{:else if reason && showReason}
				<span class="reason">{reason}</span>
			{/if}
		</span>
	</svelte:element>
	<slot name="actions" />
	{#if clock}<span class="dur mono">{clock}</span>{/if}
	{#if flagged && onSwap}
		<button class="swap" on:click|stopPropagation={onSwap}>Swap</button>
	{:else if onAdd && !flagged}
		<button
			class="add"
			class:added
			on:click|stopPropagation={onAdd}
			disabled={added || busy}
			aria-busy={busy}
			aria-label={added ? `${title} added` : `${addLabel}: ${title}`}
			title={added ? 'Added' : addLabel}
		>
			{#if busy}<span class="spinner" aria-hidden="true" />{:else}<Icon name={added ? 'check' : 'plus'} size={15} />{/if}
		</button>
	{/if}
</div>

<style>
	.row {
		display: flex;
		align-items: center;
		gap: 12px;
		min-width: 0;
		padding: 8px 10px;
		border-radius: var(--radius-row);
		transition: background-color var(--transition);
	}

	.row:hover {
		background: var(--hover);
	}

	.row.selected {
		background: rgba(var(--accent-rgb), 0.08);
	}

	.row.previewing {
		background: rgba(var(--accent-rgb), 0.08);
	}

	.row.previewing .title {
		color: var(--accent-tint-text);
	}

	.row[draggable='true'] {
		cursor: grab;
	}

	.row.compact {
		gap: 10px;
		padding: 5px 8px;
	}

	.rank {
		flex: none;
		width: 20px;
		text-align: right;
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		color: var(--text-subtle);
	}

	.main {
		flex: 1;
		min-width: 0;
		display: flex;
		align-items: center;
		gap: inherit;
		padding: 0;
		border: none;
		background: none;
		color: inherit;
		font: inherit;
		text-align: left;
		white-space: normal;
	}

	button.main {
		cursor: pointer;
		border-radius: 6px;
	}

	.cover {
		flex: none;
		width: 40px;
		height: 40px;
		border-radius: 7px;
		object-fit: cover;
		background: var(--surface-2);
		box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
		transition: filter var(--transition);
	}

	.compact .cover {
		width: 34px;
		height: 34px;
	}

	/* The cover as the preview button: a play badge in its corner; while playing, an accent ring and white bars. */
	.cover-btn {
		position: relative;
		flex: none;
		padding: 0;
		border: none;
		border-radius: 7px;
		background: none;
		cursor: pointer;
		transition: box-shadow var(--transition);
	}

	.cover-btn:hover .cover {
		filter: brightness(0.85);
	}

	.cover-btn.on {
		box-shadow: 0 0 0 2px var(--accent);
	}

	.badge {
		position: absolute;
		right: -3px;
		bottom: -3px;
		width: 16px;
		height: 16px;
		display: grid;
		place-items: center;
		padding-left: 1px;
		border-radius: 50%;
		background: var(--accent);
		color: var(--accent-on);
		box-shadow: 0 0 0 2px var(--surface-0);
	}

	.bars {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: center;
		border-radius: 7px;
		background: rgba(0, 0, 0, 0.5);
	}

	.cover.blank {
		display: grid;
		place-items: center;
		background: linear-gradient(140deg, oklch(0.66 0.12 var(--h)), oklch(0.32 0.08 calc(var(--h) + 45)));
		font-size: calc(11px * var(--text-scale, 1));
		font-weight: 600;
		letter-spacing: 0.02em;
		color: rgba(255, 255, 255, 0.82);
	}

	button.main:hover .cover {
		filter: brightness(0.85);
	}

	.text {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.title-line {
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
	}

	.title,
	.artist {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		line-height: 1.3;
	}

	.title {
		font-size: calc(14px * var(--text-scale, 1));
		font-weight: 500;
	}

	.artist {
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.compact .title {
		font-size: calc(13px * var(--text-scale, 1));
	}

	.compact .artist {
		font-size: calc(12px * var(--text-scale, 1));
	}

	.dj {
		flex: none;
		font-size: calc(11px * var(--text-scale, 1));
		color: var(--accent);
	}

	.reason,
	.note {
		margin-top: 2px;
		font-size: calc(12px * var(--text-scale, 1));
		line-height: 1.4;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		text-wrap: pretty;
	}

	.reason {
		color: rgba(243, 243, 245, 0.5);
	}

	.compact .reason,
	.compact .note {
		-webkit-line-clamp: 1;
	}

	.note.muted {
		color: var(--text-subtle);
	}

	.note.warning {
		color: var(--warning);
	}

	.note.danger {
		font-weight: 500;
		color: var(--danger);
	}

	.dur {
		flex: none;
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.add,
	.swap {
		flex: none;
		cursor: pointer;
		transition: border-color var(--transition), background-color var(--transition), color var(--transition);
	}

	.add {
		width: 32px;
		height: 32px;
		display: grid;
		place-items: center;
		padding: 0;
		border-radius: 8px;
		border: 1px solid rgba(255, 255, 255, 0.08);
		background: transparent;
		color: rgba(243, 243, 245, 0.75);
	}

	.compact .add {
		width: 28px;
		height: 28px;
	}

	.add:hover:not(:disabled) {
		border-color: var(--accent-tint-border);
	}

	.add.added {
		background: rgba(var(--accent-rgb), 0.14);
		color: var(--accent);
		cursor: default;
	}

	.add:disabled:not(.added) {
		opacity: 0.6;
		cursor: default;
	}

	.swap {
		height: 30px;
		padding: 0 12px;
		border-radius: 8px;
		border: 1px solid rgba(255, 122, 122, 0.35);
		background: transparent;
		color: var(--danger-text);
		font: inherit;
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
	}

	/* Rows' extra buttons (heart, ⋯, remove) share the + button's size. */
	.row :global(.row-btn) {
		flex: none;
		width: 32px;
		height: 32px;
		display: grid;
		place-items: center;
		padding: 0;
		border: none;
		border-radius: 8px;
		background: none;
		color: var(--text-subtle);
		cursor: pointer;
		transition: background-color var(--transition), color var(--transition);
	}

	.compact :global(.row-btn) {
		width: 28px;
		height: 28px;
	}

	.row :global(.row-btn:hover:not(:disabled)) {
		background: var(--hover);
		color: var(--text-primary);
	}

	.spinner {
		width: 14px;
		height: 14px;
		border-radius: 50%;
		border: 2px solid rgba(255, 255, 255, 0.2);
		border-top-color: var(--accent);
		animation: bbspin 0.7s linear infinite;
	}
</style>
