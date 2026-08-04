<script>
	// Reusable radar chart. Pass `axes` as [{ label, value }].
	// `max` defaults to the largest value (so the top axis reaches the edge).
	export let axes = [];
	export let max = null;
	export let showValue = true;
	export let ariaLabel = 'Radar chart';

	const cx = 170;
	const cy = 145;
	const maxR = 84;
	const labelR = maxR + 14;
	// viewBox cropped to the chart + labels with ~18px of breathing room.
	// overflow:visible covers any label that nudges past the edge.
	const VBX = 6;
	const VBY = 18;
	const VBW = 340;
	const VBH = 258;
	const levels = [0.25, 0.5, 0.75, 1];

	$: N = axes.length;
	$: vals = axes.map((a) => Math.max(0, a.value ?? 0));
	$: effectiveMax = max ?? ((vals.length ? Math.max(...vals) : 1) || 1);

	function point(i, r, n = N) {
		const angle = (Math.PI * 2 / n) * i - Math.PI / 2;
		return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
	}

	function ringPoints(r) {
		return axes.map((_, i) => point(i, r).join(',')).join(' ');
	}

	function label(i) {
		const angle = (Math.PI * 2 / N) * i - Math.PI / 2;
		const cos = Math.cos(angle);
		const sin = Math.sin(angle);
		const [x, y] = point(i, labelR);
		const anchor = Math.abs(cos) < 0.35 ? 'middle' : cos > 0 ? 'start' : 'end';
		const dy = sin < -0.35 ? -2 : sin > 0.35 ? 10 : 4;
		return { x, y: y + dy, anchor };
	}

	$: dataVertices = axes.map((a, i) => point(i, maxR * Math.min(1, (a.value ?? 0) / effectiveMax)));
	$: dataPolygon = dataVertices.map((p) => p.join(',')).join(' ');
</script>

{#if N >= 3}
	<svg class="radar" viewBox="{VBX} {VBY} {VBW} {VBH}" role="img" aria-label={ariaLabel}>
		<defs>
			<linearGradient id="radar-grad" x1="0" y1="0" x2="1" y2="1">
				<stop offset="0%" stop-color="#5ec9ff" />
				<stop offset="100%" stop-color="#a235ff" />
			</linearGradient>
		</defs>

		<g class="grid-group">
			{#each levels as lvl}
				<polygon class="grid" points={ringPoints(maxR * lvl)} />
			{/each}
			{#each axes as _, i}
				{@const [x, y] = point(i, maxR)}
				<line class="axis" x1={cx} y1={cy} x2={x} y2={y} />
			{/each}
		</g>

		<polygon class="data" points={dataPolygon} fill="url(#radar-grad)" />

		{#each dataVertices as [x, y]}
			<circle class="vertex" cx={x} cy={y} r="3" />
		{/each}

		{#each axes as axis, i}
			{@const pos = label(i)}
			<text class="label" x={pos.x} y={pos.y} text-anchor={pos.anchor}>
				<tspan class="label-name">{axis.label}</tspan>
				{#if showValue}
					<tspan class="label-value" x={pos.x} dy="1.15em">{Math.round(axis.value ?? 0)}</tspan>
				{/if}
			</text>
		{/each}
	</svg>
{/if}

<style>
	.radar {
		display: block;
		width: 100%;
		height: auto;
		overflow: visible;
	}

	.grid {
		fill: none;
		stroke: rgba(255, 255, 255, 0.07);
		stroke-width: 1;
	}

	.axis {
		stroke: rgba(255, 255, 255, 0.07);
		stroke-width: 1;
	}

	.data {
		fill-opacity: 0.35;
		stroke: var(--accent);
		stroke-width: 2;
		stroke-linejoin: round;
	}

	.vertex {
		fill: #fff;
	}

	.label-name {
		fill: var(--text-muted);
		font-size: 10px;
		font-weight: 600;
	}

	.label-value {
		fill: var(--accent);
		font-size: 11px;
		font-weight: 700;
	}
</style>
