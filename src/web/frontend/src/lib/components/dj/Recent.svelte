<script>
	// Recently played (W4): this session's history, synced from the driving
	// device. Click a row to see its profile; + queues it again.
	import { flip } from 'svelte/animate';
	import SongRow from '../ui/SongRow.svelte';
	import { asSong, djContext } from './context.js';

	/** @type {any} */
	export let dj;
	const { doc } = dj;
	const { selected } = djContext();
	$: recent = $doc.recent;
</script>

<div class="recent">
	{#if recent.length}
		<ul>
			{#each recent as t (t.id)}
				<li animate:flip={{ duration: 200 }}>
					<SongRow
						compact
						title={t.title}
						artists={t.artists}
						image={t.image}
						selected={$selected?.id === t.id}
						onOpen={() => selected.set(asSong(t))}
						openLabel="Show the profile of {t.title}"
						onAdd={() => dj.add(t)}
						addLabel="Queue again"
					/>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="empty">Songs played this session show up here.</p>
	{/if}
</div>

<style>
	.recent {
		padding: 6px 10px 12px;
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.empty {
		margin: 8px 6px 0;
		font-size: calc(13px * var(--text-scale, 1));
		line-height: 1.45;
		color: var(--text-muted);
	}
</style>
