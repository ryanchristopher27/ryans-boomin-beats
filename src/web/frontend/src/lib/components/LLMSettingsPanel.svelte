<script>
	// The gear popover (R1). Only the AI tab for now; General arrives in F1.
	import { PUBLIC_API_URL } from '$env/static/public';
	import { llmConfig } from '../../stores.js';
	import Icon from './Icon.svelte';

	export let onClose = () => {};

	let provider = $llmConfig.provider;
	let apiKey = $llmConfig.apiKey;
	let loading = false;
	let errorMsg = '';

	// 'Your Claude Code' uses the CLI login on this Mac; there's no key to paste.
	const PROVIDERS = [
		{ id: 'claude', label: 'Claude', note: 'Anthropic API key', placeholder: 'sk-ant-…' },
		{ id: 'openai', label: 'OpenAI', note: 'OpenAI API key', placeholder: 'sk-…' },
		{ id: 'groq', label: 'Groq', note: 'Free tier, faster, lighter picks', placeholder: 'gsk_…' },
		{ id: 'claude-code', label: 'Your Claude Code', note: 'Runs on this Mac. No key needed. Works while the backend runs locally.' }
	];
	$: chosen = PROVIDERS.find((p) => p.id === provider) ?? PROVIDERS[0];
	$: connectedName = PROVIDERS.find((p) => p.id === $llmConfig.provider)?.label ?? $llmConfig.provider;
	$: keyless = provider === 'claude-code';

	async function connect() {
		loading = true;
		errorMsg = '';
		try {
			// /llm/connect/ only validates the key against the provider and
			// discards it; nothing is stored server-side any more.
			const res = await fetch(`${PUBLIC_API_URL}/llm/connect/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ provider, api_key: keyless ? '' : apiKey })
			});
			const data = await res.json();
			if (data.connected) {
				const key = keyless ? '' : apiKey;
				$llmConfig = { provider, apiKey: key, connected: true };
				localStorage.setItem('llmConfig', JSON.stringify({ provider, apiKey: key, connected: true }));
				onClose();
			} else {
				errorMsg = data.error || 'Connection failed.';
			}
		} catch (e) {
			errorMsg = 'Could not reach the server.';
		} finally {
			loading = false;
		}
	}

	function disconnect() {
		$llmConfig = { provider: 'claude', apiKey: '', connected: false };
		localStorage.removeItem('llmConfig');
		apiKey = '';
	}

	function pick(id) {
		if (id === provider) return;
		provider = id;
		apiKey = id === $llmConfig.provider ? $llmConfig.apiKey : '';
		errorMsg = '';
	}
</script>

<svelte:window on:keydown={(e) => e.key === 'Escape' && onClose()} />

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div class="scrim" on:click={onClose} />
<div class="popover" role="dialog" aria-label="Settings">
	<div class="head">
		<h2>Settings</h2>
		<span class="tab"><span class="dot" class:connected={$llmConfig.connected} /> AI</span>
		<button class="icon-btn" on:click={onClose} aria-label="Close"><Icon name="x" size={14} /></button>
	</div>

	<div class="body">
		<div class="status" class:connected={$llmConfig.connected}>
			<span class="dot" class:connected={$llmConfig.connected} />
			<div>
				<p class="status-title">{$llmConfig.connected ? `${connectedName} connected` : 'Connect an AI'}</p>
				<p class="status-note">
					{$llmConfig.connected
						? 'Powers song analysis, playlists and DJ moves. Your key stays on this device.'
						: 'Add one for song analysis, playlists and DJ moves. Your key stays on this device.'}
				</p>
			</div>
		</div>

		<p class="section">PROVIDER</p>
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
			{#if !keyless}
				<input class="key" type="password" placeholder={chosen.placeholder} bind:value={apiKey} aria-label="{chosen.label} API key" autocomplete="off" />
			{/if}
			{#if errorMsg}<p class="error" role="alert">{errorMsg}</p>{/if}
			<div class="buttons">
				<button class="btn primary" on:click={connect} disabled={(!keyless && !apiKey) || loading}>
					{loading ? 'Connecting…' : $llmConfig.connected ? 'Save' : 'Connect'}
				</button>
				{#if $llmConfig.connected}<button class="btn" on:click={disconnect}>Disconnect</button>{/if}
			</div>
		</div>
	</div>

	<div class="foot">Saved on this device</div>
</div>

<style>
	.scrim {
		position: fixed;
		inset: 0;
		z-index: 60;
	}

	.popover {
		position: fixed;
		z-index: 61;
		top: calc(var(--header-height) + 8px);
		right: 16px;
		width: 380px;
		max-height: calc(100vh - var(--header-height) - 24px);
		display: flex;
		flex-direction: column;
		border-radius: 18px;
		background: var(--popover);
		-webkit-backdrop-filter: blur(30px);
		backdrop-filter: blur(30px);
		border: 1px solid var(--border-control);
		box-shadow: var(--shadow-pop);
		overflow: hidden;
		animation: bbin 0.18s var(--ease);
	}

	.head {
		flex: none;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 12px 10px 12px 16px;
		border-bottom: 1px solid var(--border-subtle);
	}

	h2 {
		flex: 1;
		margin: 0;
		font-size: 15px;
		font-weight: 600;
	}

	.tab {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		height: 28px;
		padding: 0 12px;
		border-radius: 7px;
		background: var(--surface-active);
		font-size: 12px;
		font-weight: 500;
	}

	.head .icon-btn {
		width: 30px;
		height: 30px;
	}

	.dot {
		flex: none;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: rgba(243, 243, 245, 0.3);
	}

	.dot.connected {
		background: var(--success);
	}

	.body {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding: 0 16px 8px;
	}

	.status {
		display: flex;
		align-items: center;
		gap: 10px;
		margin: 14px 0 10px;
		padding: 12px;
		border-radius: 12px;
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid rgba(255, 255, 255, 0.08);
	}

	.status.connected {
		background: rgba(74, 222, 128, 0.06);
		border-color: rgba(74, 222, 128, 0.2);
	}

	.status .dot {
		width: 8px;
		height: 8px;
	}

	p {
		margin: 0;
	}

	.status-title {
		font-size: 14px;
		font-weight: 500;
	}

	.status-note {
		font-size: 12px;
		line-height: 1.4;
		color: rgba(243, 243, 245, 0.55);
	}

	.section {
		padding: 16px 0 4px;
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 500;
		letter-spacing: 0.04em;
		color: var(--text-subtle);
	}

	.providers {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin: 0 -8px;
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
		text-align: left;
		white-space: normal;
		cursor: pointer;
		transition: background-color var(--transition), border-color var(--transition);
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
		font-size: 14px;
		font-weight: 500;
	}

	.provider-note {
		font-size: 12px;
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
		font-size: 13px;
	}

	.key:focus {
		outline: none;
		border-color: var(--accent-tint-border);
	}

	.error {
		font-size: 12px;
		color: var(--danger-text);
	}

	.buttons {
		display: flex;
		gap: 8px;
	}

	.buttons .btn {
		height: 38px;
	}

	.buttons .primary {
		flex: 1;
	}

	.foot {
		flex: none;
		padding: 10px 16px;
		border-top: 1px solid var(--border-subtle);
		font-size: 12px;
		color: var(--text-subtle);
	}
</style>
