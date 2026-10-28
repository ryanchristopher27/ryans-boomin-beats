<script>
	// Who's driving (SY3 on the web): quiet when this tab drives, a clear call
	// to action when another device does, and a warning when it has gone quiet.
	import Icon from '../Icon.svelte';

	/** @type {any} */
	export let dj;
	const { sync } = dj;
	let claiming = false;

	async function claim() {
		claiming = true;
		await dj.claimPrimary();
		claiming = false;
	}
</script>

{#if $sync.status === 'error'}
	<div class="banner" role="status">
		<span class="who warn" title={$sync.error ?? ''}><Icon name="alert" size={14} /> Changes aren't syncing to your other devices.</span>
	</div>
{:else if $sync.status === 'synced' && $sync.primary}
	<div class="banner" role="status">
		{#if $sync.isPrimary}
			<span class="who"><span class="dot live" /> Driving from this browser</span>
		{:else}
			<span class="who" class:warn={!$sync.primary.online}>
				<span class="dot" class:live={$sync.primary.online} class:off={!$sync.primary.online} />
				{$sync.primary.online ? `Driving from ${$sync.primary.label}` : `${$sync.primary.label} stopped driving`}
			</span>
			<button class="drive" class:urgent={!$sync.primary.online} on:click={claim} disabled={claiming}>
				{claiming ? 'Taking over…' : 'Drive from here'}
			</button>
		{/if}
		{#if $sync.notice}
			<span class="notice">{$sync.notice}</span>
			<button class="drive" on:click={() => dj.dismissNotice()}>Dismiss</button>
		{/if}
	</div>
{/if}

<style>
	.banner {
		display: flex;
		align-items: center;
		gap: 8px;
		min-height: 32px;
		padding: 0 4px 0 10px;
		border-radius: 9px;
		background: var(--glass);
		border: 1px solid var(--border-subtle);
		-webkit-backdrop-filter: blur(20px);
		backdrop-filter: blur(20px);
		font-size: 13px;
		color: rgba(243, 243, 245, 0.7);
		white-space: nowrap;
	}

	.who {
		display: inline-flex;
		align-items: center;
		gap: 8px;
	}

	.dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: rgba(243, 243, 245, 0.3);
	}

	.dot.live {
		background: var(--success);
	}

	.dot.off,
	.warn {
		color: var(--warning);
	}

	.dot.off {
		background: var(--warning);
	}

	.drive {
		height: 24px;
		padding: 0 9px;
		border: none;
		border-radius: 6px;
		background: var(--surface-active);
		color: var(--text-primary);
		font: inherit;
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
	}

	.drive.urgent {
		background: var(--accent);
		color: var(--accent-on);
	}

	.drive:disabled {
		opacity: 0.6;
		cursor: default;
	}

	.notice {
		color: var(--text-primary);
		white-space: normal;
	}
</style>
