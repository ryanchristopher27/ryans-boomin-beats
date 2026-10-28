// General settings (F1), saved on this device. Keys follow the handoff.
import { writable } from 'svelte/store';
import { llmSettingsOpen } from '../stores.js';

const KEYS = { textScale: 'bb-zoom', compact: 'bb-compact', motion: 'bb-motion' };
export const DEFAULTS = { textScale: 0.9, compact: false, motion: true };
export const TEXT_SCALES = [0.8, 0.9, 1, 1.1, 1.2];

function saved(name) {
	let start = DEFAULTS[name];
	try {
		const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(KEYS[name]) : null;
		if (raw !== null) {
			const v = JSON.parse(raw);
			if (typeof v === typeof start && (name !== 'textScale' || TEXT_SCALES.includes(v))) start = v;
		}
	} catch {
		/* corrupt or blocked storage: the default */
	}
	const store = writable(start);
	store.subscribe((v) => {
		try {
			if (typeof localStorage !== 'undefined') localStorage.setItem(KEYS[name], JSON.stringify(v));
		} catch {
			/* private mode: lasts this visit */
		}
	});
	return store;
}

/** Text size as a multiplier of the design's sizes; 0.9 is the handoff's default. */
export const textScale = saved('textScale');
/** Smaller covers and tighter spacing in every song list. */
export const compactRows = saved('compact');
/** The visualizer, glowing covers and drifting colour while music plays. */
export const playbackMotion = saved('motion');

export function resetSettings() {
	textScale.set(DEFAULTS.textScale);
	compactRows.set(DEFAULTS.compact);
	playbackMotion.set(DEFAULTS.motion);
}

/** Which tab the gear popover shows. */
export const settingsTab = writable(/** @type {'general' | 'ai'} */ ('general'));

/**
 * Open Settings on a tab: 'ai' from "Add an AI key" prompts, 'general' from the gear.
 * @param {'general' | 'ai'} [tab]
 */
export function openSettings(tab = 'general') {
	settingsTab.set(tab);
	llmSettingsOpen.set(true);
}
