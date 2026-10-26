<script>
	import Icon from './Icon.svelte';
	import Goal from './Goal.svelte';

	/** @type {any} */
	export let dj;
	/** Show the goal here when there's no separate Goal widget. */
	export let withGoal = false;
	const { doc } = dj;

	const MODES = [
		{ id: 'whisper', label: 'Whisper', summary: 'Suggests only when you ask.' },
		{ id: 'copilot', label: 'Co-pilot', summary: 'Always has moves ready; you pick.' },
		{ id: 'autofill', label: 'Autofill', summary: 'Adds a pick when the queue runs dry. Remove it to veto.' },
		{ id: 'driver', label: 'Driver', summary: 'Keeps 3 songs lined up, choosing the moves itself. Set a goal to steer it.' }
	];

	$: o = $doc.options;
	$: mode = MODES.find((m) => m.id === o.mode) ?? MODES[1];
	$: avoiding = o.avoidTracks.length + o.avoidArtists.length;
	// The slider moves freely; the DJ re-asks only when it's released.
	let draft = null;
	$: bold = draft ?? o.adventurousness;
</script>

<div class="controls">
	<div class="segmented" role="radiogroup" aria-label="DJ control">
		{#each MODES as m}
			<button role="radio" aria-checked={o.mode === m.id} class:active={o.mode === m.id} on:click={() => dj.setMode(m.id)}>{m.label}</button>
		{/each}
	</div>
	<p class="hint">{mode.summary}</p>

	<label class="slider">
		<span>Safe</span>
		<input
			type="range"
			min="0"
			max="1"
			step="0.05"
			value={bold}
			aria-label="Safe to bold"
			on:input={(e) => (draft = +e.currentTarget.value)}
			on:change={(e) => {
				dj.setAdventurousness(+e.currentTarget.value);
				draft = null;
			}}
		/>
		<span>Bold</span>
	</label>

	<label class="toggle">
		<input type="checkbox" checked={o.clean} on:change={(e) => dj.setClean(e.currentTarget.checked)} />
		<span>Clean only</span>
	</label>

	{#if withGoal}
		<div class="docked"><Goal {dj} /></div>
	{/if}

	{#if avoiding}
		<details class="avoid">
			<summary>Avoiding {o.avoidTracks.length ? `${o.avoidTracks.length} song${o.avoidTracks.length > 1 ? 's' : ''}` : ''}{o.avoidTracks.length && o.avoidArtists.length ? ', ' : ''}{o.avoidArtists.length ? `${o.avoidArtists.length} artist${o.avoidArtists.length > 1 ? 's' : ''}` : ''}</summary>
			<ul>
				{#each o.avoidTracks as t (t.id)}
					<li>
						<span>{t.title} <span class="muted">· {t.artist}</span></span>
						<button class="icon-btn" on:click={() => dj.unavoid({ track: t.id })} aria-label="Allow {t.title} again"><Icon name="x" size={14} /></button>
					</li>
				{/each}
				{#each o.avoidArtists as a (a)}
					<li>
						<span>{a}</span>
						<button class="icon-btn" on:click={() => dj.unavoid({ artist: a })} aria-label="Allow {a} again"><Icon name="x" size={14} /></button>
					</li>
				{/each}
			</ul>
		</details>
	{/if}
</div>

<style>
	.controls {
		padding: 14px 16px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.docked {
		margin: 2px -16px 0;
		border-top: 1px solid var(--border-subtle);
	}

	.hint {
		margin: -4px 0 0;
		font-size: 13px;
		line-height: 1.45;
		color: var(--text-muted);
	}

	.slider {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 13px;
		color: var(--text-muted);
	}

	.slider input {
		flex: 1;
		accent-color: var(--accent);
	}

	.toggle {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 14px;
		cursor: pointer;
	}

	.toggle input {
		width: 16px;
		height: 16px;
		accent-color: var(--accent);
	}

	.avoid summary {
		font-size: 13px;
		color: var(--text-muted);
		cursor: pointer;
	}

	.avoid ul {
		list-style: none;
		margin: 8px 0 0;
		padding: 0;
	}

	.avoid li {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		font-size: 13px;
		padding: 2px 0;
	}

	.muted {
		color: var(--text-muted);
	}
</style>
