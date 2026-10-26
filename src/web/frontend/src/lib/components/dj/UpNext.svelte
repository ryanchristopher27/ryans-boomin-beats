<script>
	import { flip } from 'svelte/animate';
	import SongSearch from '$lib/components/SongSearch.svelte';
	import Icon from './Icon.svelte';

	/** @type {any} */
	export let dj;
	export let adding = false;

	const { doc, sync } = dj;
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
			<SongSearch placeholder="Add a song…" onSelect={(t) => dj.add(t)} />
		</div>
	{/if}

	{#if q.sent.length}
		<h3>In Spotify</h3>
		<ul class="list">
			{#each q.sent as item (item.id)}
				<li class="row" class:skipping={item.skipOnArrival} animate:flip={anim}>
					<img src={item.image} alt="" width="36" height="36" />
					<div class="text">
						<p class="title">{item.title}{#if item.addedByDJ}<span class="dj" title="Added by the DJ"><Icon name="sparkle" size={12} label="Added by the DJ" /></span>{/if}</p>
						<p class="artist">{item.skipOnArrival ? 'Skipping when it comes up' : item.artists.join(', ')}</p>
					</div>
					{#if !item.skipOnArrival}
						<button class="icon-btn" on:click={() => dj.playLater(item)} aria-label="Play {item.title} later" title="Play later"><Icon name="later" size={16} /></button>
						<button class="icon-btn" on:click={() => dj.removeSent(item.id)} aria-label="Remove {item.title}" title="Remove"><Icon name="x" size={16} /></button>
					{/if}
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
					<button class="icon-btn grip" data-row={item.id} on:keydown={(e) => onKey(e, i)} aria-label="Reorder {item.title}" aria-describedby="reorder-hint">
						<Icon name="grip" size={14} />
					</button>
					<img src={item.image} alt="" width="36" height="36" />
					<div class="text">
						<p class="title">{item.title}{#if item.addedByDJ}<span class="dj" title="Added by the DJ"><Icon name="sparkle" size={12} label="Added by the DJ" /></span>{/if}</p>
						<p class="artist">{item.artists.join(', ')}</p>
					</div>
					<button class="icon-btn" on:click={() => dj.removeUpcoming(item.id)} aria-label="Remove {item.title}" title="Remove"><Icon name="x" size={16} /></button>
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
		padding: 8px 16px 12px;
	}

	.search {
		padding-top: 10px;
	}

	h3 {
		margin: 12px 0 4px;
		font-size: 13px;
		font-weight: 600;
		color: var(--text-muted);
	}

	.list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.row {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 4px;
		border-radius: 6px;
		border-top: 1px solid transparent;
	}

	.row + .row {
		border-top-color: var(--border-subtle);
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

	.skipping .title {
		text-decoration: line-through;
	}

	.grip {
		width: 22px;
		color: var(--text-subtle);
		cursor: grab;
	}

	img {
		border-radius: 4px;
		object-fit: cover;
		background: var(--surface-2);
		flex: none;
	}

	.text {
		flex: 1;
		min-width: 0;
	}

	p {
		margin: 0;
	}

	.title {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 14px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.artist {
		font-size: 12px;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.dj {
		color: var(--accent);
		display: inline-flex;
	}

	.hint {
		margin: 8px 0 0;
		font-size: 12px;
		line-height: 1.45;
		color: var(--text-muted);
	}
</style>
