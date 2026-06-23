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
		background-color: var(--surface-1);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-lg);
		padding: 24px;
		width: 340px;
	}

	.modal-title {
		font-size: 1rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 16px;
		text-align: center;
	}

	.name-input {
		width: 100%;
		box-sizing: border-box;
		background-color: var(--surface-0);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		padding: 10px 12px;
		font-size: 0.9rem;
		margin-bottom: 16px;
		transition: border-color var(--transition);
	}

	.name-input::placeholder {
		color: var(--text-subtle);
	}

	.name-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.actions {
		display: flex;
		gap: 10px;
		justify-content: flex-end;
	}

	.cancel-btn {
		height: 36px;
		padding: 0 16px;
		background-color: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		color: var(--text-primary);
		font-size: 0.8rem;
		cursor: pointer;
		transition: border-color var(--transition);
	}

	.cancel-btn:hover {
		border-color: var(--accent);
	}

	.save-btn {
		height: 36px;
		padding: 0 16px;
		background: var(--brand-gradient);
		border: none;
		border-radius: var(--radius-sm);
		color: var(--surface-0);
		font-weight: 700;
		font-size: 0.8rem;
		cursor: pointer;
		transition: filter var(--transition);
	}

	.save-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.save-btn:hover:not(:disabled) {
		filter: brightness(1.1);
	}
</style>
