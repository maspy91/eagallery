<script lang="ts">
	// frontend/src/lib/components/TurnstileWidget.svelte
	// NEW FILE — place at: src/lib/components/TurnstileWidget.svelte
	//
	// Renders nothing at all when PUBLIC_TURNSTILE_SITE_KEY isn't set --
	// this is deliberate. The backend's verify_turnstile_token() already
	// no-ops (always returns true) when TURNSTILE_ENABLED=False, so as
	// long as this widget also no-ops when unconfigured, every existing
	// register/login flow keeps working exactly as it does today whether
	// or not you've set up Cloudflare yet. Nothing breaks by dropping
	// this file in; it only starts doing anything once you set the site
	// key AND flip TURNSTILE_ENABLED=True on the backend.
	//
	// Uses Turnstile's "explicit" render mode (render=explicit in the
	// script URL) so this component controls exactly when/where the
	// widget mounts, rather than Turnstile auto-scanning the DOM for
	// `cf-turnstile` classes -- avoids double-render issues across
	// client-side navigation between these auth pages.

	import { onMount, onDestroy, createEventDispatcher } from 'svelte';
	import { PUBLIC_TURNSTILE_SITE_KEY } from '$env/static/public';

	const dispatch = createEventDispatcher<{ verified: string; expired: void; error: void }>();

	export const enabled = Boolean(PUBLIC_TURNSTILE_SITE_KEY);

	let container: HTMLDivElement;
	let widgetId: string | null = null;

	interface TurnstileGlobal {
		render: (container: HTMLElement, options: Record<string, unknown>) => string;
		remove: (id: string) => void;
		reset: (id: string) => void;
	}
	declare global {
		interface Window {
			turnstile?: TurnstileGlobal;
			__onTurnstileLoad?: () => void;
		}
	}

	function loadScript(): Promise<void> {
		return new Promise((resolve) => {
			if (window.turnstile) {
				resolve();
				return;
			}
			const existing = document.querySelector('script[data-turnstile-loader]');
			if (existing) {
				const previous = window.__onTurnstileLoad;
				window.__onTurnstileLoad = () => {
					previous?.();
					resolve();
				};
				return;
			}
			const script = document.createElement('script');
			script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=__onTurnstileLoad&render=explicit';
			script.async = true;
			script.defer = true;
			script.dataset.turnstileLoader = 'true';
			window.__onTurnstileLoad = () => resolve();
			document.head.appendChild(script);
		});
	}

	onMount(async () => {
		if (!enabled) return;
		await loadScript();
		if (!window.turnstile || !container) return;

		widgetId = window.turnstile.render(container, {
			sitekey: PUBLIC_TURNSTILE_SITE_KEY,
			callback: (token: string) => dispatch('verified', token),
			'expired-callback': () => dispatch('expired'),
			'error-callback': () => dispatch('error')
		});
	});

	onDestroy(() => {
		if (widgetId && window.turnstile) {
			try {
				window.turnstile.remove(widgetId);
			} catch {
				// widget already gone (e.g. navigated away mid-challenge) -- nothing to clean up
			}
		}
	});

	/** Exposed so a form can clear a used/expired token and make the
	 * person complete the challenge again (e.g. after a failed login). */
	export function reset() {
		if (widgetId && window.turnstile) window.turnstile.reset(widgetId);
	}
</script>

{#if enabled}
	<div bind:this={container} />
{/if}
