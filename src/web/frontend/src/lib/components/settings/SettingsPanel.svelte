<script>
	// The gear popover (F1): General and AI tabs, saved on this device.
	import { onMount } from 'svelte';
	import { llmConfig, access_token } from '../../../stores.js';
	import { compactRows, duckPreview, playbackMotion, resetSettings, settingsTab, textScale, TEXT_SCALES } from '$lib/settings.js';
	import { PROVIDERS } from '$lib/llm.js';
	import { onboarding } from '$lib/onboarding.js';
	import { logoutSpotify } from '$lib/spotifyAuth.js';
	import { getDJ } from '$lib/dj/instance.js';
	import { nameHue } from '$lib/dj/ambience.js';
	import AiForm from './AiForm.svelte';
	import Icon from '../Icon.svelte';

	export let onClose = () => {};

	const dj = getDJ();
	const doc = dj?.doc;
	// Clean only is the DJ's synced option, so one switch covers every device.
	$: clean = !!$doc?.options.clean;

	$: connectedName = PROVIDERS.find((p) => p.id === $llmConfig.provider)?.label ?? $llmConfig.provider;

	// The account row: who's signed in, straight from Spotify (no backend call).
	let me = null;
	onMount(async () => {
		if (!$access_token) return;
		try {
			const res = await fetch('https://api.spotify.com/v1/me', { headers: { Authorization: `Bearer ${$access_token}` } });
			if (res.ok) me = await res.json();
		} catch {
			/* the row falls back to "Spotify connected" */
		}
	});
	$: initials = (me?.display_name ?? '').split(/\s+/).slice(0, 2).map((w) => w[0] ?? '').join('').toUpperCase();

	function logOut() {
		logoutSpotify();
		onClose();
		$onboarding = 1;
	}

	const pct = (v) => `${Math.round(v * 100)}%`;
</script>

