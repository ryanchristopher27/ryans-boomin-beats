<script>
	// The app's one outline icon set (Tabler-style, 24px grid, 1.75 stroke).
	export let name;
	export let size = 18;
	export let label = '';

	const paths = {
		play: 'M7 4v16l13-8z',
		pause: 'M6 5h4v14H6zM14 5h4v14h-4z',
		prev: 'M20 5v14l-12-7zM4 5v14',
		next: 'M4 5v14l12-7zM20 5v14',
		up: 'M7 10v10H4V10zM7 11l4-8a2 2 0 0 1 3 2l-1 4h5a2 2 0 0 1 2 2l-1.5 7a2 2 0 0 1-2 2H7',
		down: 'M7 14V4H4v10zM7 13l4 8a2 2 0 0 0 3-2l-1-4h5a2 2 0 0 0 2-2l-1.5-7a2 2 0 0 0-2-2H7',
		plus: 'M12 5v14M5 12h14',
		check: 'M5 12l5 5L20 7',
		refresh: 'M20 11A8 8 0 0 0 5.6 6.4L4 8M4 4v4h4M4 13a8 8 0 0 0 14.4 4.6L20 16M20 20v-4h-4',
		dots: 'M5 12h.01M12 12h.01M19 12h.01',
		grip: 'M9 5h.01M9 12h.01M9 19h.01M15 5h.01M15 12h.01M15 19h.01',
		x: 'M18 6L6 18M6 6l12 12',
		hold: 'M5 10h14M5 14h14',
		lift: 'M12 19V5M6 11l6-6 6 6',
		drop: 'M12 5v14M6 13l6 6 6-6',
		pivot: 'M5 19v-6a4 4 0 0 1 4-4h10M15 5l4 4-4 4',
		curveball: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z',
		toward: 'M12 3l7 18-7-4-7 4z',
		drift: 'M4 8h10a3 3 0 1 0-3-3M4 12h15a3 3 0 1 1-3 3M4 16h7',
		later: 'M12 7v5l3 3M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
		speaker: 'M7 3h10a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM12 14m-3 0a3 3 0 1 0 6 0 3 3 0 1 0-6 0M12 7h.01',
		search: 'M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM21 21l-6-6',
		layout: 'M4 4h6v16H4zM14 4h6v6h-6zM14 14h6v6h-6z',
		broadcast: 'M12 12h.01M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8',
		alert: 'M12 9v4M12 17h.01M10.3 3.9L2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
		sparkle: 'M12 4l1.5 5.5L19 11l-5.5 1.5L12 18l-1.5-5.5L5 11l5.5-1.5z',
		compass: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM15.5 8.5l-2 5-5 2 2-5z',
		wand: 'M4 20L14 10M15 4v2M15 10v2M12 7h-2M20 7h-2M17.5 4.5l-1 1M17.5 9.5l-1-1',
		disc: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
		user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM5 20a7 7 0 0 1 14 0',
		gear: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z',
		playlist: 'M4 6h16M4 12h10M4 18h7M17 14v6M14 17h6',
		back: 'M15 6l-6 6 6 6',
		forward: 'M9 6l6 6-6 6',
		arrow: 'M5 12h14M13 6l6 6-6 6',
		heart: 'M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z',
		expand: 'M14 4h6v6M10 20H4v-6M20 4l-6 6M4 20l6-6',
		collapse: 'M4 14h6v6M20 10h-6V4M14 10l6-6M10 14l-6 6',
		music: 'M9 18V5l11-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM20 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
		send: 'M5 12h14M13 6l6 6-6 6',
		logout: 'M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 16l4-4-4-4M14 12H4'
	};
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="1.75"
	stroke-linecap="round"
	stroke-linejoin="round"
	role={label ? 'img' : undefined}
	aria-label={label || undefined}
	aria-hidden={label ? undefined : 'true'}
	class="icon"
>
	<path d={paths[name] ?? ''} />
</svg>

<style>
	.icon {
		flex: none;
		display: block;
	}
</style>
