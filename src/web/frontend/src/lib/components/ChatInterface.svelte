<script>
	import { PUBLIC_API_URL } from '$env/static/public';
	import { chatMessages, generatedPlaylist, llmConfig } from '../../stores.js';

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
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
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
		background-color: var(--color-dark-gray);
		border-radius: 20px;
		padding: 16px;
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
		border-radius: 12px;
		font-size: 0.85rem;
		max-width: 80%;
	}

	.user-message {
		background-color: var(--color-light-blue);
		color: var(--color-dark-gray);
		align-self: flex-end;
		font-weight: 600;
	}

	.assistant-message {
		border: 1px solid var(--color-light-blue);
		color: var(--color-light-blue);
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
		background-color: var(--color-dark-gray);
		color: var(--color-light-blue);
		border: 2px solid var(--color-light-blue);
		border-radius: 10px;
		padding: 8px 12px;
		font-size: 0.85rem;
		resize: none;
		font-family: inherit;
	}

	.prompt-input::placeholder {
		color: rgba(94, 201, 255, 0.5);
	}

	.send-btn {
		height: 40px;
		width: 40px;
		background-color: var(--color-light-blue);
		color: var(--color-dark-gray);
		border: 2px solid var(--color-light-blue);
		border-radius: 10px;
		font-size: 1.1rem;
		font-weight: 700;
		cursor: pointer;
		flex-shrink: 0;
	}

	.send-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.send-btn:hover:not(:disabled) {
		border-color: var(--color-purple);
	}

	.settings-bar {
		display: flex;
		gap: 16px;
		align-items: center;
		margin-bottom: 12px;
		padding: 8px 12px;
		background-color: rgba(94, 201, 255, 0.05);
		border: 1px solid rgba(94, 201, 255, 0.15);
		border-radius: 10px;
	}

	.setting {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.setting-label {
		font-size: 0.75rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: rgba(94, 201, 255, 0.6);
	}

	.count-input {
		width: 56px;
		background-color: var(--color-dark-gray);
		color: var(--color-light-blue);
		border: 1px solid rgba(94, 201, 255, 0.4);
		border-radius: 6px;
		padding: 4px 8px;
		font-size: 0.85rem;
		text-align: center;
	}

	.count-input:focus {
		outline: none;
		border-color: var(--color-light-blue);
	}

	.error {
		color: #ff6b6b;
		font-size: 0.8rem;
		margin-bottom: 10px;
	}
</style>
