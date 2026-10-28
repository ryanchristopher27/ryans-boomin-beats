<script>
	import { onMount } from 'svelte';
	import { page, access_token } from '../../stores.js';
	import { getDJ } from '$lib/dj/instance.js';
	import { coverHue } from '$lib/dj/ambience.js';
	import { PRESETS, STORAGE_KEY, WIDGETS, addable, itemsFor, loadLayout, moveLabel } from '$lib/dj/layout.js';
	import Grid from '$lib/components/dj/Grid.svelte';
	import Widget from '$lib/components/dj/Widget.svelte';
	import NowPlaying from '$lib/components/dj/NowPlaying.svelte';
	import Controls from '$lib/components/dj/Controls.svelte';
	import Goal from '$lib/components/dj/Goal.svelte';
	import Moves from '$lib/components/dj/Moves.svelte';
	import UpNext from '$lib/components/dj/UpNext.svelte';
	import Requests from '$lib/components/dj/Requests.svelte';
	import SongProfile from '$lib/components/dj/SongProfile.svelte';
	import Recent from '$lib/components/dj/Recent.svelte';
	import { provideDJContext } from '$lib/components/dj/context.js';
	import { NIGHT, activePreset, applyPreset } from '$lib/dj/presets.js';
	import { page as route } from '$app/stores';
	import { goto } from '$app/navigation';
	import SyncBanner from '$lib/components/dj/SyncBanner.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Blobs from '$lib/components/ui/Blobs.svelte';
	import Bars from '$lib/components/ui/Bars.svelte';

	const dj = /** @type {any} */ (getDJ());
	const { doc, suggestions, player } = dj;
	provideDJContext();
	// Screen-reader feedback for keyboard move/resize.
	let announcement = '';

	function nudge(item, dx, dy, dw, dh) {
		const n = grid.nudge(item.id, dx, dy, dw, dh);
		if (n) announcement = `${titleFor(item)}: column ${n.x + 1}, row ${n.y + 1}, ${n.w} wide, ${n.h} tall.`;
	}

	let layout = loadLayout(read());
	let items = itemsFor(layout);
	let gridKey = 0;
	let editing = false;
	/** @type {any} */
	let grid;
	let before = items;
	let addingSong = false;
	let addMenu;
	let addButton;

	onMount(() => {
		$page = 'DJ';
		// Profile's "Start an evening DJ set" links here with ?preset=pregame.
		const preset = $route.url.searchParams.get('preset');
		if (preset && NIGHT[preset]) {
			applyPreset(dj, preset);
			goto('/dj/', { replaceState: true, noScroll: true });
		}
		return dj.watchSuggestions();
	});

	function read() {
		try {
			return localStorage.getItem(STORAGE_KEY);
		} catch {
			return null;
		}
	}

	function persist() {
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
		} catch {
			/* private mode: the layout lasts for this visit */
		}
	}

	function choose(preset) {
		layout = { ...layout, preset };
		items = itemsFor(layout);
		gridKey++;
		persist();
	}

	function startEditing() {
		before = items.map((i) => ({ ...i }));
		editing = true;
	}

	function cancel() {
		items = before;
		gridKey++;
		editing = false;
	}

	function done() {
		items = grid.save();
		layout = { preset: 'custom', custom: items };
		persist();
		editing = false;
	}

	// The menu is in the top layer; open it under its button.
	function placeMenu(e) {
		if (e.newState !== 'open') return;
		const r = addButton.getBoundingClientRect();
		addMenu.style.top = `${r.bottom + 4}px`;
		addMenu.style.left = `${Math.max(8, r.left)}px`;
	}

	function addWidget(w) {
		addMenu.hidePopover();
		const def = WIDGETS[w.type];
		grid.add({ id: w.id, type: w.type, ...(w.kind ? { kind: w.kind } : {}), x: 0, y: 0, w: def.w, h: def.h });
	}

	function onKey(e) {
		if (editing && e.key === 'Escape' && !document.querySelector(':popover-open')) cancel();
	}

	// Album-art ambience: the page's drifting colour takes the cover's hue and
	// only moves while music plays.
	let hue = 235;
	$: track = $player.state?.track;
	$: playing = !!($player.state?.active && $player.state.is_playing);
	$: if (track) coverHue(track.image, track.title).then((h) => {
		if (track === $player.state?.track) hue = h;
	});

	const titleFor = (item) => (item.type === 'move' ? moveLabel(item.kind) : WIDGETS[item.type].title);
	$: night = activePreset($doc.options);
	$: requestCount = $doc.queue.requests.length;
	$: upNextCount = $doc.queue.sent.length + $doc.queue.upcoming.length;
	$: pickCount = $suggestions.status === 'loaded' ? $suggestions.moves.reduce((n, m) => n + m.tracks.length, 0) : 0;
	$: choices = [...Object.entries(PRESETS).map(([id, p]) => ({ id, label: p.label })), ...(layout.custom ? [{ id: 'custom', label: 'Your layout' }] : [])];
