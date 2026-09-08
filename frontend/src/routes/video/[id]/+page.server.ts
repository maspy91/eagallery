// Mirrors image/[id]/+page.server.ts exactly -- see its comments for
// the full reasoning (crawlers don't run JS, so this has to happen
// server-side; calls the view-count-free /meta endpoint on purpose;
// never throws on a miss).

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	try {
		const res = await fetch(`/api/videos/${params.id}/meta`);
		if (!res.ok) return { meta: null };
		return { meta: await res.json() };
	} catch {
		return { meta: null };
	}
};
