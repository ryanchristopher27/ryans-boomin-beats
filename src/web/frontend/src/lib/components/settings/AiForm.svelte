<script>
	// Pick an AI provider and connect it (Settings' AI tab and first run).
	import { llmConfig } from '../../../stores.js';
	import { PROVIDERS, connectLLM, disconnectLLM } from '$lib/llm.js';

	/** Called after a successful connect. */
	export let onConnected = () => {};
	/** Show Disconnect when something is connected (Settings). */
	export let canDisconnect = true;
	/** First run's larger controls. */
	export let large = false;

	let provider = PROVIDERS.some((p) => p.id === $llmConfig.provider) ? $llmConfig.provider : PROVIDERS[0].id;
	let apiKey = $llmConfig.apiKey;
	let loading = false;
	let errorMsg = '';

	$: chosen = PROVIDERS.find((p) => p.id === provider) ?? PROVIDERS[0];

	function pick(id) {
		if (id === provider) return;
		provider = id;
		apiKey = id === $llmConfig.provider ? $llmConfig.apiKey : '';
		errorMsg = '';
	}

	async function connect() {
		loading = true;
		errorMsg = '';
		const r = await connectLLM(provider, apiKey);
		loading = false;
		if (r.ok) onConnected();
		else errorMsg = r.error;
	}

	function disconnect() {
		disconnectLLM();
		apiKey = '';
	}
</script>

<div class="ai" class:large>
	<div class="providers" role="radiogroup" aria-label="AI provider">
		{#each PROVIDERS as p}
			<button class="provider" class:on={p.id === provider} role="radio" aria-checked={p.id === provider} on:click={() => pick(p.id)}>
				<span class="ring"><span /></span>
				<span class="provider-text">
					<span class="provider-label">{p.label}</span>
					<span class="provider-note">{p.note}</span>
				</span>
			</button>
		{/each}
	</div>

	<div class="form">
		{#if !chosen.keyless}
			<input class="key" type="password" placeholder={chosen.placeholder} bind:value={apiKey} aria-label="{chosen.label} API key" autocomplete="off" spellcheck="false" />
		{/if}
		{#if errorMsg}<p class="error" role="alert">{errorMsg}</p>{/if}
		<div class="buttons">
			<button class="btn primary" on:click={connect} disabled={(!chosen.keyless && !apiKey) || loading}>
				{loading ? 'Connecting…' : $llmConfig.connected ? 'Save' : 'Connect'}
			</button>
			{#if canDisconnect && $llmConfig.connected}<button class="btn" on:click={disconnect}>Disconnect</button>{/if}
			<slot name="after" />
		</div>
	</div>
</div>

<style>
	.providers {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin: 0 -8px;
	}

	.large .providers {
		margin: 0;
		padding: 6px;
		border-radius: 16px;
		background: var(--glass);
		border: 1px solid var(--border-subtle);
		-webkit-backdrop-filter: var(--glass-blur);
		backdrop-filter: var(--glass-blur);
	}

	.provider {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 9px 10px;
		border-radius: 10px;
		border: 1px solid transparent;
		background: transparent;
		color: var(--text-primary);
		font: inherit;
		text-align: left;
		white-space: normal;
		cursor: pointer;
		transition: background-color var(--transition), border-color var(--transition);
	}

	.large .provider {
		padding: 11px 12px;
		border-radius: 11px;
	}

	.provider:hover {
		background: var(--hover);
	}

	.provider.on {
		background: rgba(var(--accent-rgb), 0.07);
		border-color: rgba(var(--accent-rgb), 0.35);
	}

	.ring {
		flex: none;
		width: 16px;
		height: 16px;
		display: grid;
		place-items: center;
		border-radius: 50%;
		border: 1.5px solid rgba(255, 255, 255, 0.25);
	}

	.ring span {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}

	.provider.on .ring {
		border-color: var(--accent);
	}

	.provider.on .ring span {
		background: var(--accent);
	}

	.provider-text {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}

	.provider-label {
		font-size: calc(14px * var(--text-scale, 1));
		font-weight: 500;
	}

	.provider-note {
		font-size: calc(12px * var(--text-scale, 1));
		color: rgba(243, 243, 245, 0.5);
	}

	.form {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 14px 0 10px;
	}

	.key {
		height: 38px;
		padding: 0 12px;
		border-radius: 9px;
		border: 1px solid var(--border-control);
		background: rgba(0, 0, 0, 0.35);
		color: var(--text-primary);
		font-family: var(--font-mono);
		font-size: calc(13px * var(--text-scale, 1));
	}

	.large .key {
		height: 44px;
		border-radius: 11px;
	}

	.key:focus {
		outline: none;
		border-color: var(--accent-tint-border);
	}

	.error {
		margin: 0;
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--danger-text);
	}

	.buttons {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
	}

	.buttons :global(.btn) {
		flex: 1;
		min-width: 140px;
		height: 38px;
	}

	.large .buttons :global(.btn) {
		height: 46px;
		border-radius: 11px;
		font-size: calc(14px * var(--text-scale, 1));
	}
</style>
