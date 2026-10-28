<script>
	// The Next moves widget, and (with `kind`) a single-move widget. All of them
	// read the one `suggestions` store: one LLM call per track, however many
	// move widgets are on screen.
	import { flip } from 'svelte/animate';
	import { llmSettingsOpen } from '../../../stores.js';
	import { MOVE_SUMMARY, moveLabel } from '$lib/dj/layout.js';
	import { queuedKeys } from '$lib/dj/logic.js';
	import PickRow from './PickRow.svelte';
	import Bars from '../ui/Bars.svelte';

	// The handoff's move glyphs.
	const GLYPH = { hold: '=', lift: '↑', drop: '↓', pivot: '←', curveball: '→', toward: '◆', drift: '~' };

	/** @type {any} */
	export let dj;
	/** @type {string | null} */
	export let kind = null;

	const { suggestions, doc, player } = dj;

	$: s = $suggestions;
	$: moves = kind ? s.moves.filter((m) => m.move === kind) : s.moves;
	$: queued = queuedKeys([...$doc.queue.sent, ...$doc.queue.upcoming]);
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
		<p class="reading" role="status"><Bars count={4} height={12} /> Reading the room…</p>
		<div class:groups={!kind} aria-busy="true" aria-label="Loading moves">
			{#each Array(kind ? 1 : 6) as _}
				<div class="group">
					{#if !kind}<div class="skeleton sk-head" />{/if}
					{#each Array(3) as _}
						<div class="sk-row"><span class="skeleton sk-art" /><span class="sk-lines"><span class="skeleton" style:width="60%" /><span class="skeleton" style:width="85%" /></span></div>
					{/each}
				</div>
			{/each}
		</div>
	{:else if s.status === 'failed'}
		<div class="empty">
			<p>{s.error}</p>
			<button class="btn" on:click={() => dj.loadSuggestions(undefined, true)}>Try again</button>
		</div>
	{:else if !moves.length}
		<p class="empty">{missingCopy(kind)}</p>
	{:else}
		<div class:groups={!kind}>
			{#each moves as move, i (move.move)}
				<section class="group" class:lead={move.move === 'toward' || move.move === 'drift'} style:animation-delay="{i * 40}ms">
					<h3>
						{#if !kind}
							<span class="glyph mono" aria-hidden="true">{GLYPH[move.move] ?? '·'}</span>
							<span class="name">{moveLabel(move.move)}</span>
						{/if}
						<span class="summary">{MOVE_SUMMARY[move.move] ?? ''}</span>
					</h3>
					<ul class="list">
						{#each move.tracks as pick (pick.id)}
							<li animate:flip={{ duration: 200 }}>
								<PickRow {dj} {pick} compact queued={queued.has(pick.id)} />
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		</div>
	{/if}
</div>

<style>
	.moves {
		padding: 8px;
	}

	.groups {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
		gap: 8px;
	}

	.group {
		padding: 4px;
		border-radius: 12px;
		background: rgba(255, 255, 255, 0.025);
		border: 1px solid rgba(255, 255, 255, 0.06);
		animation: bbin 0.4s var(--ease) both;
	}

	/* A single-move widget is one group without its own card. */
	.moves > div:not(.groups) > .group {
		padding: 0;
		border: none;
		background: none;
	}

	h3 {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
		margin: 0;
		padding: 6px 8px 4px;
		font-size: 13px;
		font-weight: 600;
	}

	.glyph {
		width: 14px;
		text-align: center;
	}

	.summary {
		flex: 1;
		min-width: 0;
		font-size: 12px;
		font-weight: 400;
		color: rgba(243, 243, 245, 0.5);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	/* The goal's influence is the only purple in the content area. */
	.lead {
		border-color: rgba(196, 155, 255, 0.25);
	}

	.lead h3 {
		color: var(--accent-2-text);
	}

	.list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.reading {
		display: flex;
		align-items: center;
		gap: 10px;
		margin: 0;
		padding: 6px 8px 12px;
		font-size: 13px;
		color: rgba(243, 243, 245, 0.65);
	}

	.sk-head {
		height: 12px;
		width: 45%;
		margin: 8px;
	}

	.sk-row {
		display: flex;
		gap: 10px;
		align-items: center;
		padding: 6px 8px;
	}

	.sk-art {
		flex: none;
		width: 34px;
		height: 34px;
		border-radius: 7px;
	}

	.sk-lines {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.sk-lines .skeleton {
		height: 9px;
		border-radius: 4px;
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
</style>
