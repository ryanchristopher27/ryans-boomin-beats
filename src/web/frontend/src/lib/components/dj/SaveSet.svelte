<script>
	// Save tonight's set (F3f): name it, optionally let the AI write the
	// description, check the stats and songs, then save it to Spotify.
	import { llmConfig } from '../../../stores.js';
	import { createPlaylist } from '$lib/playlistActions.js';
	import { setStats } from '$lib/dj/logic.js';
	import { say } from '$lib/toast.js';
	import SongRow from '../ui/SongRow.svelte';
	import Icon from '../Icon.svelte';

	/** @type {any} */
	export let dj;
	export let onClose = () => {};

	const { setlog } = dj;
	$: songs = $setlog;
	$: stats = setStats(songs);

	const today = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
	let name = `Tonight · ${today}`;
	let description = '';
	let writing = false;
	let saving = false;
	let error = '';

	async function writeRecap() {
		writing = true;
		error = '';
		const r = await dj.request('POST', 'dj/recap/', { json: { songs: songs.slice(-100).map((s) => ({ id: s.id, title: s.title, artist: s.artists[0] ?? '' })) } }).catch(() => null);
		writing = false;
		if (r?.status === 200) description = r.data.recap;
		else error = r?.data?.detail ?? "Couldn't write a recap right now.";
	}

	async function save() {
		saving = true;
		const r = await createPlaylist(name.trim(), songs.map((s) => s.id), description.trim());
		saving = false;
		if (r.ok) {
			say(`Saved ${name.trim()} to Spotify.`);
			onClose();
		} else error = r.error === 'auth' ? 'Log in to Spotify again, then save.' : "Couldn't save the playlist.";
	}

	function newSet() {
		dj.clearSet();
		say('Started a new set.');
		onClose();
	}
</script>

<svelte:window on:keydown={(e) => e.key === 'Escape' && onClose()} />

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div class="overlay" on:click|self={onClose}>
	<div class="modal" role="dialog" aria-modal="true" aria-labelledby="set-title">
		<div class="left">
			<div class="head">
				<h2 id="set-title">Save tonight's set</h2>
				<button class="icon-btn" on:click={onClose} aria-label="Close"><Icon name="x" size={14} /></button>
			</div>
			<label class="field">
				<span>Playlist name</span>
				<input bind:value={name} maxlength="100" autocomplete="off" />
			</label>
			<label class="field">
				<span class="field-row">
					Description
					{#if $llmConfig.connected}
						<button class="link" on:click|preventDefault={writeRecap} disabled={writing || !songs.length}>{writing ? 'Writing…' : description ? 'Rewrite with AI' : 'Write an AI recap'}</button>
					{/if}
				</span>
				<textarea rows="3" bind:value={description} maxlength="300" placeholder="Optional. Shows on the playlist in Spotify." />
			</label>
			<dl class="stats">
				<div><dt>Played</dt><dd class="mono">{stats.minutes} min</dd></div>
				<div><dt>Songs</dt><dd class="mono">{stats.songs}</dd></div>
				<div><dt>DJ picks kept</dt><dd class="mono">{stats.djPicks}</dd></div>
				<div><dt>Guest requests</dt><dd class="mono">{stats.requests}</dd></div>
			</dl>
			{#if error}<p class="error" role="alert">{error}</p>{/if}
			<div class="actions">
				<button class="btn primary" on:click={save} disabled={saving || !songs.length || !name.trim()}>{saving ? 'Saving…' : 'Save to Spotify'}</button>
				<button class="btn" on:click={newSet} disabled={!songs.length}>Start a new set</button>
			</div>
		</div>
		<div class="right">
			<p class="list-head mono">PLAYED ON THIS DEVICE</p>
			{#if songs.length}
				<div class="songs">
					{#each songs as s, i (s.at)}
						<SongRow compact index={i + 1} title={s.title} artists={s.artists} image={s.image} dj={s.dj} duration={s.duration_ms} />
					{/each}
				</div>
			{:else}
				<p class="empty">Songs show up here as they play. Leave the DJ open during the night and they're all kept, even across a reload.</p>
			{/if}
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
		width: min(720px, 100%);
		max-height: min(640px, calc(100vh - 32px));
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		border-radius: 18px;
		background: var(--popover);
		-webkit-backdrop-filter: blur(30px);
		backdrop-filter: blur(30px);
		border: 1px solid var(--border-control);
		box-shadow: var(--shadow-pop);
		overflow: hidden;
		animation: bbin 0.18s var(--ease);
	}

	.left {
		display: flex;
		flex-direction: column;
		gap: 14px;
		padding: 18px 20px 20px;
		overflow-y: auto;
	}

	.head {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	h2 {
		margin: 0;
		font-size: calc(16px * var(--text-scale, 1));
		font-weight: 600;
	}

	.head .icon-btn {
		width: 30px;
		height: 30px;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 6px;
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-muted);
	}

	.field-row {
		display: flex;
		justify-content: space-between;
		gap: 8px;
	}

	input,
	textarea {
		padding: 10px 12px;
		border-radius: 10px;
		border: 1px solid var(--border-control);
		background: rgba(0, 0, 0, 0.35);
		color: var(--text-primary);
		font: inherit;
		font-size: calc(14px * var(--text-scale, 1));
		resize: vertical;
	}

	input:focus,
	textarea:focus {
		outline: none;
		border-color: var(--accent-tint-border);
	}

	.link {
		padding: 0;
		border: none;
		background: none;
		color: var(--accent);
		font: inherit;
		font-weight: 500;
		cursor: pointer;
	}

	.link:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.stats {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
		margin: 0;
	}

	.stats div {
		padding: 10px 12px;
		border-radius: 10px;
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--border-subtle);
	}

	dt {
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	dd {
		margin: 2px 0 0;
		font-size: calc(18px * var(--text-scale, 1));
		font-weight: 500;
	}

	.error {
		margin: 0;
		font-size: calc(13px * var(--text-scale, 1));
		color: var(--danger-text);
	}

	.actions {
		display: flex;
		gap: 8px;
		margin-top: auto;
	}

	.actions .btn {
		flex: 1;
		height: 40px;
	}

	.right {
		display: flex;
		flex-direction: column;
		min-height: 0;
		border-left: 1px solid var(--border-subtle);
		background: rgba(0, 0, 0, 0.15);
	}

	.list-head {
		margin: 0;
		padding: 16px 16px 6px;
		font-size: calc(11px * var(--text-scale, 1));
		letter-spacing: 0.04em;
		color: var(--text-subtle);
	}

	.songs {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding: 0 6px 10px;
	}

	.empty {
		margin: 0;
		padding: 8px 16px;
		font-size: calc(13px * var(--text-scale, 1));
		line-height: 1.5;
		color: var(--text-muted);
	}

	:global([data-bp='phone']) .modal {
		grid-template-columns: minmax(0, 1fr);
		overflow-y: auto;
	}
	:global([data-bp='phone']) .right {
		border-left: none;
		border-top: 1px solid var(--border-subtle);
		max-height: 260px;
	}
</style>
