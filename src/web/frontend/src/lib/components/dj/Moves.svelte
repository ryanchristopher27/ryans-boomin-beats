<script>
	import { openSettings } from '$lib/settings.js';
	// The Next moves widget, and (with `kind`) a single-move widget. All of them
	// read the one `suggestions` store: one LLM call per track, however many
	// move widgets are on screen.
	import { flip } from 'svelte/animate';
		import { MOVE_SUMMARY, moveLabel } from '$lib/dj/layout.js';
	import { queuedKeys } from '$lib/dj/logic.js';
	import PickRow from './PickRow.svelte';
	import Bars from '../ui/Bars.svelte';
	import Icon from '../Icon.svelte';
	import { say } from '$lib/toast.js';

	// F3c: why a move's picks missed; the last chip just asks for different ones.
	const WHY = ['Too slow', 'Too intense', 'Heard recently', 'Wrong genre', 'Too obvious'];

	// The handoff's move glyphs.
	const GLYPH = { hold: '=', lift: '↑', drop: '↓', pivot: '←', curveball: '→', toward: '◆', drift: '~', similar: '≈' };

	/** @type {any} */
	export let dj;
	/** @type {string | null} */
	export let kind = null;

	const { suggestions, doc, player, moveFeedback, moveLoading } = dj;

	/** The move whose "What's off?" chips are open. */
	let asking = null;

	async function refresh(move, note) {
		asking = null;
		const r = await dj.refreshMove(move, note);
		if (r?.ok) say(note ? `Got it: fewer picks that are ${note.toLowerCase()}.` : 'Here are some different ones.');
		else if (r) say("Couldn't get new picks for that move. Try again.");
	}

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
			<button class="btn" on:click={() => openSettings('ai')}>Open AI settings</button>
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
						<button
							class="refresh"
							class:spin={$moveLoading[move.move]}
							on:click={() => (asking = asking === move.move ? null : move.move)}
							disabled={$moveLoading[move.move]}
							aria-expanded={asking === move.move}
							aria-label="New {moveLabel(move.move)} picks"
							title="New {moveLabel(move.move)} picks"
						>
							<Icon name="refresh" size={13} />
						</button>
					</h3>
					{#if asking === move.move}
						<div class="ask">
							<p>What's off about these?</p>
							<div class="why">
								<!-- Last.fm's picks can't take notes; only an AI round can. -->
								{#each move.move === 'similar' ? [] : WHY as w}<button class="chip why-chip" on:click={() => refresh(move.move, w)}>{w}</button>{/each}
								<button class="chip why-chip new" on:click={() => refresh(move.move)}>Just show new ones</button>
							</div>
						</div>
					{/if}
					{#if $moveFeedback[move.move]?.length}
						<p class="learned mono" title="Sent with every {moveLabel(move.move)} request this session">Avoiding: {$moveFeedback[move.move].join(', ').toLowerCase()}</p>
					{/if}
					{#if $moveLoading[move.move]}
						{#each Array(move.tracks.length || 2) as _}
							<div class="sk-row" aria-hidden="true"><span class="skeleton sk-art" /><span class="sk-lines"><span class="skeleton" style:width="60%" /><span class="skeleton" style:width="85%" /></span></div>
						{/each}
					{:else}
						<ul class="list">
							{#each move.tracks as pick (pick.id)}
								<li animate:flip={{ duration: 200 }}>
									<PickRow {dj} {pick} compact queued={queued.has(pick.id)} />
								</li>
							{/each}
						</ul>
					{/if}
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
		font-size: calc(13px * var(--text-scale, 1));
		font-weight: 600;
	}

	.refresh {
		flex: none;
		width: 26px;
		height: 26px;
		display: grid;
		place-items: center;
		padding: 0;
		border: none;
		border-radius: 7px;
		background: transparent;
		color: rgba(243, 243, 245, 0.55);
		cursor: pointer;
		transition: background-color var(--transition), color var(--transition);
	}

	.refresh:hover:not(:disabled),
	.refresh[aria-expanded='true'] {
		background: rgba(255, 255, 255, 0.08);
		color: var(--text-primary);
	}

	.refresh.spin :global(svg) {
		animation: bbspin 0.7s linear infinite;
	}

	.ask {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 6px 8px 8px;
		animation: bbin 0.18s var(--ease);
	}

	.ask p {
		margin: 0;
		font-size: calc(12px * var(--text-scale, 1));
		color: rgba(243, 243, 245, 0.6);
	}

	.why {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}

	.why-chip {
		height: 26px;
		padding: 0 10px;
		font-size: calc(12px * var(--text-scale, 1));
	}

	.why-chip.new {
		border-color: var(--accent-tint-border);
		color: var(--accent-tint-text);
	}

	.learned {
		margin: 0;
		padding: 0 8px 4px;
		font-size: calc(11px * var(--text-scale, 1));
		color: var(--accent-tint-text);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.glyph {
		width: 14px;
		text-align: center;
	}

	.summary {
		flex: 1;
		min-width: 0;
		font-size: calc(12px * var(--text-scale, 1));
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
		font-size: calc(13px * var(--text-scale, 1));
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
		font-size: calc(14px * var(--text-scale, 1));
		line-height: 1.5;
		color: var(--text-muted);
	}

	.empty p {
		margin: 0 0 12px;
	}
</style>
