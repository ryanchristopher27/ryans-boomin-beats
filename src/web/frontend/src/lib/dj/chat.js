// DJ chat: the host asks in their own words; /dj/chat/ answers with a reply,
// checked songs, and actions applied here (layout, controls, goal, steering the
// board). The log is kept on this device, so it survives a layout change (the
// grid remounts its widgets) and a reload.
import { get, writable } from 'svelte/store';
import { WIDGETS, layoutFromChat } from './layout.js';

const KEY = 'dj_chat';
const KEEP = 30;
const PRESET_LABEL = { host: 'Host', board: 'Board', compass: 'Compass', focus: 'Focus' };
const MODE_LABEL = { whisper: 'Whisper', copilot: 'Co-pilot', autofill: 'Autofill', driver: 'Driver' };

/**
 * @typedef {{role: 'user', text: string} | {role: 'assistant', text: string, picks?: any[], applied?: string[], error?: boolean}} ChatEntry
 */

function restore() {
	try {
		const v = JSON.parse(localStorage.getItem(KEY) ?? '[]');
		return Array.isArray(v) ? v : [];
	} catch {
		return [];
	}
}

/** @type {import('svelte/store').Writable<ChatEntry[]>} */
export const chatLog = writable(typeof localStorage === 'undefined' ? [] : restore());
chatLog.subscribe((log) => {
	try {
		if (typeof localStorage !== 'undefined') localStorage.setItem(KEY, JSON.stringify(log.slice(-KEEP)));
	} catch {
		/* private mode: lasts this visit */
	}
});
export const chatBusy = writable(false);

export function clearChat() {
	chatLog.set([]);
}

/**
 * Apply what the DJ chat asked for and say what changed, one line each.
 * @param {any[]} actions validated by the backend (routers/dj_chat.py)
 * @param {{dj: any, page: {choose: (p: string) => void, apply: (items: any[]) => void} | null}} ctx
 * @returns {string[]}
 */
export function applyActions(actions, { dj, page }) {
	const done = [];
	for (const a of actions ?? []) {
		if (a.type === 'preset' && PRESET_LABEL[a.name] && page) {
			page.choose(a.name);
			done.push(`Layout: ${PRESET_LABEL[a.name]}`);
		} else if (a.type === 'layout' && page) {
			const items = layoutFromChat(a.items);
			if (items) {
				page.apply(items);
				done.push('Layout rearranged');
			}
		} else if (a.type === 'controls') {
			if (MODE_LABEL[a.mode]) {
				dj.setMode(a.mode);
				done.push(`Mode: ${MODE_LABEL[a.mode]}`);
			}
			if (typeof a.adventurousness === 'number') {
				dj.setAdventurousness(a.adventurousness);
				done.push(`Safe ↔ Bold: ${Math.round(a.adventurousness * 100)}%`);
			}
			if (typeof a.familiar === 'number') {
				dj.setFamiliar(a.familiar);
				done.push(`Familiar ↔ New: ${Math.round(a.familiar * 100)}%`);
			}
		} else if (a.type === 'goal') {
			dj.setGoal(a.goal);
			done.push(a.goal ? `Goal: ${a.goal.kind === 'destination' ? a.goal.destination : a.goal.kind === 'arc' ? a.goal.shape?.replace('_', ' ') ?? 'arc' : 'drift'}` : 'Goal cleared');
		} else if (a.type === 'refresh_moves' && a.note) {
			dj.steerMoves(a.note);
			done.push(`New moves: ${a.note}`);
		}
	}
	return done;
}

/** What /dj/chat/ needs to know: the night so far, the controls and the layout. */
export function chatBody(message, { dj, page }) {
	const doc = get(dj.doc);
	const o = doc.options;
	const ref = (t) => ({ id: t.trackID ?? t.id ?? '', isrc: t.isrc ?? null, title: t.title, artist: t.artists?.[0] ?? t.artist ?? '' });
	const now = get(dj.player).state?.track;
	const history = get(chatLog)
		.slice(-10)
		.map((e) => ({ role: e.role, content: e.text.slice(0, 2000) }));
	return {
		message,
		history,
		now_playing: now ? ref(now) : null,
		recent: doc.recent.slice(0, 15).map(ref),
		upcoming: [...doc.queue.sent, ...doc.queue.upcoming].slice(0, 30).map(ref),
		mode: o.mode,
		adventurousness: o.adventurousness,
		familiar: o.familiar ?? 0.5,
		clean: o.clean,
		goal: o.goal ? { kind: o.goal.kind, destination: o.goal.destination ?? '', shape: o.goal.shape ?? 'build', minutes: o.goal.minutes ?? 30 } : null,
		preset: page?.preset() ?? 'host',
		layout: (page?.items() ?? []).map(({ type, kind, x, y, w, h }) => ({ type, ...(kind ? { kind } : {}), x, y, w, h })),
		widgets: Object.entries(WIDGETS).map(([type, d]) => ({ type, title: d.title, minW: d.minW, minH: d.minH }))
	};
}

/** Send one message; the reply (or the error) joins the log. */
export async function sendChat(message, ctx) {
	const text = message.trim();
	if (!text || get(chatBusy)) return;
	const body = chatBody(text, ctx);
	chatLog.update((log) => [...log, { role: 'user', text }]);
	chatBusy.set(true);
	try {
		const r = await ctx.dj.request('POST', 'dj/chat/', { json: body });
		if (r.status !== 200) {
			const error = r.status === 401 ? 'Connect an AI in Settings → AI to chat with the DJ.' : r.data?.error ?? r.data?.detail ?? "Couldn't get an answer. Try again.";
			chatLog.update((log) => [...log, { role: 'assistant', text: error, error: true }]);
			return;
		}
		const applied = applyActions(r.data.actions, ctx);
		chatLog.update((log) => [...log, { role: 'assistant', text: r.data.reply, picks: r.data.picks ?? [], applied }]);
	} catch {
		chatLog.update((log) => [...log, { role: 'assistant', text: "Couldn't reach the server.", error: true }]);
	} finally {
		chatBusy.set(false);
	}
}
