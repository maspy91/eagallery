import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export type Theme = 'light' | 'dark';

function getInitialTheme(): Theme {
	if (!browser) return 'dark';
	return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

function createThemeStore() {
	const { subscribe, set } = writable<Theme>(getInitialTheme());

	function apply(theme: Theme) {
		if (!browser) return;
		document.documentElement.classList.toggle('dark', theme === 'dark');
		localStorage.setItem('theme', theme);
		set(theme);
	}

	return {
		subscribe,
		set: apply,
		toggle() {
			apply(document.documentElement.classList.contains('dark') ? 'light' : 'dark');
		}
	};
}

export const theme = createThemeStore();
