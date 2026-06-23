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
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		padding: 16px;
		width: 280px;
		box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 14px;
	}

	.panel-title {
		font-size: 0.8rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-subtle);
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		font-size: 0.9rem;
		padding: 0;
		transition: color var(--transition);
	}

	.close-btn:hover {
		color: var(--text-primary);
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
		color: var(--text-muted);
		cursor: pointer;
		accent-color: var(--accent);
	}

	.key-input {
		width: 100%;
		box-sizing: border-box;
		background-color: var(--surface-0);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		padding: 8px 10px;
		font-size: 0.8rem;
		margin-bottom: 10px;
		transition: border-color var(--transition);
	}

	.key-input::placeholder {
		color: var(--text-subtle);
	}

	.key-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.connect-btn {
		width: 100%;
		height: 36px;
		background: var(--brand-gradient);
		color: var(--surface-0);
		border: none;
		border-radius: var(--radius-sm);
		font-weight: 700;
		font-size: 0.8rem;
		cursor: pointer;
		transition: filter var(--transition);
	}

	.connect-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.connect-btn:hover:not(:disabled) {
		filter: brightness(1.1);
	}

	.connected-state {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.connected-label {
		font-size: 0.8rem;
		color: var(--text-muted);
	}

	.provider-name {
		color: var(--accent);
		font-weight: 700;
	}

	.disconnect-btn {
		background-color: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		color: var(--text-primary);
		font-size: 0.75rem;
		padding: 6px 12px;
		cursor: pointer;
		transition: border-color var(--transition);
	}

	.disconnect-btn:hover {
		border-color: var(--accent);
	}

	.error {
		color: #ff6b6b;
		font-size: 0.75rem;
		margin-bottom: 8px;
	}
</style>
