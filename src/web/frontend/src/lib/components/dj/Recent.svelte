<script>
	// Recently played (W4): this session's history, synced from the driving
	// device. Click a row to see its profile; + queues it again.
	import { flip } from 'svelte/animate';
	import Icon from '../Icon.svelte';
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
				<li animate:flip={{ duration: 200 }} class:selected={$selected?.id === t.id}>
					<button class="select" on:click={() => selected.set(asSong(t))} aria-label="Show the profile of {t.title}">
						<img src={t.image} alt="" width="36" height="36" loading="lazy" />
						<span class="text">
							<span class="title">{t.title}</span>
							<span class="artist">{t.artists.join(', ')}</span>
						</span>
					</button>
					<button class="icon-btn" on:click={() => dj.add(t)} aria-label="Queue {t.title} again" title="Queue again"><Icon name="plus" size={16} /></button>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="empty">Songs played this session show up here.</p>
	{/if}
</div>

<style>
	.recent {
		padding: 6px 12px 12px;
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	li {
		display: flex;
		align-items: center;
		gap: 4px;
		border-radius: 6px;
	}

	li + li {
		border-top: 1px solid var(--border-subtle);
	}

	.select {
		flex: 1;
		min-width: 0;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 4px;
		border: none;
		background: none;
		color: inherit;
		font: inherit;
		text-align: left;
		cursor: pointer;
		border-radius: 6px;
	}

	.selected {
		background: rgba(var(--accent-rgb), 0.1);
	}

	img {
		border-radius: 4px;
		object-fit: cover;
		background: var(--surface-2);
		flex: none;
	}

	.text {
		min-width: 0;
		display: flex;
		flex-direction: column;
	}

	.title,
	.artist {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.title {
		font-size: 14px;
	}

	.artist {
		font-size: 12px;
		color: var(--text-muted);
	}

	.empty {
		margin: 12px 4px;
		font-size: 13px;
		color: var(--text-muted);
	}
</style>
