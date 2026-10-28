<script>
	// The Builder's empty state (R4): the hero composer and example prompts.
	import Icon from '../Icon.svelte';

	export let draft = '';
	export let count = 10;
	export let aiLabel = '';
	export let busy = false;
	export let onSubmit = (prompt) => {};

	const COUNTS = [10, 12, 20];
	const EXAMPLES = ['late night jazz for studying', 'moody r&b for a night drive, nothing too slow', 'sunny 70s soul for a cookout', 'house that builds for a pregame'];

	function submit() {
		if (draft.trim() && !busy) onSubmit(draft.trim());
	}

	function onKey(e) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			submit();
		}
	}
</script>

<section class="hero">
	<div class="inner">
		<p class="eyebrow">Playlist builder · {aiLabel}</p>
		<h1>Describe a playlist.</h1>
		<p class="lede">The AI picks the songs and checks each one is on Spotify. You can refine it after.</p>
		<div class="composer">
			<textarea rows="2" placeholder="e.g. late night jazz for studying" aria-label="Describe a playlist" bind:value={draft} on:keydown={onKey} />
			<div class="bar">
				<div class="count">
					<span>Songs</span>
					<div class="seg" role="radiogroup" aria-label="Number of songs">
						{#each COUNTS as n}
							<button role="radio" aria-checked={count === n} class:active={count === n} class="mono" on:click={() => (count = n)}>{n}</button>
						{/each}
					</div>
				</div>
				<button class="btn white build" on:click={submit} disabled={!draft.trim() || busy}>Build playlist <Icon name="arrow" size={15} /></button>
			</div>
		</div>
		<div class="examples">
			{#each EXAMPLES as ex}
				<button class="chip example" on:click={() => onSubmit(ex)}>{ex}</button>
			{/each}
		</div>
	</div>
</section>

<style>
	.hero {
		min-height: calc(100vh - var(--header-height) - var(--mini-h, 0px));
		padding: 12vh 32px 80px;
		background: radial-gradient(90% 110% at 50% 0%, oklch(0.32 0.09 285) 0%, oklch(0.16 0.03 285) 55%, var(--surface-0) 100%);
	}

	.inner {
		max-width: 820px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 24px;
		text-align: center;
	}

	.eyebrow {
		margin: 0;
		font-family: var(--font-mono);
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		color: rgba(243, 243, 245, 0.6);
	}

	h1 {
		margin: 0;
		font-size: calc(clamp(44px, 9vw, 84px) * var(--text-scale, 1));
		font-weight: 700;
		line-height: 0.95;
		letter-spacing: -0.05em;
		text-wrap: balance;
	}

	.lede {
		margin: 0;
		max-width: 560px;
		font-size: calc(17px * var(--text-scale, 1));
		line-height: 1.5;
		color: rgba(243, 243, 245, 0.7);
		text-wrap: pretty;
	}

	.composer {
		width: 100%;
		padding: 6px;
		border-radius: 22px;
		background: rgba(10, 10, 12, 0.55);
		border: 1px solid rgba(255, 255, 255, 0.14);
		-webkit-backdrop-filter: blur(12px);
		backdrop-filter: blur(12px);
		text-align: left;
	}

	.composer:focus-within {
		border-color: var(--accent-tint-border);
	}

	textarea {
		width: 100%;
		resize: none;
		padding: 14px 16px 4px;
		border: none;
		background: transparent;
		color: var(--text-primary);
		font-size: calc(18px * var(--text-scale, 1));
		line-height: 1.5;
	}

	textarea:focus {
		outline: none;
	}

	.bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: 6px 6px 6px 16px;
	}

	.count {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: calc(13px * var(--text-scale, 1));
		color: rgba(243, 243, 245, 0.55);
	}

	.seg {
		display: flex;
		padding: 2px;
		border-radius: 999px;
		background: rgba(0, 0, 0, 0.35);
	}

	.seg button {
		height: 28px;
		padding: 0 12px;
		border: none;
		border-radius: 999px;
		background: none;
		color: var(--text-muted);
		font-size: calc(13px * var(--text-scale, 1));
		font-weight: 500;
		cursor: pointer;
	}

	.seg button.active {
		background: var(--surface-active);
		color: var(--text-primary);
	}

	.build {
		height: 42px;
		padding: 0 18px;
		border-radius: 999px;
		font-size: calc(14px * var(--text-scale, 1));
	}

	.examples {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 8px;
	}

	.example {
		height: 34px;
		padding: 0 14px;
		border-color: rgba(255, 255, 255, 0.14);
		background: rgba(10, 10, 12, 0.35);
	}

	.example:hover {
		background: rgba(255, 255, 255, 0.08);
	}

	@media (max-width: 759px) {
		.hero {
			padding: 8vh 16px 48px;
		}
	}
</style>
