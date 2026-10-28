<script>
	import { toast, dismiss } from '$lib/toast.js';

	function undo() {
		$toast?.undo?.();
		dismiss();
	}
</script>

<div class="region" role="status" aria-live="polite">
	{#if $toast}
		{#key $toast.id}
			<div class="toast">
				<span>{$toast.text}</span>
				{#if $toast.undo}<button on:click={undo}>Undo</button>{/if}
			</div>
		{/key}
	{/if}
</div>

<style>
	.region {
		position: fixed;
		left: 50%;
		bottom: calc(var(--mini-h, 0px) + 16px);
		transform: translateX(-50%);
		z-index: 70;
		pointer-events: none;
	}

	.toast {
		display: flex;
		align-items: center;
		gap: 14px;
		height: 40px;
		padding: 0 8px 0 16px;
		border-radius: 999px;
		background: #f3f3f5;
		color: #0a0a0c;
		font-size: calc(13px * var(--text-scale, 1));
		font-weight: 500;
		white-space: nowrap;
		box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
		pointer-events: auto;
		animation: bbin 0.2s var(--ease);
	}

	.toast:not(:has(button)) {
		padding-right: 16px;
	}

	button {
		height: 28px;
		padding: 0 12px;
		border: none;
		border-radius: 999px;
		background: #0a0a0c;
		color: #f3f3f5;
		font: inherit;
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 600;
		cursor: pointer;
	}
</style>
