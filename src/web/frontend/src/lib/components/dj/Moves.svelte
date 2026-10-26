<script>
	// The Next moves widget, and (with `kind`) a single-move widget. All of them
	// read the one `suggestions` store: one LLM call per track, however many
	// move widgets are on screen.
	import { flip } from 'svelte/animate';
	import { llmSettingsOpen } from '../../../stores.js';
	import { MOVE_SUMMARY, moveLabel } from '$lib/dj/layout.js';
	import Icon from './Icon.svelte';
	import PickRow from './PickRow.svelte';

	/** @type {any} */
	export let dj;
	/** @type {string | null} */
	export let kind = null;

	const { suggestions, doc, player } = dj;

	$: s = $suggestions;
	$: moves = kind ? s.moves.filter((m) => m.move === kind) : s.moves;
	$: queued = new Set([...$doc.queue.sent, ...$doc.queue.upcoming].map((i) => i.trackID));
	$: hasTrack = !!$player.state?.track;
	$: goal = $doc.options.goal;

	function missingCopy(k) {
		if (k === 'toward') return goal?.kind === 'drift' ? 'The goal is Drift; add the Drift move instead.' : 'Set a goal to get Toward picks.';
		if (k === 'drift') return 'Set the goal to Drift to get these picks.';
		return 'No picks for this move this time.';
	}
</script>

<div class="moves">
	{#if !hasTrack}
		<p class="empty">Moves show up once a song is playing.</p>
	{:else if s.status === 'needsKey'}
		<div class="empty">
			<p>Add an AI key in Settings to get suggestions.</p>
			<button class="btn" on:click={() => ($llmSettingsOpen = true)}>Open AI settings</button>
		</div>
	{:else if s.status === 'idle'}
		<div class="empty">
			<p>Whisper mode: the DJ waits until you ask.</p>
			<button class="btn primary" on:click={() => dj.loadSuggestions(undefined, true)}>Get moves</button>
		</div>
	{:else if s.status === 'loading'}
		<ul class="list" aria-busy="true" aria-label="Loading moves">
			{#each Array(kind ? 2 : 6) as _}
				<li class="skeleton-row"><span class="sk art" /><span class="sk lines"><span class="sk l1" /><span class="sk l2" /></span></li>
			{/each}
		</ul>
	{:else if s.status === 'failed'}
		<div class="empty">
			<p>{s.error}</p>
			<button class="btn" on:click={() => dj.loadSuggestions(undefined, true)}>Try again</button>
		</div>
	{:else if !moves.length}
		<p class="empty">{missingCopy(kind)}</p>
	{:else}
		{#each moves as move (move.move)}
			<section class="move" class:lead={move.move === 'toward' || move.move === 'drift'}>
				{#if !kind}
					<h3>
						<Icon name={move.move} size={16} />
						<span>{moveLabel(move.move)}</span>
						<span class="summary">{MOVE_SUMMARY[move.move] ?? ''}</span>
					</h3>
				{:else}
					<p class="single-summary">{MOVE_SUMMARY[move.move] ?? ''}</p>
				{/if}
				<ul class="list">
					{#each move.tracks as pick (pick.id)}
						<li animate:flip={{ duration: 200 }}>
							<PickRow {dj} {pick} queued={queued.has(pick.id)} />
						</li>
					{/each}
				</ul>
			</section>
		{/each}
	{/if}
</div>

<style>
	.moves {
		padding: 4px 16px 12px;
	}

	.move + .move {
		margin-top: 12px;
	}

	h3 {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 10px 0 2px;
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.summary,
	.single-summary {
		font-size: 13px;
		font-weight: 400;
		color: var(--text-muted);
	}

	.single-summary {
		margin: 10px 0 0;
	}

	/* The goal's influence is the only purple in the content area. */
	.lead h3 {
		color: var(--accent-2-text);
	}

	.list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.list > li + li {
		border-top: 1px solid var(--border-subtle);
	}

	.empty {
		margin: 24px auto;
		max-width: 34ch;
		text-align: center;
		font-size: 14px;
		line-height: 1.5;
		color: var(--text-muted);
	}

	.empty p {
		margin: 0 0 12px;
	}

	.skeleton-row {
		display: flex;
		gap: 12px;
		padding: 10px 0;
		border-top: 1px solid var(--border-subtle);
	}

	.skeleton-row:first-child {
		border-top: none;
	}

	.sk {
		display: block;
		background: var(--surface-2);
		border-radius: 4px;
	}

	.sk.art {
		width: 44px;
		height: 44px;
		flex: none;
	}

	.sk.lines {
		flex: 1;
		background: none;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding-top: 4px;
	}

	.sk.l1 {
		height: 12px;
		width: 60%;
	}

	.sk.l2 {
		height: 10px;
		width: 85%;
	}
</style>
