<script>
	// The Builder's chat column (R4): the exchange so far, the build progress,
	// refine chips and a follow-up input.
	import { afterUpdate } from 'svelte';
	import { replyText } from '$lib/builder.js';
	import Bars from '../ui/Bars.svelte';
	import Icon from '../Icon.svelte';

	/** @type {{ role: string, content: string }[]} */
	export let messages = [];
	export let loading = false;
	/** 0 picking, 1 checking */
	export let step = 0;
	export let error = '';
	export let onSend = (text) => {};
	export let onReset = () => {};
	/** @type {null | (() => void)} */
	export let onOpenSettings = null;

	const STEPS = ['Picking songs', 'Checking each one is on Spotify'];
	const REFINES = ['More upbeat', 'Add some 90s', 'Fewer big hits', 'Shorter songs'];

	let follow = '';
	let scroller;

	afterUpdate(() => {
		if (scroller) scroller.scrollTop = scroller.scrollHeight;
	});

	function send(text) {
		if (!text.trim() || loading) return;
		onSend(text.trim());
		follow = '';
	}

	// Each assistant reply is the songs as JSON; the first one built the list.
	$: firstReply = messages.findIndex((m) => m.role === 'assistant');
</script>

<section class="conv" aria-label="Conversation">
	<div class="head">
		<h2>Conversation</h2>
		<button class="btn small reset" on:click={onReset} disabled={loading}>New playlist</button>
	</div>

	<div class="log" bind:this={scroller} aria-live="polite">
		{#each messages as msg, i}
			<div class="msg {msg.role === 'user' ? 'user' : 'ai'}">
				<p>{msg.role === 'user' ? msg.content : replyText(msg.content, i === firstReply)}</p>
			</div>
		{/each}
		{#if loading}
			<div class="progress" role="status">
				<Bars count={7} height={14} />
				{#each STEPS as label, i}
					<p class="step" class:done={i < step} class:now={i === step}><span class="dot" />{label}</p>
				{/each}
			</div>
		{/if}
		{#if error}
			<div class="msg ai err" role="alert">
				<p>{error}</p>
				{#if onOpenSettings}<button class="btn small primary" on:click={onOpenSettings}>Open AI settings</button>{/if}
			</div>
		{/if}
	</div>

	<div class="foot">
		<div class="refines">
			{#each REFINES as r}
				<button class="chip refine" on:click={() => send(r)} disabled={loading}>{r}</button>
			{/each}
		</div>
		<form class="follow" on:submit|preventDefault={() => send(follow)}>
			<input placeholder="Refine it: more upbeat, fewer ballads" aria-label="Refine the playlist" bind:value={follow} disabled={loading} />
			<button class="send" type="submit" aria-label="Send" disabled={!follow.trim() || loading}><Icon name="lift" size={15} /></button>
		</form>
	</div>
</section>

<style>
	.conv {
		display: flex;
		flex-direction: column;
		min-height: 0;
		height: 100%;
		border-right: 1px solid var(--border-subtle);
	}

	.head {
		flex: none;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 16px 20px;
		border-bottom: 1px solid var(--border-subtle);
	}

	h2 {
		margin: 0;
		font-size: 15px;
		font-weight: 600;
	}

	.reset {
		height: 30px;
		padding: 0 10px;
		border-color: rgba(255, 255, 255, 0.08);
		color: rgba(243, 243, 245, 0.7);
		font-size: 12px;
	}

	.log {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overflow-x: hidden;
		display: flex;
		flex-direction: column;
		gap: 14px;
		padding: 20px;
	}

	.msg {
		display: flex;
		flex-direction: column;
		gap: 10px;
		max-width: 88%;
		padding: 11px 14px;
		border-radius: 14px;
		font-size: 14px;
		line-height: 1.5;
		animation: bbin 0.2s var(--ease);
	}

	.msg p {
		margin: 0;
		text-wrap: pretty;
	}

	.user {
		align-self: flex-end;
		background: var(--surface-active);
		color: var(--text-primary);
	}

	.ai {
		align-self: flex-start;
		border: 1px solid rgba(255, 255, 255, 0.09);
		color: rgba(243, 243, 245, 0.8);
	}

	.err {
		border-color: rgba(255, 122, 122, 0.25);
		color: #ffb0b0;
	}

	.err .btn {
		align-self: flex-start;
	}

	.progress {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 12px 14px;
		border-radius: 14px;
		border: 1px solid var(--border-subtle);
	}

	/* The bars take the brand gradient across their height. */
	.progress :global(.bars span) {
		width: 3px;
		background: var(--brand-gradient);
	}

	.step {
		display: flex;
		align-items: center;
		gap: 10px;
		margin: 0;
		font-size: 13px;
		color: var(--text-subtle);
	}

	.step.done {
		color: rgba(243, 243, 245, 0.75);
	}

	.step.now {
		color: var(--text-primary);
	}

	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.15);
	}

	.done .dot,
	.now .dot {
		background: var(--accent);
	}

	.now .dot {
		animation: bbpulse 1s ease-in-out infinite;
	}

	.foot {
		flex: none;
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 14px 16px 16px;
		border-top: 1px solid var(--border-subtle);
	}

	.refines {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.refine {
		height: 28px;
		padding: 0 10px;
		font-size: 12px;
		color: rgba(243, 243, 245, 0.75);
	}

	.refine:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.follow {
		display: flex;
		gap: 8px;
		align-items: center;
		padding: 4px 4px 4px 14px;
		border-radius: 12px;
		background: var(--surface-1);
		border: 1px solid rgba(255, 255, 255, 0.09);
	}

	.follow:focus-within {
		border-color: var(--accent-tint-border);
	}

	.follow input {
		flex: 1;
		min-width: 0;
		height: 36px;
		border: none;
		background: transparent;
		color: var(--text-primary);
		font-size: 14px;
	}

	.follow input:focus {
		outline: none;
	}

	.send {
		flex: none;
		width: 36px;
		height: 36px;
		display: grid;
		place-items: center;
		padding: 0;
		border: none;
		border-radius: 9px;
		background: var(--accent);
		color: var(--accent-on);
		cursor: pointer;
	}

	.send:disabled {
		opacity: 0.45;
		cursor: default;
	}
</style>