<svelte:window on:keydown={(e) => e.key === 'Escape' && onClose()} />

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div class="scrim" on:click={onClose} />
<div class="popover" role="dialog" aria-label="Settings">
	<div class="head">
		<h2>Settings</h2>
		<div class="tabs" role="tablist" aria-label="Settings sections">
			<button role="tab" aria-selected={$settingsTab === 'general'} class:active={$settingsTab === 'general'} on:click={() => ($settingsTab = 'general')}>General</button>
			<button role="tab" aria-selected={$settingsTab === 'ai'} class:active={$settingsTab === 'ai'} on:click={() => ($settingsTab = 'ai')}>
				<span class="dot" class:connected={$llmConfig.connected} /> AI
			</button>
		</div>
		<button class="icon-btn" on:click={onClose} aria-label="Close settings"><Icon name="x" size={14} /></button>
	</div>

	<div class="body">
		{#if $settingsTab === 'general'}
			<p class="section mono">DISPLAY</p>
			<div class="size">
				<div class="size-head">
					<div class="label"><span class="title">Text size</span><span class="sub">Smaller fits more songs on each page.</span></div>
					<span class="value mono">{pct($textScale)}</span>
				</div>
				<div class="sizes" role="radiogroup" aria-label="Text size">
					{#each TEXT_SCALES as s}
						<button role="radio" aria-checked={$textScale === s} class:active={$textScale === s} class="mono" on:click={() => ($textScale = s)}>{pct(s)}</button>
					{/each}
				</div>
			</div>
			<label class="toggle">
				<span class="label"><span class="title">Compact song rows</span><span class="sub">Smaller covers and tighter spacing in every list.</span></span>
				<input class="switch" type="checkbox" role="switch" bind:checked={$compactRows} />
			</label>

			<p class="section mono">PLAYBACK</p>
			<label class="toggle">
				<span class="label"><span class="title">Clean only</span><span class="sub">Skip explicit songs in DJ picks, playlists and recommendations.</span></span>
				<input class="switch" type="checkbox" role="switch" checked={clean} disabled={!dj} on:change={(e) => dj?.setClean(e.currentTarget.checked)} />
			</label>
			<label class="toggle">
				<span class="label"><span class="title">Lower Spotify while previewing</span><span class="sub">Drops Spotify's volume to about 20% during a preview, then restores it.</span></span>
				<input class="switch" type="checkbox" role="switch" bind:checked={$duckPreview} />
			</label>

			<p class="section mono">MOTION</p>
			<label class="toggle">
				<span class="label"><span class="title">Playback animations</span><span class="sub">Visualizer, glowing covers and moving colour while music plays.</span></span>
				<input class="switch" type="checkbox" role="switch" bind:checked={$playbackMotion} />
			</label>

			{#if $access_token}
				<p class="section mono">ACCOUNT</p>
				<div class="account">
					{#if me?.images?.[0]?.url}
						<img class="avatar" src={me.images[0].url} alt="" width="36" height="36" />
					{:else}
						<span class="avatar blank" style:--h={nameHue(me?.display_name ?? '')}>{initials}</span>
					{/if}
					<div class="who">
						<span class="title">{me?.display_name ?? 'Your Spotify account'}</span>
						<span class="sub"><span class="dot connected" /> Spotify connected</span>
					</div>
					<button class="btn small" on:click={logOut}>Log out</button>
				</div>
			{/if}
		{:else}
			<div class="status" class:connected={$llmConfig.connected}>
				<span class="dot" class:connected={$llmConfig.connected} />
				<div>
					<p class="title">{$llmConfig.connected ? `${connectedName} connected` : 'Connect an AI'}</p>
					<p class="sub">
						{$llmConfig.connected
							? 'Powers song analysis, playlists and DJ moves. Your key stays on this device.'
							: 'Add one for song analysis, playlists and DJ moves. Your key stays on this device.'}
					</p>
				</div>
			</div>
			<p class="section mono">PROVIDER</p>
			<AiForm onConnected={onClose} />
		{/if}
	</div>

	<div class="foot">
		<span>Saved on this device</span>
		{#if $settingsTab === 'general'}<button class="btn small" on:click={resetSettings}>Reset to defaults</button>{/if}
	</div>
</div>

<style>
	.scrim {
		position: fixed;
		inset: 0;
		z-index: 60;
	}

	.popover {
		position: fixed;
		z-index: 61;
		top: calc(var(--header-height) + 8px);
		right: 16px;
		width: 380px;
		max-height: calc(100vh - var(--header-height) - 24px);
		display: flex;
		flex-direction: column;
		border-radius: 18px;
		background: var(--popover);
		-webkit-backdrop-filter: blur(30px);
		backdrop-filter: blur(30px);
		border: 1px solid var(--border-control);
		box-shadow: var(--shadow-pop);
		overflow: hidden;
		animation: bbin 0.18s var(--ease);
	}

	.head {
		flex: none;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 12px 10px 12px 16px;
		border-bottom: 1px solid var(--border-subtle);
	}

	h2 {
		flex: 1;
		margin: 0;
		font-size: calc(15px * var(--text-scale, 1));
		font-weight: 600;
	}

	.tabs {
		display: flex;
		padding: 2px;
		border-radius: 9px;
		background: rgba(0, 0, 0, 0.35);
	}

	.tabs button {
		height: 28px;
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 0 12px;
		border: none;
		border-radius: 7px;
		background: none;
		color: var(--text-muted);
		font: inherit;
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		cursor: pointer;
	}

	.tabs button.active {
		background: var(--surface-active);
		color: var(--text-primary);
	}

	.head .icon-btn {
		width: 30px;
		height: 30px;
	}

	.dot {
		flex: none;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: rgba(243, 243, 245, 0.3);
	}

	.dot.connected {
		background: var(--success);
	}

	.body {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding: 0 16px 8px;
		overscroll-behavior: contain;
	}

	.section {
		margin: 0;
		padding: 16px 0 4px;
		font-size: calc(11px * var(--text-scale, 1));
		font-weight: 500;
		letter-spacing: 0.04em;
		color: var(--text-subtle);
	}

	.label,
	.who {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.title {
		margin: 0;
		font-size: calc(14px * var(--text-scale, 1));
		font-weight: 500;
	}

	.sub {
		display: flex;
		align-items: center;
		gap: 6px;
		margin: 0;
		font-size: calc(12px * var(--text-scale, 1));
		line-height: 1.4;
		color: rgba(243, 243, 245, 0.55);
	}

	.size {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 8px 0 14px;
	}

	.size-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 12px;
	}

	.value {
		font-size: calc(13px * var(--text-scale, 1));
		font-weight: 500;
		color: var(--accent);
	}

	.sizes {
		display: grid;
		grid-template-columns: repeat(5, 1fr);
		padding: 2px;
		border-radius: 9px;
		background: rgba(0, 0, 0, 0.35);
	}

	.sizes button {
		height: 30px;
		border: none;
		border-radius: 7px;
		background: none;
		color: var(--text-muted);
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 500;
		cursor: pointer;
	}

	.sizes button.active {
		background: var(--surface-active);
		color: var(--text-primary);
	}

	.toggle {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 0;
		border-top: 1px solid rgba(255, 255, 255, 0.06);
		cursor: pointer;
	}

	/* A 36×22 switch with a 16px knob. */
	.switch {
		appearance: none;
		flex: none;
		position: relative;
		width: 36px;
		height: 22px;
		margin: 0;
		border-radius: 999px;
		background: rgba(255, 255, 255, 0.16);
		cursor: pointer;
		transition: background-color var(--transition);
	}

	.switch::after {
		content: '';
		position: absolute;
		top: 3px;
		left: 3px;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		background: #fff;
		transition: transform 0.15s var(--ease);
	}

	.switch:checked {
		background: var(--accent);
	}

	.switch:checked::after {
		transform: translateX(14px);
	}

	.switch:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.account {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 0 12px;
		border-top: 1px solid rgba(255, 255, 255, 0.06);
	}

	.avatar {
		flex: none;
		width: 36px;
		height: 36px;
		border-radius: 50%;
		object-fit: cover;
	}

	.avatar.blank {
		display: grid;
		place-items: center;
		background: linear-gradient(140deg, oklch(0.62 0.1 var(--h)), oklch(0.32 0.08 calc(var(--h) + 50)));
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 600;
	}

	.status {
		display: flex;
		align-items: center;
		gap: 10px;
		margin: 14px 0 10px;
		padding: 12px;
		border-radius: 12px;
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid rgba(255, 255, 255, 0.08);
	}

	.status.connected {
		background: rgba(74, 222, 128, 0.06);
		border-color: rgba(74, 222, 128, 0.2);
	}

	.status .dot {
		width: 8px;
		height: 8px;
	}

	.foot {
		flex: none;
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 10px;
		padding: 10px 16px;
		border-top: 1px solid var(--border-subtle);
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.foot .btn {
		height: 28px;
		font-size: calc(12px * var(--text-scale, 1));
	}

	:global([data-bp='phone']) .popover {
		top: auto;
		left: 8px;
		right: 8px;
		bottom: calc(8px + env(safe-area-inset-bottom, 0px));
		width: auto;
		max-height: 82vh;
	}
</style>
