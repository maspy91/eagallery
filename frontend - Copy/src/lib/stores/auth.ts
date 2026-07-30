import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import type { AppUser } from '$lib/types';
import { customerApi, adminApi, ApiError } from '$lib/api';

/**
 * PHASE 2: session state is the httpOnly cookie the backend sets on
 * login/verify-email/accept-invite -- this store is just a client-side
 * mirror of it, hydrated by asking the backend "who am I?" on load. It is
 * NOT the access-control boundary; a stolen/forged value here can't grant
 * access to anything, because every protected backend route re-derives
 * the user from its own cookie on every request.
 *
 * SEPARATE LOGIN SYSTEMS: customer sessions (customer_session cookie,
 * /api/customer/*) and admin/staff sessions (admin_session cookie,
 * /api/auth/*) are entirely independent on the backend. It's possible in
 * principle to be logged into both at once in the same browser; this
 * store only ever holds one active identity at a time client-side, set by
 * whichever login flow last succeeded.
 */

export const currentUser = writable<AppUser | null>(null);
export const isAuthenticated = derived(currentUser, ($u) => $u !== null);

// Tracks whether the initial session restore (see restoreSession) has
// finished, so route guards can show a loading state instead of
// momentarily treating "not yet checked" as "not logged in".
export const authChecked = writable(false);

function toAppUser(apiUser: {
	id: string;
	email: string;
	name: string;
	role: 'admin' | 'staff' | 'customer';
	avatarInitials: string;
}): AppUser {
	return {
		id: apiUser.id,
		email: apiUser.email,
		name: apiUser.name,
		role: apiUser.role,
		avatarInitials: apiUser.avatarInitials
	};
}

/**
 * Call once on app load (see +layout.svelte). Tries the customer session
 * first, then the admin/staff session -- whichever cookie is present (and
 * still valid) wins. If neither resolves, the user is simply logged out;
 * that's the normal case for a first-time visitor, not an error.
 */
export async function restoreSession() {
	if (!browser) return;
	try {
		try {
			const user = await customerApi.me();
			currentUser.set(toAppUser(user));
			return;
		} catch {
			// no customer session -- fall through and try admin/staff
		}

		try {
			const user = await adminApi.me();
			currentUser.set(toAppUser(user));
		} catch {
			currentUser.set(null);
		}
	} finally {
		authChecked.set(true);
	}
}

export async function registerCustomer(name: string, email: string, password: string) {
	await customerApi.register(name, email, password);
	// No session yet -- registration only sends the verification email.
	// The session begins when the link is confirmed (see verifyEmail).
}

export async function verifyEmail(token: string) {
	const user = await customerApi.verifyEmail(token);
	currentUser.set(toAppUser(user));
	return toAppUser(user);
}

export async function loginCustomer(email: string, password: string) {
	const user = await customerApi.login(email, password);
	currentUser.set(toAppUser(user));
	return toAppUser(user);
}

export async function loginAdmin(email: string, password: string) {
	const user = await adminApi.login(email, password);
	currentUser.set(toAppUser(user));
	return toAppUser(user);
}

export async function acceptStaffInvite(token: string, password: string) {
	const user = await adminApi.acceptInvite(token, password);
	currentUser.set(toAppUser(user));
	return toAppUser(user);
}

export async function logout() {
	const wasAdminSide = ['admin', 'staff'].includes(get(currentUser)?.role ?? '');
	currentUser.set(null);
	try {
		if (wasAdminSide) {
			await adminApi.logout();
		} else {
			await customerApi.logout();
		}
	} catch {
		// Cookie is cleared client-side regardless of network failure --
		// worst case the server-side cookie lingers until it expires.
	}
}

export { ApiError };
