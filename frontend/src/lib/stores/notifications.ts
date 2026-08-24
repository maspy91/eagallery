import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { notificationsApi, type ApiNotification } from '$lib/api';

/**
 * Mirrors the auth store's pattern: this is a client-side cache of
 * server state, hydrated on demand, never the source of truth. Kept
 * separate from stores/auth.ts (rather than folding into currentUser)
 * so pages that don't care about notifications don't pull this in.
 */
export const notifications = writable<ApiNotification[]>([]);

export const unreadCount = derived(notifications, ($n) => $n.filter((n) => !n.read).length);

export async function loadNotifications() {
	if (!browser) return;
	try {
		notifications.set(await notificationsApi.list());
	} catch {
		// Not logged in as a customer, or a network hiccup -- either way,
		// leave notifications empty rather than surface an error for what
		// is, on most pages, a background refresh.
	}
}

export async function markNotificationRead(id: string) {
	const previous = get(notifications);
	notifications.set(previous.map((n) => (n.id === id ? { ...n, read: true } : n)));
	try {
		await notificationsApi.markRead(id);
	} catch {
		notifications.set(previous); // roll back on failure
	}
}

export async function markAllNotificationsRead() {
	const previous = get(notifications);
	notifications.set(previous.map((n) => ({ ...n, read: true })));
	try {
		await notificationsApi.markAllRead();
	} catch {
		notifications.set(previous); // roll back on failure
	}
}

export function clearNotifications() {
	notifications.set([]);
}
