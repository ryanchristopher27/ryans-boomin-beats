// Playlist Builder helpers (R4).

/** A name from the first prompt: the backend doesn't name playlists. */
export function playlistName(prompt) {
	const p = (prompt ?? '').trim().replace(/\s+/g, ' ').replace(/[.!?]+$/, '');
	if (!p) return 'New playlist';
	const short = p.length > 48 ? `${p.slice(0, 45).replace(/\s+\S*$/, '')}…` : p;
	return short[0].toUpperCase() + short.slice(1);
}

/** The assistant's reply as a sentence: its content is the songs as JSON. */
export function replyText(content, first) {
	let n = 0;
	try {
		const songs = JSON.parse(content);
		n = Array.isArray(songs) ? songs.length : 0;
	} catch {
		return content;
	}
	if (!n) return "I couldn't find songs for that. Try describing it another way.";
	return first ? `Picked ${n} songs and checked each one.` : `Updated the playlist: ${n} songs.`;
}

/** "10 songs · 38 min" (minutes only when durations are known). */
export function playlistMeta(tracks) {
	const ms = tracks.reduce((sum, t) => sum + (t.spotify?.duration_ms ?? 0), 0);
	const songs = `${tracks.length} song${tracks.length === 1 ? '' : 's'}`;
	return ms ? `${songs} · ${Math.max(1, Math.round(ms / 60000))} min` : songs;
}
