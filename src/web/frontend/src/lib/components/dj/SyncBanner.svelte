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
		<span class="who warn" title={$sync.error ?? ''}><Icon name="alert" size={16} /> Changes aren't syncing to your other devices.</span>
	</div>
{:else if $sync.status === 'synced' && $sync.primary}
	<div class="banner" role="status">
		{#if $sync.isPrimary}
			<span class="who"><Icon name="broadcast" size={16} /> Driving from this browser</span>
		{:else}
			<span class="who" class:warn={!$sync.primary.online}>
				<Icon name={$sync.primary.online ? 'broadcast' : 'alert'} size={16} />
				{$sync.primary.online ? `Driving from ${$sync.primary.label}` : `${$sync.primary.label} stopped driving`}
			</span>
			<button class="btn small" class:primary={!$sync.primary.online} on:click={claim} disabled={claiming}>
				{claiming ? 'Taking over…' : 'Drive from here'}
			</button>
		{/if}
		{#if $sync.notice}
			<span class="notice">{$sync.notice}</span>
			<button class="btn small" on:click={() => dj.dismissNotice()}>Dismiss</button>
		{/if}
	</div>
{/if}

<style>
	.banner {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
		font-size: 13px;
		color: var(--text-muted);
	}

	.who {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}

	.warn {
		color: var(--warning);
	}

	.notice {
		color: var(--text-primary);
	}
</style>
