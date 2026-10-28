<script>
	export let onSave = (name) => {};
	export let onCancel = () => {};
	/** A suggested name, selected so typing replaces it. */
	export let initial = '';

	let name = initial;

	function select(node) {
		node.focus();
		node.select();
	}

	function handleKeydown(e) {
		if (e.key === 'Enter' && name.trim()) onSave(name.trim());
		if (e.key === 'Escape') onCancel();
	}
</script>

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div class="overlay" on:click|self={onCancel}>
	<div class="modal" role="dialog" aria-modal="true" aria-labelledby="name-title">
		<h2 id="name-title">Name your playlist</h2>
		<input type="text" placeholder="Playlist name" aria-label="Playlist name" bind:value={name} on:keydown={handleKeydown} use:select />
		<div class="actions">
			<button class="btn" on:click={onCancel}>Cancel</button>
			<button class="btn primary" on:click={() => onSave(name.trim())} disabled={!name.trim()}>Save to Spotify</button>
		</div>
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		z-index: 80;
		display: grid;
		place-items: center;
		padding: 16px;
		background: rgba(5, 5, 7, 0.6);
	}

	.modal {
		width: min(420px, 100%);
		display: flex;
		flex-direction: column;
		gap: 16px;
		padding: 20px;
		border-radius: 18px;
		background: var(--popover);
		-webkit-backdrop-filter: blur(30px);
		backdrop-filter: blur(30px);
		border: 1px solid var(--border-control);
		box-shadow: var(--shadow-pop);
		animation: bbin 0.18s var(--ease);
	}

	h2 {
		margin: 0;
		font-size: calc(16px * var(--text-scale, 1));
		font-weight: 600;
	}

	input {
		height: 42px;
		padding: 0 12px;
		border-radius: 10px;
		border: 1px solid var(--border-control);
		background: rgba(0, 0, 0, 0.35);
		color: var(--text-primary);
		font-size: calc(15px * var(--text-scale, 1));
	}

	input:focus {
		outline: none;
		border-color: var(--accent-tint-border);
	}

	.actions {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
	}
</style>
