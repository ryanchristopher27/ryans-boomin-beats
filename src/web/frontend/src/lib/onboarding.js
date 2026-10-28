// First run (F1): 1 connect Spotify → 2 pick an AI → 3 where to start; 0 = done.
// Saved so the step survives Spotify's sign-in redirect.
import { writable } from 'svelte/store';

const KEY = 'bb-onboarding';

function initial() {
	try {
		const raw = localStorage.getItem(KEY);
		// Number(null) is 0, which would read "never started" as "finished".
		const v = raw === null ? NaN : Number(raw);
		return [0, 1, 2, 3].includes(v) ? v : null;
	} catch {
		return null;
	}
}

/** null = never decided (the layout starts it for people who aren't signed in). */
export const onboarding = writable(typeof localStorage !== 'undefined' ? initial() : null);
onboarding.subscribe((v) => {
	try {
		if (typeof localStorage !== 'undefined' && v != null) localStorage.setItem(KEY, String(v));
	} catch {
		/* private mode */
	}
});
