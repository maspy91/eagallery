// The actual server-side guard the proxy migration exists to enable.
// Runs on every request to anything under /dashboard -- full page loads
// AND client-side navigations (SvelteKit re-invokes server load
// functions on client-side route changes too) -- so a protected page's
// content is never sent to an unauthenticated request in the first
// place.
//
// `fetch` here is SvelteKit's provided fetch: for a relative URL like
// this, during SSR it forwards the incoming request's cookies
// automatically. That only works because /api/* is same-origin now (see
// vercel.json / vite.config.ts) -- the session cookie is set under this
// app's own domain, so this server can actually see it.

import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ fetch, cookies }) => {
	if (!cookies.get('customer_session')) {
		throw redirect(303, '/login');
	}

	const res = await fetch('/api/customer/me');
	if (!res.ok) {
		throw redirect(303, '/login');
	}

	const user = await res.json();
	if (user.role !== 'customer') {
		throw redirect(303, '/admin');
	}

	return { user };
};
