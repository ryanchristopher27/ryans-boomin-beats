// Explore's recipe logic (R3), shared by the page and SongProfile.

/** The AI's "Label: value" analysis lines as fields. */
export function parseAnalysis(raw) {
	if (!raw) return [];
	return raw
		.split('\n')
		.map((line) => line.trim())
		.filter((line) => line.includes(':'))
		.map((line) => {
			const i = line.indexOf(':');
			return { label: line.slice(0, i).trim(), value: line.slice(i + 1).trim() };
		})
		.filter((f) => f.label && f.value);
}

/** The discovery prompt for "Find 12 similar songs". */
export function discoverPrompt(song, tags, aspects) {
	const artist = song.artists?.[0] ?? song.artist ?? '';
	const aspectLines = aspects.map((a) => `- ${a.label}: ${a.value}`).join('\n');
	const tagLine = tags.length ? `Shared tags/descriptors: ${tags.join(', ')}` : '';
	const qualities = [aspectLines, tagLine].filter(Boolean).join('\n');
	return `Using "${song.title}" by ${artist} as a reference point, find 12 songs that share these specific qualities:\n${qualities}\nFocus on these aspects when choosing songs. Do not include the reference song itself.`;
}

/** The Builder hand-off for "Build a playlist from this recipe". */
export function builderPrompt(song, picks) {
	const artist = song.artists?.[0] ?? song.artist ?? '';
	return `Songs like ${song.title}${artist ? ` by ${artist}` : ''}: ${picks.join(', ')}`;
}

/**
 * The Path after opening `song` from the current one: everything up to the
 * current song, then the new one (going back and branching drops the rest).
 */
export function extendTrail(trail, currentId, song) {
	const at = trail.findIndex((t) => t.id === currentId);
	const kept = at >= 0 ? trail.slice(0, at + 1) : trail;
	return [...kept.filter((t) => t.id !== song.id), song];
}
