// Exists specifically to get Open Graph tags into the actual
// server-rendered HTML -- link-preview crawlers (Facebook/WhatsApp/
// X/etc unfurling a shared link) don't run JavaScript, so meta tags set
// client-side after the page's own onMount-driven fetch resolves would
// never be seen by them. This runs before the page renders at all, on
// both a full page load and a client-side navigation into this route.
//
// Deliberately calls the view-count-free /meta endpoint, not the real
// GET /api/photos/{id} the page component itself still uses on mount --
// see PhotoMetaOut's docstring in the backend for why those are two
// separate endpoints.
//
// Never throws on a miss: a draft/flagged/unknown id should render the
// page's own "not found" UI (handled client-side, unchanged), not a
// SvelteKit error page. `meta` is just null in that case, and the
// layout falls back to generic site tags.

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	try {
		const res = await fetch(`/api/photos/${params.id}/meta`);
		if (!res.ok) return { meta: null };
		return { meta: await res.json() };
	} catch {
		return { meta: null };
	}
};
