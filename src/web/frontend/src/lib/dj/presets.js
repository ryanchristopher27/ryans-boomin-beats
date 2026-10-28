// Night presets (F3a): one tap sets how bold the DJ is and where it's heading.
// Values from the handoff (Dinner 20 / Pregame 55 / Peak 80 / Afterparty 35);
// `familiar` waits for the Familiar ↔ New slider (F3d).

export const NIGHT = {
	dinner: { label: 'Dinner', bold: 0.2, familiar: 0.75, goal: { kind: 'drift' } },
	pregame: { label: 'Pregame', bold: 0.55, familiar: 0.45, goal: { kind: 'arc', shape: 'build', minutes: 60 } },
	peak: { label: 'Peak', bold: 0.8, familiar: 0.4, goal: { kind: 'arc', shape: 'peak_cool', minutes: 60 } },
	afterparty: { label: 'Afterparty', bold: 0.35, familiar: 0.3, goal: { kind: 'arc', shape: 'wind_down', minutes: 60 } }
};

const sameGoal = (a, b) => !!a && a.kind === b.kind && (a.kind !== 'arc' || (a.shape === b.shape && a.minutes === b.minutes));

/** The preset the current options match, or null once the host has tweaked them. */
export function activePreset(options) {
	for (const [id, p] of Object.entries(NIGHT)) {
		if (Math.abs((options?.adventurousness ?? -1) - p.bold) < 0.026 && sameGoal(options?.goal, p.goal)) return id;
	}
	return null;
}

/** Apply a preset through the engine's setters (each one syncs). */
export function applyPreset(dj, id) {
	const p = NIGHT[id];
	if (!p) return;
	dj.setAdventurousness(p.bold);
	dj.setGoal(p.goal);
}