</script>

<svelte:head>
	<title>DJ</title>
	<meta name="description" content="Your AI DJ companion" />
</svelte:head>

<svelte:window on:keydown={onKey} />

<div class="dj-page">
	<Blobs {hue} moving={playing} />
	<div class="bar">
		<h1>DJ</h1>
		<SyncBanner {dj} />
		<div class="spacer" />
		{#if editing}
			<button class="btn" bind:this={addButton} popovertarget="add-widget" disabled={!addable(items).length}><Icon name="plus" size={16} /> Add widget</button>
			<div class="menu" id="add-widget" popover="auto" bind:this={addMenu} on:toggle={placeMenu}>
				{#each addable(items) as w (w.id)}
					<button on:click={() => addWidget(w)}>{w.label}</button>
				{/each}
			</div>
			<button class="btn" on:click={() => { choose('host'); startEditing(); }}>Reset to Host</button>
			<button class="btn" on:click={cancel}>Cancel</button>
			<button class="btn primary" on:click={done}>Done</button>
		{:else}
			<div class="night">
				<span class="night-label" id="night-label">Night</span>
				<div class="segmented" role="radiogroup" aria-labelledby="night-label">
					{#each Object.entries(NIGHT) as [id, p] (id)}
						<button role="radio" aria-checked={night === id} class:active={night === id} on:click={() => applyPreset(dj, id)} title="{p.label}: sets how bold the DJ is and its goal">{p.label}</button>
					{/each}
				</div>
			</div>
			<div class="segmented" role="radiogroup" aria-label="Layout">
				{#each choices as c (c.id)}
					<button role="radio" aria-checked={layout.preset === c.id} class:active={layout.preset === c.id} on:click={() => choose(c.id)}>{c.label}</button>
				{/each}
			</div>
			<button class="btn" on:click={startEditing}><Icon name="layout" size={16} /> Edit layout</button>
		{/if}
	</div>

	{#if !$access_token}
		<div class="signin">
			<p>Sign in with Spotify to start the DJ.</p>
			<a class="btn primary" href="/profile/">Go to Profile</a>
		</div>
	{:else}
		{#key gridKey}
			<Grid bind:this={grid} bind:items {editing} fill let:item>
				<Widget title={titleFor(item)} {editing} onRemove={() => grid.remove(item.id)} onNudge={(dx, dy, dw, dh) => nudge(item, dx, dy, dw, dh)}>
					<svelte:fragment slot="badge">
						{#if item.type === 'requests' && requestCount}
							<span class="badge mono" aria-label="{requestCount} pending">{requestCount}</span>
						{:else if item.type === 'nowPlaying' && playing}
							<Bars count={3} height={10} />
						{:else if item.type === 'moves' && pickCount}
							<span class="count mono">{pickCount} picks</span>
						{:else if item.type === 'upNext' && upNextCount}
							<span class="count mono">{upNextCount}</span>
						{/if}
					</svelte:fragment>
					<svelte:fragment slot="actions">
						{#if item.type === 'moves'}
							<button class="icon-btn" on:click={() => dj.loadSuggestions(undefined, true)} disabled={$suggestions.status === 'loading'} aria-label="Refresh moves" title="Refresh moves">
								<Icon name="refresh" size={16} />
							</button>
						{:else if item.type === 'upNext'}
							<button class="btn small" class:primary={addingSong} on:click={() => (addingSong = !addingSong)} aria-expanded={addingSong}>
								<Icon name={addingSong ? 'x' : 'search'} size={14} /> {addingSong ? 'Close' : 'Add song'}
							</button>
						{/if}
					</svelte:fragment>

					{#if item.type === 'nowPlaying'}
						<NowPlaying {dj} />
					{:else if item.type === 'controls'}
						<Controls {dj} withGoal={!items.some((i) => i.type === 'goal')} />
					{:else if item.type === 'goal'}
						<Goal {dj} />
					{:else if item.type === 'moves'}
						<Moves {dj} />
					{:else if item.type === 'move'}
						<Moves {dj} kind={item.kind} />
					{:else if item.type === 'upNext'}
						<UpNext {dj} adding={addingSong} />
					{:else if item.type === 'requests'}
						<Requests {dj} />
					{:else if item.type === 'profile'}
						<SongProfile {dj} />
					{:else if item.type === 'recent'}
						<Recent {dj} />
					{/if}
				</Widget>
			</Grid>
		{/key}
		{#if editing}
			<p class="edit-hint">Drag a widget by its header, resize from its corner, or focus its handle and use the arrow keys (Shift resizes). Esc cancels.</p>
		{/if}
	{/if}

	<p class="sr-only" aria-live="polite">{announcement}</p>
</div>

<style>
	/* Full bleed under the page padding, so the drifting colour reaches the edges. */
	.dj-page {
		position: relative;
		min-width: 0;
		min-height: calc(100vh - var(--header-height));
		margin: calc(var(--primary-spacing) * -1);
		padding: 16px 20px 0;
		overflow: hidden;
	}

	.dj-page > :global(:not(.blobs)) {
		position: relative;
		z-index: 1;
	}

	.bar {
		display: flex;
		align-items: center;
		gap: 10px;
		min-height: 36px;
		margin-bottom: 7px;
		flex-wrap: wrap;
	}

	h1 {
		margin: 0 4px 0 0;
		font-size: calc(24px * var(--text-scale, 1));
		font-weight: 700;
		letter-spacing: -0.02em;
	}

	.spacer {
		flex: 1;
	}

	.bar .segmented,
	.bar .btn {
		-webkit-backdrop-filter: blur(20px);
		backdrop-filter: blur(20px);
	}

	.bar .segmented {
		padding: 2px;
		border-radius: 9px;
		border-color: var(--border-subtle);
	}

	.bar .segmented button {
		height: 28px;
		padding: 0 11px;
		font-size: calc(12px * var(--text-scale, 1));
	}

	.bar .btn {
		height: 32px;
		padding: 0 12px;
		border-color: var(--border-control);
		background: var(--glass);
	}

	.bar .btn.primary {
		background: var(--accent);
	}

	.night {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.night-label {
		font-size: calc(12px * var(--text-scale, 1));
		color: rgba(243, 243, 245, 0.5);
	}

	.badge {
		min-width: 18px;
		height: 18px;
		padding: 0 5px;
		border-radius: 999px;
		background: var(--danger);
		color: #1a0505;
		font-size: calc(11px * var(--text-scale, 1));
		font-weight: 600;
		display: inline-grid;
		place-items: center;
	}

	.count {
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.menu {
		position: fixed;
		inset: auto;
		margin: 0;
		padding: 4px;
		min-width: 200px;
		background: var(--popover);
		-webkit-backdrop-filter: blur(30px);
		backdrop-filter: blur(30px);
		color: var(--text-primary);
		border: 1px solid var(--border-control);
		border-radius: 12px;
		box-shadow: var(--shadow-pop);
	}

	.menu button {
		display: block;
		width: 100%;
		text-align: left;
		padding: 8px 10px;
		border: none;
		background: none;
		color: inherit;
		font: inherit;
		font-size: calc(13px * var(--text-scale, 1));
		border-radius: 8px;
		cursor: pointer;
	}

	.menu button:hover {
		background: var(--hover);
	}

	.signin {
		margin: 80px auto;
		text-align: center;
		color: var(--text-muted);
	}

	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
		white-space: nowrap;
	}

	.edit-hint {
		margin: 10px 0 0;
		font-size: calc(12px * var(--text-scale, 1));
		color: var(--text-muted);
		text-align: center;
	}

	@media (max-width: 759px) {
		.dj-page {
			padding: 12px 12px 0;
		}
	}
</style>
