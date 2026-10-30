<script>
	// The Ask the DJ widget: new picks in your own words, or a change to the
	// controls, the goal or the layout. lib/dj/chat.js sends and applies; the
	// widget header holds Clear (routes/dj/+page.svelte).
	import { afterUpdate, tick } from 'svelte';
	import Icon from '../Icon.svelte';
	import Bars from '../ui/Bars.svelte';
	import PickRow from './PickRow.svelte';
	import { djContext } from './context.js';
	import { chatBusy, chatLog, sendChat } from '$lib/dj/chat.js';
	import { queuedKeys } from '$lib/dj/logic.js';
	import { openSettings } from '$lib/settings.js';
	import { hasLLM } from '$lib/dj/api.js';
	import { llmConfig } from '../../../stores.js';

	/** @type {any} */
	export let dj;
	const { doc } = dj;
	const ctx = djContext();

	const STARTERS = ['More upbeat picks', 'Something from the 90s', 'Switch to Compass', 'Put Up next on the left'];

	let draft = '';
	let list;
	$: queued = queuedKeys([...$doc.queue.sent, ...$doc.queue.upcoming]);
	$: noAI = ($llmConfig, !hasLLM());

	async function send(text = draft) {
		if (!text.trim() || $chatBusy) return;
		draft = '';
		await sendChat(text, { dj, page: ctx.page });
	}

	function onKey(e) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	}

	// Keep the newest message in view.
	let seen = 0;
	afterUpdate(async () => {
		if (!list || $chatLog.length + ($chatBusy ? 1 : 0) === seen) return;
		seen = $chatLog.length + ($chatBusy ? 1 : 0);
		await tick();
		list.scrollTop = list.scrollHeight;
	});
</script>

<section class="chat" aria-label="Ask the DJ">
	{#if noAI}
		<p class="note">Connect an AI to chat with the DJ. <button class="link" on:click={() => openSettings('ai')}>Add one</button></p>
	{:else}
		{#if $chatLog.length || $chatBusy}
			<ol class="log" bind:this={list} aria-live="polite">
				{#each $chatLog as e, i (i)}
					<li class={e.role} class:error={e.error}>
						<p class="text">{e.text}</p>
						{#if e.applied?.length}
							<div class="applied">
								{#each e.applied as a}<span class="chip"><Icon name="check" size={11} /> {a}</span>{/each}
							</div>
						{/if}
						{#if e.picks?.length}
							<ul class="picks">
								{#each e.picks as pick (pick.id)}
									<li><PickRow {dj} {pick} compact queued={queued.has(pick.id) || (!!pick.isrc && queued.has(pick.isrc))} /></li>
								{/each}
							</ul>
						{/if}
					</li>
				{/each}
				{#if $chatBusy}
					<li class="assistant thinking" role="status"><Bars count={3} height={10} /> Thinking…</li>
				{/if}
			</ol>
		{:else}
			<div class="starters">
				{#each STARTERS as s}<button class="chip-btn" on:click={() => send(s)}>{s}</button>{/each}
			</div>
		{/if}
		<div class="composer">
			<textarea rows="1" placeholder="Ask for songs, or change the layout…" aria-label="Message the DJ" bind:value={draft} on:keydown={onKey} />
			<button class="icon-btn send" on:click={() => send()} disabled={!draft.trim() || $chatBusy} aria-label="Send">
				<Icon name="send" size={15} />
			</button>
		</div>
	{/if}
</section>

<style>
	/* Fills the widget: the conversation scrolls, the composer stays at the bottom. */
	.chat {
		height: 100%;
		box-sizing: border-box;
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 8px 12px 12px;
	}

	.link {
		padding: 0;
		border: none;
		background: none;
		color: var(--accent);
		font: inherit;
		font-size: calc(12px * var(--text-scale, 1));
		cursor: pointer;
	}

	.note {
		margin: 0;
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.log {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 8px;
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overscroll-behavior: contain;
	}

	.log > li {
		max-width: 92%;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.user {
		align-self: flex-end;
		padding: 7px 11px;
		border-radius: 12px 12px 4px 12px;
		background: rgba(var(--accent-rgb), 0.14);
		color: var(--text-primary);
	}

	.assistant {
		align-self: stretch;
		max-width: none;
	}

	.text {
		margin: 0;
		font-size: calc(13px * var(--text-scale, 1));
		line-height: 1.45;
		white-space: pre-wrap;
	}

	.assistant .text {
		color: var(--text-secondary, var(--text-primary));
	}

	.error .text {
		color: var(--warning);
	}

	.thinking {
		flex-direction: row;
		align-items: center;
		gap: 8px;
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.applied {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 2px 8px;
		border-radius: 999px;
		background: var(--surface-2);
		font-size: calc(11px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.picks {
		list-style: none;
		margin: 0 -8px;
		padding: 0;
	}

	.starters {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.chip-btn {
		height: 28px;
		padding: 0 10px;
		border-radius: 999px;
		border: 1px solid var(--border-control);
		background: transparent;
		color: var(--text-muted);
		font: inherit;
		font-size: calc(12px * var(--text-scale, 1));
		cursor: pointer;
	}

	.chip-btn:hover {
		background: var(--hover);
		color: var(--text-primary);
	}

	.composer {
		margin-top: auto;
		display: flex;
		align-items: flex-end;
		gap: 6px;
		padding: 4px 4px 4px 10px;
		border-radius: 12px;
		border: 1px solid var(--border-control);
		background: var(--surface-2);
	}

	.composer:focus-within {
		border-color: var(--accent-tint-border);
	}

	textarea {
		flex: 1;
		min-width: 0;
		resize: none;
		max-height: 96px;
		padding: 6px 0;
		border: none;
		background: transparent;
		color: var(--text-primary);
		font: inherit;
		font-size: calc(13px * var(--text-scale, 1));
		line-height: 1.4;
		field-sizing: content;
	}

	textarea:focus {
		outline: none;
	}

	.send {
		flex: none;
	}
</style>
