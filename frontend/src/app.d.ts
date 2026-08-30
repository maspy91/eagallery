// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}

	// Cloudflare Turnstile's global, loaded ad-hoc by TurnstileWidget.svelte
	// via a <script> tag (see its loadScript()) rather than an npm package,
	// so there's no @types package to pull this in from.
	//
	// This lives here rather than inside TurnstileWidget.svelte itself:
	// a `declare global` written inside a .svelte file's <script> block
	// gets wrapped in a function scope by svelte2tsx's .svelte -> .tsx
	// transform for type-checking, so it silently fails to augment the
	// real global Window type -- even other code in that same file then
	// fails to see it. Ambient global augmentation has to live in a
	// plain .d.ts file to actually take effect.
	interface TurnstileGlobal {
		render: (container: HTMLElement, options: Record<string, unknown>) => string;
		remove: (id: string) => void;
		reset: (id: string) => void;
	}
	interface Window {
		turnstile?: TurnstileGlobal;
		__onTurnstileLoad?: () => void;
	}
}

export {};
