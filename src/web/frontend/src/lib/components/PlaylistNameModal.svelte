<script>
	export let onSave = (name) => {};
	export let onCancel = () => {};

	let name = '';

	function handleKeydown(e) {
		if (e.key === 'Enter' && name.trim()) onSave(name.trim());
		if (e.key === 'Escape') onCancel();
	}
</script>

<div class="overlay" on:click|self={onCancel}>
	<div class="modal">
		<div class="modal-title">Name your playlist</div>
		<input
			class="name-input"
			type="text"
			placeholder="Playlist name..."
			bind:value={name}
			on:keydown={handleKeydown}
			autofocus
		/>
		<div class="actions">
			<button class="cancel-btn" on:click={onCancel}>Cancel</button>
			<button class="save-btn" on:click={() => onSave(name.trim())} disabled={!name.trim()}>
				Save to Spotify
			</button>
		</div>
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}

	.modal {
		background-color: var(--color-dark-gray);
		border: 2px solid var(--color-light-blue);
		border-radius: 16px;
		padding: 24px;
		width: 340px;
	}

	.modal-title {
		font-size: 1rem;
		font-weight: 700;
		color: var(--color-light-blue);
		margin-bottom: 16px;
		text-align: center;
	}

	.name-input {
		width: 100%;
		box-sizing: border-box;
		background-color: var(--color-dark-gray);
		color: var(--color-light-blue);
		border: 2px solid var(--color-light-blue);
		border-radius: 8px;
		padding: 8px 12px;
		font-size: 0.9rem;
		margin-bottom: 16px;
	}

	.actions {
		display: flex;
		gap: 10px;
		justify-content: flex-end;
	}

	.cancel-btn {
		height: 34px;
		padding: 0 16px;
		background: none;
		border: 2px solid var(--color-light-blue);
		border-radius: 8px;
		color: var(--color-light-blue);
		font-size: 0.8rem;
		cursor: pointer;
	}

	.cancel-btn:hover {
		border-color: var(--color-purple);
		color: var(--color-purple);
	}

	.save-btn {
		height: 34px;
		padding: 0 16px;
		background-color: var(--color-light-blue);
		border: 2px solid var(--color-light-blue);
		border-radius: 8px;
		color: var(--color-dark-gray);
		font-weight: 700;
		font-size: 0.8rem;
		cursor: pointer;
	}

	.save-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.save-btn:hover:not(:disabled) {
		border-color: var(--color-purple);
	}
</style>
