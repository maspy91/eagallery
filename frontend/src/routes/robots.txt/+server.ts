// A dynamic route (not a static file under /static) specifically so the
// Sitemap: directive below can use an absolute URL built from the
// request's own origin -- correct whether this is running on the real
// production domain, a Vercel preview URL, or localhost, with nothing
// to keep in sync by hand.

import type { RequestHandler } from './$types';

export const GET: RequestHandler = ({ url }) => {
	const body = `User-agent: *
Allow: /
Disallow: /admin
Disallow: /dashboard
Disallow: /login
Disallow: /register
Disallow: /auth
Disallow: /forgot-password
Disallow: /reset-password
Disallow: /verify-email
Disallow: /staff/accept-invite

Sitemap: ${url.origin}/sitemap.xml
`;

	return new Response(body, {
		headers: { 'Content-Type': 'text/plain; charset=utf-8' }
	});
};
