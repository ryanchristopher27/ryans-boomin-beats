import { writable } from "svelte/store";

/**
 * A writable store backed by localStorage. Hydrates from storage on load and
 * persists every change, so state survives tab switches, in-app navigation,
 * and full page reloads. SSR-safe (no-ops when localStorage is unavailable).
 */
function persisted(key, initial) {
    let start = initial;
    if (typeof localStorage !== 'undefined') {
        const stored = localStorage.getItem(key);
        if (stored !== null) {
            try {
                start = JSON.parse(stored);
            } catch {
                start = initial;
            }
        }
    }

    const store = writable(start);

    if (typeof localStorage !== 'undefined') {
        store.subscribe(value => {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch {
                /* storage full or unavailable — ignore */
            }
        });
    }

    return store;
}

export const alert = writable("Welcome to the to-do list app!");

export const page = writable('Home');

export const user = writable({});

export const access_token = writable('');

export const logged_in = writable(false);

const storedLlmConfig = typeof localStorage !== 'undefined'
    ? JSON.parse(localStorage.getItem('llmConfig') || 'null')
    : null;

export const llmConfig = writable(storedLlmConfig || { provider: 'claude', apiKey: '', connected: false });

// --- Persisted page work state (survives tab switch / nav / reload) ---

// Playlist Builder
export const chatMessages = persisted('chatMessages', []);
export const generatedPlaylist = persisted('generatedPlaylist', []);
export const playlistRequested = persisted('playlistRequested', 0);

// Explore
export const selectedSong = persisted('selectedSong', null);
export const discoveryPlaylist = persisted('discoveryPlaylist', []);
export const discoveryRequested = persisted('discoveryRequested', 0);

// Cached song profile + selections, keyed to the song so returning to the same
// song does NOT re-query Last.fm / the LLM.
export const exploreSession = persisted('exploreSession', {
    key: null,
    profile: null,
    selectedTags: [],
    selectedAspects: [],
});
