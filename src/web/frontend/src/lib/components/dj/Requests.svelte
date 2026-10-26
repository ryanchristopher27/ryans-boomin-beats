<script>
	import { flip } from 'svelte/animate';

	/** @type {any} */
	export let dj;
	const { doc, sync } = dj;
	$: requests = $doc.queue.requests;
</script>

<div class="requests">
	{#if requests.length}
		<ul>
			{#each requests as r (r.id)}
				<li animate:flip={{ duration: 200 }}>
					<img src={r.image} alt="" width="36" height="36" />
					<div class="text">
						<p class="title">{r.title}</p>
						<p class="artist">{r.artists.join(', ')}</p>
					</div>
					<div class="actions">
						<button class="btn small" on:click={() => dj.keep(r)} title="Leave it where Spotify put it">Keep</button>
						<button class="btn small" on:click={() => dj.later(r)} title="Move it to the end of Up next">Later</button>
						<button class="btn small danger" on:click={() => dj.decline(r)} title="Skip it when it comes up">Decline</button>
					</div>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="empty">
			Requests from your Spotify queue show up here.
			{#if !$sync.isPrimary}The driving device picks them up.{/if}
		</p>
	{/if}
</div>

<style>
	.requests {
		padding: 4px 16px 12px;
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	li {
		display: grid;
		grid-template-columns: 36px minmax(0, 1fr);
		gap: 6px 10px;
		padding: 10px 0;
	}

	li + li {
		border-top: 1px solid var(--border-subtle);
	}

	img {
		border-radius: 4px;
		background: var(--surface-2);
		object-fit: cover;
	}

	p {
		margin: 0;
	}

	.title {
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

	.actions {
		grid-column: 2;
		display: flex;
		gap: 6px;
	}

	.empty {
		margin: 16px 0;
		font-size: 13px;
		line-height: 1.5;
		color: var(--text-muted);
	}
</style>
