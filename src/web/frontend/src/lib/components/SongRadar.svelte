<script>
	export let scores = null;

	const order = ['Energy', 'Danceability', 'Positivity', 'Acousticness', 'Intensity', 'Tempo'];

	const cx = 170;
	const cy = 145;
	const maxR = 84;
	const labelR = maxR + 14;
	// viewBox cropped to the chart + labels with a balanced ~18px of breathing
	// room. overflow:visible covers any label that nudges past the edge.
	const VBX = 6;
	const VBY = 18;
	const VBW = 340;
	const VBH = 258;
	const levels = [0.25, 0.5, 0.75, 1];

	const N = order.length;

	function point(i, r) {
		const angle = (Math.PI * 2 / N) * i - Math.PI / 2;
		return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
	}

	function ringPoints(r) {
		return order.map((_, i) => point(i, r).join(',')).join(' ');
	}

	function label(i) {
		const angle = (Math.PI * 2 / N) * i - Math.PI / 2;
		const cos = Math.cos(angle);
		const sin = Math.sin(angle);
		const [x, y] = point(i, labelR);
		const anchor = Math.abs(cos) < 0.35 ? 'middle' : cos > 0 ? 'start' : 'end';
		// Nudge top/bottom labels vertically so they clear the chart.
		const dy = sin < -0.35 ? -2 : sin > 0.35 ? 10 : 4;
		return { x, y: y + dy, anchor };
	}

	$: clamped = scores
		? order.map((k) => Math.max(0, Math.min(100, Math.round(scores[k] ?? 0))))
		: [];
	$: dataPolygon = clamped.map((v, i) => point(i, maxR * (v / 100)).join(',')).join(' ');
	$: dataVertices = clamped.map((v, i) => point(i, maxR * (v / 100)));
</script>

{#if scores}
	<svg
		class="radar"
		viewBox="{VBX} {VBY} {VBW} {VBH}"
		role="img"
		aria-label="Song characteristics radar chart"
	>
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
			{#each order as _, i}
				{@const [x, y] = point(i, maxR)}
				<line class="axis" x1={cx} y1={cy} x2={x} y2={y} />
			{/each}
		</g>

		<polygon class="data" points={dataPolygon} fill="url(#radar-grad)" />

		{#each dataVertices as [x, y]}
			<circle class="vertex" cx={x} cy={y} r="3" />
		{/each}

		{#each order as name, i}
			{@const pos = label(i)}
			<text class="label" x={pos.x} y={pos.y} text-anchor={pos.anchor}>
				<tspan class="label-name">{name}</tspan>
				<tspan class="label-value" x={pos.x} dy="1.15em">{clamped[i]}</tspan>
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
