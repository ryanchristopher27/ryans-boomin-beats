<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import { chatMessages, generatedPlaylist, llmConfig } from '../../stores.js';
	import { llmHeaders } from '../llmHeaders.js';

	export let onResult = (data) => {};

	let prompt = '';
	let loading = false;
	let errorMsg = '';
	let songCount = 10;

	let messagesEl;

	async function send() {
		if (!prompt.trim() || loading) return;

		const userMessage = { role: 'user', content: prompt };
		$chatMessages = [...$chatMessages, userMessage];
		const currentPrompt = prompt;
		prompt = '';
		loading = true;
		errorMsg = '';

		try {
			const res = await fetch(`${PUBLIC_API_URL}/llm/generate-playlist/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', ...llmHeaders() },
				body: JSON.stringify({
					prompt: currentPrompt,
					messages: $chatMessages.slice(0, -1),
					count: songCount,
				}),
			});

			if (res.status === 401) {
				errorMsg = 'Connect your AI account first using the settings icon in the header.';
				return;
			}

			const data = await res.json();
			$chatMessages = data.messages;
			$generatedPlaylist = data.playlist;
			onResult(data);
		} catch (e) {
			errorMsg = 'Something went wrong. Make sure the backend is running.';
		} finally {
			loading = false;
		}
	}

	function handleKeydown(e) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	}

	$: if (messagesEl && $chatMessages.length) {
		setTimeout(() => { messagesEl.scrollTop = messagesEl.scrollHeight; }, 0);
	}
</script>

<div class="chat-container">
	{#if $chatMessages.length > 0}
		<div class="messages" bind:this={messagesEl}>
			{#each $chatMessages as msg}
				{#if msg.role === 'user'}
					<div class="message user-message">{msg.content}</div>
				{:else}
					<div class="message assistant-message">
						{#if loading}
							Generating playlist...
						{:else}
							Playlist updated ✓
						{/if}
					</div>
				{/if}
			{/each}
			{#if loading}
				<div class="message assistant-message loading">Thinking...</div>
			{/if}
		</div>
	{/if}

	<div class="settings-bar">
		<label class="setting">
			<span class="setting-label">Songs</span>
			<input
				class="count-input"
				type="number"
				min="1"
				max="50"
				bind:value={songCount}
				disabled={loading}
			/>
		</label>
	</div>

	{#if errorMsg}
		<div class="error">{errorMsg}</div>
	{/if}

	<div class="input-row">
		<textarea
			class="prompt-input"
			placeholder="Describe your playlist… (e.g. 'late night jazz for studying')"
			bind:value={prompt}
			on:keydown={handleKeydown}
			rows="2"
			disabled={loading}
		></textarea>
		<button class="send-btn" on:click={send} disabled={!prompt.trim() || loading}>
			{loading ? '...' : '→'}
		</button>
	</div>
</div>

<style>
	.chat-container {
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-lg);
		padding: 18px;
		margin-bottom: 20px;
	}

	.messages {
		max-height: 220px;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-bottom: 12px;
	}

	.message {
		padding: 8px 14px;
		border-radius: var(--radius);
		font-size: 0.85rem;
		max-width: 80%;
	}

	.user-message {
		background: var(--brand-gradient);
		color: var(--surface-0);
		align-self: flex-end;
		font-weight: 600;
	}

	.assistant-message {
		background-color: var(--surface-2);
		color: var(--text-muted);
		align-self: flex-start;
	}

	.loading {
		opacity: 0.6;
	}

	.input-row {
		display: flex;
		gap: 10px;
		align-items: flex-end;
	}

	.prompt-input {
		flex: 1;
		background-color: var(--surface-0);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		padding: 10px 14px;
		font-size: 0.85rem;
		resize: none;
		font-family: inherit;
		transition: border-color var(--transition);
	}

	.prompt-input::placeholder {
		color: var(--text-subtle);
	}

	.prompt-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.send-btn {
		height: 44px;
		width: 44px;
		background: var(--brand-gradient);
		color: var(--surface-0);
		border: none;
		border-radius: var(--radius);
		font-size: 1.1rem;
		font-weight: 700;
		cursor: pointer;
		flex-shrink: 0;
		transition: filter var(--transition);
	}

	.send-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.send-btn:hover:not(:disabled) {
		filter: brightness(1.1);
	}

	.settings-bar {
		display: flex;
		gap: 16px;
		align-items: center;
		margin-bottom: 12px;
		padding: 10px 14px;
		background-color: var(--surface-0);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
	}

	.setting {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.setting-label {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-subtle);
	}

	.count-input {
		width: 56px;
		background-color: var(--surface-1);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		padding: 4px 8px;
		font-size: 0.85rem;
		text-align: center;
		transition: border-color var(--transition);
	}

	.count-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.error {
		color: #ff6b6b;
		font-size: 0.8rem;
		margin-bottom: 10px;
	}
</style>
