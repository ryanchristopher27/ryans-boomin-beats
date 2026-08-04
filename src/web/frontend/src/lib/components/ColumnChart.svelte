<script>
	// Vertical bar/column chart: category labels on the x-axis, value on the y-axis.
	export let items = []; // [{ label, value }]
	export let max = null;

	const W = 360;
	const H = 230;
	const padL = 26;
	const padR = 10;
	const padT = 20;
	const padB = 26;

	$: n = items.length;
	$: plotW = W - padL - padR;
	$: plotH = H - padT - padB;
	$: dataMax = max ?? Math.max(1, ...items.map((d) => d.value || 0));
	$: baseline = padT + plotH;
	$: slot = n ? plotW / n : plotW;
	$: barW = Math.min(48, slot * 0.6);

	function barX(i) {
		return padL + i * slot + (slot - barW) / 2;
	}
	function barH(v) {
		return plotH * ((v || 0) / dataMax);
	}

	// y-axis ticks (0, mid, max)
	$: ticks = [0, Math.round(dataMax / 2), dataMax].filter((v, i, a) => a.indexOf(v) === i);
	function tickY(v) {
		return baseline - barH(v);
	}
</script>

{#if n}
	<svg viewBox="0 0 {W} {H}" class="col-chart" role="img" aria-label="Songs by era">
		<defs>
			<linearGradient id="col-grad" x1="0" y1="1" x2="0" y2="0">
				<stop offset="0%" stop-color="#5ec9ff" />
				<stop offset="100%" stop-color="#a235ff" />
			</linearGradient>
		</defs>

		<!-- gridlines + y-axis labels -->
		{#each ticks as t}
			<line class="grid" x1={padL} y1={tickY(t)} x2={W - padR} y2={tickY(t)} />
			<text class="y-label" x={padL - 6} y={tickY(t) + 3} text-anchor="end">{t}</text>
		{/each}

		<!-- bars + value + x labels -->
		{#each items as d, i}
			{@const h = barH(d.value)}
			<rect
				class="bar"
				x={barX(i)}
				y={baseline - h}
				width={barW}
				height={Math.max(0, h)}
				rx="4"
				fill="url(#col-grad)"
			/>
			{#if d.value}
				<text class="bar-value" x={barX(i) + barW / 2} y={baseline - h - 5} text-anchor="middle">{d.value}</text>
			{/if}
			<text class="x-label" x={barX(i) + barW / 2} y={baseline + 16} text-anchor="middle">{d.label}</text>
		{/each}
	</svg>
{/if}

<style>
	.col-chart {
		display: block;
		width: 100%;
		max-width: 300px;
		height: auto;
		margin: 0 auto;
	}

	.grid {
		stroke: rgba(255, 255, 255, 0.06);
		stroke-width: 1;
	}

	.y-label {
		fill: var(--text-subtle);
		font-size: 9px;
	}

	.bar {
		transition: opacity var(--transition);
	}

	.bar-value {
		fill: var(--text-muted);
		font-size: 10px;
		font-weight: 700;
	}

	.x-label {
		fill: var(--text-subtle);
		font-size: 10px;
		font-weight: 600;
	}
</style>
