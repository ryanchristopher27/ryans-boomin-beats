// Profile's summary sentence and insight cards (R5), built from the data the
// page already loads: ranked genres, decade counts and the listening clock.

export const PERIOD_LABELS = { short_term: '4 weeks', medium_term: '6 months', long_term: 'All time' };
const PERIOD_PHRASE = { short_term: 'Your last 4 weeks', medium_term: 'Your last 6 months', long_term: 'All time' };

/** "7pm" for hour 19. */
export const hourLabel = (h) => `${h % 12 || 12}${h < 12 ? 'am' : 'pm'}`;

/** The busiest hour in a 24-slot count list, or null without data. */
export function peakHour(counts) {
	if (!counts?.some((c) => c > 0)) return null;
	return counts.indexOf(Math.max(...counts));
}

const lower = (s) => s.toLowerCase();

/**
 * The one-sentence summary as parts; `strong` parts are the key phrases.
 * @param {{ period: string, genres: string[], decades: {label: string, value: number}[], peak: number | null }} d
 * @returns {{ text: string, strong?: boolean }[]}
 */
export function summaryParts({ period, genres, decades, peak }) {
	const parts = [{ text: `${PERIOD_PHRASE[period] ?? PERIOD_PHRASE.short_term}: ` }];
	const clauses = [];
	if (genres.length) clauses.push([{ text: 'mostly ' }, { text: genres.slice(0, 2).map(lower).join(' and '), strong: true }]);
	const total = decades.reduce((s, d) => s + d.value, 0);
	if (total) {
		const top = [...decades].sort((a, b) => b.value - a.value)[0];
		clauses.push([{ text: `${Math.round((100 * top.value) / total)}% from the ${top.label}` }]);
	}
	if (peak != null) clauses.push([{ text: 'and you listen most around ' }, { text: hourLabel(peak), strong: true }]);
	if (!clauses.length) return [{ text: 'Your profile fills in as you listen. ' }, { text: 'Check back in a few days', strong: true }, { text: ' to see your top tracks, genres and eras.' }];
	clauses.forEach((c, i) => {
		if (i) parts.push({ text: ', ' });
		parts.push(...c);
	});
	parts.push({ text: '.' });
	return parts;
}

/**
 * Insight cards: a label, a statement, and an action. `action.kind` is
 * 'build' (a Builder prompt) or 'dj' (open the DJ; night presets are F3).
 */
export function insights({ period, genres, decades, peak, topArtist }) {
	const out = [];
	if (genres[0]) out.push({ label: 'Top genre', value: `${genres[0][0].toUpperCase()}${genres[0].slice(1)} leads your ${lower(PERIOD_LABELS[period] ?? '4 weeks')}`, action: `Build a ${lower(genres[0])} playlist`, kind: 'build', prompt: `the best ${lower(genres[0])} for right now` });
	const eras = [...decades].sort((a, b) => b.value - a.value);
	if (eras[0]) {
		const second = eras[1];
		out.push({ label: 'Eras', value: second ? `Mostly the ${eras[0].label}, some ${second.label}` : `All from the ${eras[0].label}`, action: `Build from the ${(second ?? eras[0]).label}`, kind: 'build', prompt: `my kind of music from the ${(second ?? eras[0]).label}` });
	}
	if (peak != null) {
		const late = peak >= 21 || peak < 4;
		out.push({ label: 'Listening clock', value: `You listen most around ${hourLabel(peak)}`, action: late ? 'Start a late-night DJ set' : 'Start an evening DJ set', kind: 'dj' });
	}
	if (topArtist) out.push({ label: 'Top artist', value: `${topArtist} is your #1`, action: `Build songs like ${topArtist}`, kind: 'build', prompt: `songs like ${topArtist}` });
	return out;
}
