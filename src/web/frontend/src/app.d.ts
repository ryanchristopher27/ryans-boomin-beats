// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface Platform {}
	}

	// The Popover API is newer than Svelte 4's element typings (DJ page menus).
	namespace svelteHTML {
		interface HTMLAttributes<T> {
			popover?: 'auto' | 'manual';
			popovertarget?: string;
			'on:toggle'?: (event: Event & { newState?: string }) => any;
		}
	}
}

export {};
