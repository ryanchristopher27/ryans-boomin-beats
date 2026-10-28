<script>
	import Icon from '../Icon.svelte';
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
	let famDraft = null;
	$: familiar = famDraft ?? o.familiar ?? 0.5;
	$: famLabel = familiar < 0.34 ? 'From your library' : familiar < 0.67 ? 'Mix' : 'Mostly new';
</script>

<div class="controls">
	<div class="segmented" role="radiogroup" aria-label="DJ control">
		{#each MODES as m}
			<button role="radio" aria-checked={o.mode === m.id} class:active={o.mode === m.id} on:click={() => dj.setMode(m.id)}>{m.label}</button>
		{/each}
	</div>
	<p class="hint">{mode.summary}</p>

	<label class="slider">
		<span class="ends"><span>Safe</span><span>Bold</span></span>
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
	</label>

	<label class="slider">
		<span class="ends"><span>Familiar</span><span class="mid mono">{famLabel}</span><span>New</span></span>
		<input
			type="range"
			min="0"
			max="1"
			step="0.05"
			value={familiar}
			aria-label="Familiar to new"
			aria-valuetext={famLabel}
			on:input={(e) => (famDraft = +e.currentTarget.value)}
			on:change={(e) => {
				dj.setFamiliar(+e.currentTarget.value);
				famDraft = null;
			}}
		/>
	</label>

	<label class="toggle">
		<span class="toggle-text">Clean only <span class="sub">Skip explicit songs in picks</span></span>
		<input class="switch" type="checkbox" role="switch" checked={o.clean} on:change={(e) => dj.setClean(e.currentTarget.checked)} />
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
		padding: 14px 16px 16px;
		display: flex;
		flex-direction: column;
		gap: 14px;
	}

	/* The mode picker sits on a dark track, the handoff's in-card segment. */
	.controls :global(.segmented) {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		padding: 2px;
		border: none;
		border-radius: 9px;
		background: rgba(0, 0, 0, 0.35);
		-webkit-backdrop-filter: none;
		backdrop-filter: none;
	}

	.controls :global(.segmented button) {
		height: 30px;
		padding: 0 6px;
		font-size: calc(12px * var(--text-scale, 1));
	}

	.docked {
		margin: 2px -16px 0;
		padding-top: 2px;
		border-top: 1px solid var(--border-subtle);
	}

	.hint {
		margin: -6px 0 0;
		font-size: calc(13px * var(--text-scale, 1));
		line-height: 1.4;
		color: rgba(243, 243, 245, 0.55);
	}

	.slider {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.ends {
		display: flex;
		justify-content: space-between;
		font-size: calc(12px * var(--text-scale, 1));
		color: rgba(243, 243, 245, 0.55);
	}

	.mid {
		color: var(--text-subtle);
	}

	.slider input {
		width: 100%;
		accent-color: var(--accent);
	}

	.toggle {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		cursor: pointer;
	}

	.toggle-text {
		display: flex;
		flex-direction: column;
		font-size: calc(14px * var(--text-scale, 1));
		font-weight: 500;
	}

	.sub {
		font-size: calc(12px * var(--text-scale, 1));
		font-weight: 400;
		color: rgba(243, 243, 245, 0.5);
	}

	/* A 36×22 switch with a 16px knob (the handoff's toggle). */
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

	.avoid summary {
		font-size: calc(13px * var(--text-scale, 1));
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
		font-size: calc(13px * var(--text-scale, 1));
		padding: 2px 0;
	}

	.muted {
		color: var(--text-muted);
	}
</style>
