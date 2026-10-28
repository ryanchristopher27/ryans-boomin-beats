<script>
	// Guest requests (DJ5, restyled R6): songs that showed up in the Spotify
	// queue without the app adding them. Keep / Later / Decline each one.
	import { flip } from 'svelte/animate';
	import { offerUndo } from './context.js';
	import SongRow from '../ui/SongRow.svelte';
	import Icon from '../Icon.svelte';

	/** @type {any} */
	export let dj;
	const { doc, sync } = dj;

	function decline(r) {
		dj.decline(r);
		offerUndo(`Declined ${r.title}.`, () => dj.undoDecline(r));
	}
	$: requests = $doc.queue.requests;
</script>

<div class="requests">
	{#if requests.length}
		<ul>
			{#each requests as r (r.id)}
				<li animate:flip={{ duration: 200 }}>
					<SongRow compact title={r.title} artists={r.artists} image={r.image}>
						<svelte:fragment slot="actions">
							<button class="btn primary keep" on:click={() => dj.keep(r)} title="Leave it where Spotify put it">Keep</button>
							<button class="act" on:click={() => dj.later(r)} aria-label="Play {r.title} later" title="Move it to the end of Up next"><Icon name="later" size={14} /></button>
							<button class="act decline" on:click={() => decline(r)} aria-label="Decline {r.title}" title="Skip it when it comes up"><Icon name="x" size={14} /></button>
						</svelte:fragment>
					</SongRow>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="empty">
			Guests add songs from their own Spotify queue. They show up here.
			{#if !$sync.isPrimary}The driving device picks them up.{/if}
		</p>
	{/if}
</div>

<style>
	.requests {
		padding: 6px;
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.keep {
		flex: none;
		height: 28px;
		padding: 0 10px;
		border-radius: 7px;
		font-size: 12px;
	}

	.act {
		flex: none;
		width: 28px;
		height: 28px;
		display: grid;
		place-items: center;
		padding: 0;
		border: 1px solid var(--border-control);
		border-radius: 7px;
		background: transparent;
		color: var(--text-primary);
		cursor: pointer;
		transition: background-color var(--transition);
	}

	.act:hover {
		background: var(--hover);
	}

	.decline {
		border-color: rgba(255, 122, 122, 0.3);
		color: var(--danger-text);
	}

	.empty {
		margin: 0;
		padding: 8px 10px;
		font-size: 13px;
		line-height: 1.5;
		color: rgba(243, 243, 245, 0.5);
	}
</style>
