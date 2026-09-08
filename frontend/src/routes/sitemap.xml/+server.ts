// Dynamic for the same reason as robots.txt/+server.ts -- URLs need an
// absolute origin, and this also has to reflect whatever's actually
// published right now rather than a snapshot baked in at build time.
//
// Uses the request-scoped `fetch` SvelteKit provides to this handler
// (not $lib/api.ts's helper, which relies on the browser's global
// fetch) -- that's what correctly resolves a relative /api/... path
// during server-side execution.
//
// KNOWN LIMIT: the public list endpoints cap at 100 rows per call (see
// backend/app/routers/photos.py's list_photos), so if the published
// catalog ever exceeds 100 photos or 100 videos, this sitemap won't
// include the overflow. Fine for the current catalog size; would need
// real pagination here (and probably a sitemap index file) if the
// gallery grows well past that.

import type { RequestHandler } from './$types';

interface MinimalItem {
	id: string;
}

async function fetchPublished(fetch: typeof globalThis.fetch, path: string): Promise<MinimalItem[]> {
	try {
		const res = await fetch(path);
		return res.ok ? await res.json() : [];
	} catch {
		// Backend unreachable, timed out, etc. -- degrade to an empty
		// list rather than let this reject and turn the whole sitemap
		// into a 500. A sitemap with just the homepage is still valid
		// and far better than no sitemap at all.
		return [];
	}
}

export const GET: RequestHandler = async ({ url, fetch }) => {
	const [photos, videos] = await Promise.all([
		fetchPublished(fetch, '/api/photos?status=published&limit=100'),
		fetchPublished(fetch, '/api/videos?status=published&limit=100')
	]);

	const entries = [
		{ loc: `${url.origin}/`, changefreq: 'daily', priority: '1.0' },
		...photos.map((p) => ({ loc: `${url.origin}/image/${p.id}`, changefreq: 'weekly', priority: '0.8' })),
		...videos.map((v) => ({ loc: `${url.origin}/video/${v.id}`, changefreq: 'weekly', priority: '0.8' }))
	];

	const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries
	.map((e) => `  <url>\n    <loc>${e.loc}</loc>\n    <changefreq>${e.changefreq}</changefreq>\n    <priority>${e.priority}</priority>\n  </url>`)
	.join('\n')}
</urlset>
`;

	return new Response(body, {
		headers: { 'Content-Type': 'application/xml; charset=utf-8' }
	});
};
