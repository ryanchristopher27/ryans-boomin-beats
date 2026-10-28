<script>
	import { flip } from 'svelte/animate';
	import SongSearch from '$lib/components/SongSearch.svelte';
	import Icon from '../Icon.svelte';
	import SongRow from '../ui/SongRow.svelte';
	import { asSong, djContext, offerUndo } from './context.js';

	/** @type {any} */
	export let dj;
	export let adding = false;

	const { doc, sync } = dj;
	const ctx = djContext();
	const { selected } = ctx;

	// Search results come from Deezer (Q3): adding one looks it up on Spotify.
	let searchMiss = '';
	async function pickSong(t) {
		searchMiss = '';
		const r = await dj.addPick(t);
		if (!r.ok) searchMiss = r.reason === 'not_on_spotify' ? `${t.title} isn't on Spotify.` : r.reason === 'explicit' ? `Only an explicit version of ${t.title} is on Spotify.` : "Couldn't add that right now.";
	}

	function remove(item, i) {
		dj.removeUpcoming(item.id);
		offerUndo(`Removed ${item.title}.`, () => dj.restoreUpcoming(item, i));
	}
	$: q = $doc.queue;
	const reduced = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
	const anim = { duration: reduced ? 0 : 200 };

	let dragFrom = null;
	let dropAt = null;

	function onDrop(i) {
		if (dragFrom !== null && dragFrom !== i) dj.moveUpcoming(dragFrom, i);
		dragFrom = dropAt = null;
	}

	/** Keyboard reorder: Alt+Up / Alt+Down on a focused row. */
	function onKey(e, i) {
		if (!e.altKey || (e.key !== 'ArrowUp' && e.key !== 'ArrowDown')) return;
		e.preventDefault();
		const to = e.key === 'ArrowUp' ? i - 1 : i + 1;
		if (to < 0 || to >= q.upcoming.length) return;
		dj.moveUpcoming(i, to);
		requestAnimationFrame(() => /** @type {HTMLElement | null} */ (document.querySelector(`[data-row="${q.upcoming[to]?.id}"]`))?.focus());
	}
</script>

<div class="upnext">
	{#if adding}
		<div class="search">
			<SongSearch placeholder="Add a song…" onSelect={pickSong} />
			{#if searchMiss}<p class="hint warn" role="status">{searchMiss}</p>{/if}
		</div>
	{/if}

	{#if q.sent.length}
		<h3>In Spotify</h3>
		<ul class="list">
			{#each q.sent as item (item.id)}
				<li class="row" class:skipping={item.skipOnArrival} animate:flip={anim}>
					<SongRow
						compact
						title={item.title}
						artists={item.artists}
						image={item.image}
						dj={item.addedByDJ}
						note={item.skipOnArrival ? 'Skipping when it comes up' : ''}
					>
						<svelte:fragment slot="actions">
							{#if !item.skipOnArrival}
								<button class="row-btn" on:click={() => dj.playLater(item)} aria-label="Play {item.title} later" title="Play later"><Icon name="later" size={15} /></button>
								<button class="row-btn" on:click={() => dj.removeSent(item.id)} aria-label="Remove {item.title}" title="Remove"><Icon name="x" size={15} /></button>
							{/if}
						</svelte:fragment>
					</SongRow>
				</li>
			{/each}
		</ul>
	{/if}

	<!-- Subheadings only when both parts show; the widget title already says "Up next". -->
	{#if q.sent.length}<h3>Then</h3>{/if}
	{#if q.upcoming.length}
		<ul class="list">
			{#each q.upcoming as item, i (item.id)}
				<li
					class="row"
					class:drop-target={dropAt === i && dragFrom !== i}
					animate:flip={anim}
					draggable="true"
					on:dragstart={() => (dragFrom = i)}
					on:dragover|preventDefault={() => (dropAt = i)}
					on:drop|preventDefault={() => onDrop(i)}
					on:dragend={() => (dragFrom = dropAt = null)}
				>
					<SongRow
						compact
						title={item.title}
						artists={item.artists}
						image={item.image}
						dj={item.addedByDJ}
						selected={$selected?.id === item.trackID}
						onOpen={() => selected.set(asSong(item))}
						openLabel="Show the profile of {item.title}"
					>
						<button slot="lead" class="row-btn grip" data-row={item.id} on:keydown={(e) => onKey(e, i)} aria-label="Reorder {item.title}" aria-describedby="reorder-hint">
							<Icon name="grip" size={14} />
						</button>
						<svelte:fragment slot="actions">
							<button class="row-btn" on:click={() => remove(item, i)} aria-label="Remove {item.title}" title="Remove"><Icon name="x" size={15} /></button>
						</svelte:fragment>
					</SongRow>
				</li>
			{/each}
		</ul>
		<p class="hint" id="reorder-hint">Drag to reorder, or focus a song's handle and press Alt+Up or Alt+Down.</p>
	{:else}
		<p class="hint">
			{#if $sync.isPrimary}Add a song or queue a move. {$doc.options.mode === 'driver' || $doc.options.mode === 'autofill' ? 'The DJ fills in when this runs dry.' : ''}{:else}Songs you add here are sent by the driving device.{/if}
		</p>
	{/if}
</div>

<style>
	.upnext {
		padding: 8px 10px 12px;
	}

	.search {
		padding: 10px 6px 0;
	}

	h3 {
		margin: 12px 8px 4px;
		font-family: var(--font-mono);
		font-size: calc(11px * var(--text-scale, 1));
		font-weight: 500;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--text-subtle);
	}

	.list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.row {
		border-radius: var(--radius-row);
	}

	.row[draggable='true'] {
		cursor: grab;
	}

	.drop-target {
		box-shadow: inset 0 2px 0 var(--accent);
	}

	.skipping {
		opacity: 0.55;
	}

	.grip {
		width: 20px !important;
		margin-right: -4px;
		cursor: grab !important;
	}

	.hint.warn {
		color: var(--warning);
	}

	.hint {
		margin: 8px 8px 0;
		font-size: calc(12px * var(--text-scale, 1));
		line-height: 1.45;
		color: var(--text-muted);
	}
</style>
