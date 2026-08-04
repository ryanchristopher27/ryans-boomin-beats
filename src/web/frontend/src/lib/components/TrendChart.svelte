<script>
	// Compact multi-line chart over a few x-axis points (e.g. timeframes).
	export let labels = []; // x-axis labels
	export let series = []; // [{ name, values: number[] }]
	export let min = 0;
	export let max = 100;
	export let unit = '';

	const PALETTE = ['#5ec9ff', '#a235ff', '#7b7ff0', '#6bffb8', '#ffb86b', '#ff6b9d'];

	const W = 380;
	const H = 210;
	const padL = 12;
	const padR = 12;
	const padT = 14;
	const padB = 34;

	$: n = labels.length;
	$: plotW = W - padL - padR;
	$: plotH = H - padT - padB;
	$: span = max - min || 1;

	function x(i) {
		return n <= 1 ? padL + plotW / 2 : padL + (i / (n - 1)) * plotW;
	}
	function y(v) {
		return padT + (1 - (v - min) / span) * plotH;
	}

	$: gridYs = [0, 0.25, 0.5, 0.75, 1].map((f) => padT + f * plotH);

	function linePoints(values) {
		return values.map((v, i) => `${x(i)},${y(v)}`).join(' ');
	}
</script>

{#if n >= 2 && series.length}
	<div class="trend">
		<svg viewBox="0 0 {W} {H}" class="trend-svg" role="img" aria-label="Trend chart">
			{#each gridYs as gy}
				<line class="grid" x1={padL} y1={gy} x2={W - padR} y2={gy} />
			{/each}

			{#each series as s, si}
				{@const color = PALETTE[si % PALETTE.length]}
				<polyline class="line" points={linePoints(s.values)} stroke={color} />
				{#each s.values as v, i}
					<circle cx={x(i)} cy={y(v)} r="3.5" fill={color} />
				{/each}
			{/each}

			{#each labels as lbl, i}
				<text class="x-label" x={x(i)} y={H - 12} text-anchor="middle">{lbl}</text>
			{/each}
		</svg>

		<div class="legend">
			{#each series as s, si}
				<span class="legend-item">
					<span class="swatch" style="background:{PALETTE[si % PALETTE.length]}"></span>
					{s.name}{#if unit}<span class="legend-val"> {s.values[s.values.length - 1]}{unit}</span>{/if}
				</span>
			{/each}
		</div>
	</div>
{/if}

<style>
	.trend {
		width: 100%;
		max-width: 300px;
		margin: 0 auto;
	}

	.trend-svg {
		display: block;
		width: 100%;
		height: auto;
	}

	.grid {
		stroke: rgba(255, 255, 255, 0.06);
		stroke-width: 1;
	}

	.line {
		fill: none;
		stroke-width: 2;
		stroke-linejoin: round;
		stroke-linecap: round;
	}

	.x-label {
		fill: var(--text-subtle);
		font-size: 11px;
		font-weight: 600;
	}

	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 8px 14px;
		justify-content: center;
		margin-top: 10px;
	}

	.legend-item {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 0.74rem;
		color: var(--text-muted);
	}

	.swatch {
		width: 10px;
		height: 10px;
		border-radius: 3px;
		flex-shrink: 0;
	}

	.legend-val {
		color: var(--text-subtle);
	}
</style>
