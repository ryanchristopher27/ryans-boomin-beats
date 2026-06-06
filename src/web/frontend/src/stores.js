import { writable } from "svelte/store";

export const alert = writable("Welcome to the to-do list app!");

export const page = writable('Home');

export const user = writable({});

export const access_token = writable('');

export const logged_in = writable(false);

const storedLlmConfig = typeof localStorage !== 'undefined'
    ? JSON.parse(localStorage.getItem('llmConfig') || 'null')
    : null;

export const llmConfig = writable(storedLlmConfig || { provider: 'claude', apiKey: '', connected: false });

export const chatMessages = writable([]);

export const generatedPlaylist = writable([]);