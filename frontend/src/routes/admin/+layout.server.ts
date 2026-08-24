// Same reasoning as dashboard/+layout.server.ts -- see that file for the
// full explanation of why this only works now that /api/* is same-origin.

import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ fetch, cookies }) => {
	if (!cookies.get('admin_session')) {
		throw redirect(303, '/auth');
	}

	const res = await fetch('/api/auth/me');
	if (!res.ok) {
		throw redirect(303, '/auth');
	}

	const user = await res.json();
	if (user.role === 'customer') {
		throw redirect(303, '/auth');
	}

	return { user };
};
