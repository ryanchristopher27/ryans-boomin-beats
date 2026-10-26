<script>
	import { onDestroy, onMount } from 'svelte';
	import { elapsedMinutes } from '$lib/dj/logic.js';

	/** @type {any} */
	export let dj;
	const { doc } = dj;

	const CHOICES = [
		{ id: 'none', label: 'None' },
		{ id: 'destination', label: 'Destination' },
		{ id: 'build', label: 'Build to peak' },
		{ id: 'wind_down', label: 'Wind down' },
		{ id: 'peak_cool', label: 'Peak then cool' },
		{ id: 'drift', label: 'Drift' }
	];
	const LENGTHS = [15, 30, 60];

	let now = Date.now();
	let timer;
	onMount(() => (timer = setInterval(() => (now = Date.now()), 30000)));
	onDestroy(() => clearInterval(timer));

	$: goal = $doc.options.goal;
	$: choice = !goal ? 'none' : goal.kind === 'arc' ? goal.shape : goal.kind;
	$: elapsed = goal?.kind === 'arc' ? Math.min(Math.floor(elapsedMinutes(goal, now)), goal.minutes) : 0;

	let destination = '';
	let editing = false;
	$: if (!editing) destination = goal?.destination ?? '';

	function choose(id) {
		if (id === 'none') return dj.setGoal(null);
		if (id === 'destination') {
			editing = true;
			return;
		}
		if (id === 'drift') return dj.setGoal({ kind: 'drift' });
		dj.setGoal({ kind: 'arc', shape: id, minutes: goal?.minutes ?? 30 });
	}

	function setDestination() {
		const text = destination.trim();
		if (text) dj.setGoal({ kind: 'destination', destination: text });
		editing = false;
	}
</script>

<div class="goal">
	<label class="row">
		<span class="label">Steer toward</span>
		<select value={editing ? 'destination' : choice} on:change={(e) => choose(e.currentTarget.value)}>
			{#each CHOICES as c}<option value={c.id}>{c.label}</option>{/each}
		</select>
	</label>

	{#if editing || choice === 'destination'}
		<form class="dest" on:submit|preventDefault={setDestination}>
			<input
				bind:value={destination}
				on:focus={() => (editing = true)}
				on:keydown={(e) => e.key === 'Escape' && (editing = false)}
				placeholder="e.g. 90s R&B or Daft Punk…"
				aria-label="Destination"
				name="destination"
				autocomplete="off"
				maxlength="200"
			/>
			{#if editing}<button class="btn" type="submit">Set</button>{/if}
		</form>
	{:else if goal?.kind === 'arc'}
		<div class="segmented small" role="radiogroup" aria-label="Arc length">
			{#each LENGTHS as m}
				<button role="radio" aria-checked={goal.minutes === m} class:active={goal.minutes === m} on:click={() => dj.setGoal({ ...goal, minutes: m })}>{m} min</button>
			{/each}
		</div>
		<div class="arc" aria-label="{elapsed} of {goal.minutes} minutes">
			<div class="track"><div class="fill" style:transform="scaleX({elapsed / goal.minutes})" /></div>
			<span>{elapsed} of {goal.minutes} min</span>
		</div>
	{:else if goal?.kind === 'drift'}
		<p class="hint">The DJ wanders somewhere new, one step at a time.</p>
	{:else}
		<p class="hint">Optional. The DJ steers one step at a time.</p>
	{/if}
</div>

<style>
	.goal {
		padding: 12px 16px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		font-size: 14px;
	}

	select,
	input {
		background: var(--surface-2);
		color: var(--text-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		font: inherit;
		font-size: 14px;
		padding: 6px 10px;
	}

	select {
		color: var(--accent-2-text);
	}

	.dest {
		display: flex;
		gap: 8px;
	}

	.dest input {
		flex: 1;
		min-width: 0;
	}

	input::placeholder {
		color: var(--text-muted);
	}

	.arc {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 12px;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
	}

	.arc .track {
		flex: 1;
		height: 4px;
		border-radius: 2px;
		background: rgba(255, 255, 255, 0.14);
		overflow: hidden;
	}

	.arc .fill {
		height: 100%;
		background: var(--accent-2);
		transform-origin: left;
	}

	.hint {
		margin: 0;
		font-size: 13px;
		line-height: 1.45;
		color: var(--text-muted);
	}
</style>
