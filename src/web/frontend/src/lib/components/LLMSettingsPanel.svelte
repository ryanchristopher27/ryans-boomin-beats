<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import { llmConfig } from '../../stores.js';

	export let onClose = () => {};

	let provider = $llmConfig.provider;
	let apiKey = $llmConfig.apiKey;
	let loading = false;
	let errorMsg = '';

	async function connect() {
		loading = true;
		errorMsg = '';
		try {
			const res = await fetch(`${PUBLIC_API_URL}/llm/connect/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ provider, api_key: apiKey }),
			});
			const data = await res.json();
			if (data.connected) {
				$llmConfig = { provider, apiKey, connected: true };
				localStorage.setItem('llmConfig', JSON.stringify({ provider, apiKey, connected: true }));
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
</script>

<div class="panel">
	<div class="panel-header">
		<span class="panel-title">AI Settings</span>
		<button class="close-btn" on:click={onClose}>✕</button>
	</div>

	{#if $llmConfig.connected}
		<div class="connected-state">
			<div class="connected-label">
				Connected · <span class="provider-name">{$llmConfig.provider === 'claude' ? 'Claude' : $llmConfig.provider === 'groq' ? 'Groq' : 'OpenAI'}</span>
			</div>
			<button class="disconnect-btn" on:click={disconnect}>Disconnect</button>
		</div>
	{:else}
		<div class="provider-select">
			<label class="radio-label">
				<input type="radio" bind:group={provider} value="claude" />
				Claude (Anthropic)
			</label>
			<label class="radio-label">
				<input type="radio" bind:group={provider} value="openai" />
				OpenAI
			</label>
			<label class="radio-label">
				<input type="radio" bind:group={provider} value="groq" />
				Groq (free)
			</label>
		</div>

		<input
			class="key-input"
			type="password"
			placeholder={provider === 'claude' ? 'sk-ant-...' : provider === 'groq' ? 'gsk_...' : 'sk-...'}
			bind:value={apiKey}
		/>

		{#if errorMsg}
			<div class="error">{errorMsg}</div>
		{/if}

		<button class="connect-btn" on:click={connect} disabled={!apiKey || loading}>
			{loading ? 'Connecting...' : 'Connect'}
		</button>
	{/if}
</div>

<style>
	.panel {
		background-color: var(--color-dark-gray);
		border: 2px solid var(--color-light-blue);
		border-radius: 12px;
		padding: 16px;
		width: 280px;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 14px;
	}

	.panel-title {
		font-size: 0.85rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--color-light-blue);
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--color-light-blue);
		cursor: pointer;
		font-size: 0.9rem;
		padding: 0;
	}

	.provider-select {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-bottom: 12px;
	}

	.radio-label {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 0.85rem;
		cursor: pointer;
	}

	.key-input {
		width: 100%;
		box-sizing: border-box;
		background-color: var(--color-dark-gray);
		color: var(--color-light-blue);
		border: 2px solid var(--color-light-blue);
		border-radius: 8px;
		padding: 6px 10px;
		font-size: 0.8rem;
		margin-bottom: 10px;
	}

	.connect-btn {
		width: 100%;
		height: 32px;
		background-color: var(--color-light-blue);
		color: var(--color-dark-gray);
		border: 2px solid var(--color-light-blue);
		border-radius: 8px;
		font-weight: 700;
		font-size: 0.8rem;
		cursor: pointer;
	}

	.connect-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.connect-btn:hover:not(:disabled) {
		border-color: var(--color-purple);
	}

	.connected-state {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.connected-label {
		font-size: 0.8rem;
	}

	.provider-name {
		color: var(--color-light-blue);
		font-weight: 700;
	}

	.disconnect-btn {
		background: none;
		border: 2px solid var(--color-light-blue);
		border-radius: 8px;
		color: var(--color-light-blue);
		font-size: 0.75rem;
		padding: 4px 10px;
		cursor: pointer;
	}

	.disconnect-btn:hover {
		border-color: var(--color-purple);
		color: var(--color-purple);
	}

	.error {
		color: #ff6b6b;
		font-size: 0.75rem;
		margin-bottom: 8px;
	}
</style>
