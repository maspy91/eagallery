/**
 * Every call includes `credentials: 'include'` so the httpOnly session
 * cookie (set by the backend on login/verify/accept-invite) is sent
 * along. /api/* is always same-origin now (proxied -- vercel.json in
 * production, vite.config.ts's server.proxy in dev), so every path here
 * is relative with no base URL to configure.
 */

export class ApiError extends Error {
	status: number;
	constructor(status: number, message: string) {
		super(message);
		this.status = status;
	}
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
	const res = await fetch(path, {
		credentials: 'include',
		headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
		...options
	});

	let body: unknown = null;
	const text = await res.text();
	if (text) {
		try {
			body = JSON.parse(text);
		} catch {
			body = null;
		}
	}

	if (!res.ok) {
		const detail =
			body && typeof body === 'object' && 'detail' in body
				? String((body as { detail: unknown }).detail)
				: `Request failed (${res.status})`;
		throw new ApiError(res.status, detail);
	}

	return body as T;
}

function post<T>(path: string, payload: unknown): Promise<T> {
	return request<T>(path, { method: 'POST', body: JSON.stringify(payload) });
}

function get<T>(path: string): Promise<T> {
	return request<T>(path, { method: 'GET' });
}

function del<T>(path: string): Promise<T> {
	return request<T>(path, { method: 'DELETE' });
}

export interface ApiUser {
	id: string;
	email: string;
	name: string;
	role: 'admin' | 'staff' | 'customer';
	avatarInitials: string;
	emailVerified: boolean;
}

interface MessageResponse {
	message: string;
}

// ---- Customer auth (/api/customer/*) ----

export const customerApi = {
	register: (name: string, email: string, password: string, turnstileToken?: string) =>
		post<MessageResponse>('/api/customer/register', {
			name,
			email,
			password,
			turnstile_token: turnstileToken ?? null
		}),
	login: (email: string, password: string, turnstileToken?: string) =>
		post<ApiUser>('/api/customer/login', { email, password, turnstile_token: turnstileToken ?? null }),
	logout: () => post<MessageResponse>('/api/customer/logout', {}),
	me: () => get<ApiUser>('/api/customer/me'),
	verifyEmail: (token: string) => post<ApiUser>('/api/customer/verify-email', { token }),
	resendVerification: (email: string) => post<MessageResponse>('/api/customer/resend-verification', { email })
};

// ---- Admin / staff auth (/api/auth/*) ----

export const adminApi = {
	login: (email: string, password: string, turnstileToken?: string) =>
		post<ApiUser>('/api/auth/login', { email, password, turnstile_token: turnstileToken ?? null }),
	logout: () => post<MessageResponse>('/api/auth/logout', {}),
	me: () => get<ApiUser>('/api/auth/me'),
	inviteStaff: (name: string, email: string) => post<MessageResponse>('/api/auth/staff/invite', { name, email }),
	acceptInvite: (token: string, password: string) =>
		post<ApiUser>('/api/auth/staff/accept-invite', { token, password }),
	listStaff: () => get<ApiUser[]>('/api/auth/staff'),
	revokeStaff: (id: string) => del<MessageResponse>(`/api/auth/staff/${id}`)
};

// ---- Shared password recovery (/api/auth/*) ----

export const passwordApi = {
	forgot: (email: string) => post<MessageResponse>('/api/auth/forgot-password', { email }),
	reset: (token: string, password: string) => post<MessageResponse>('/api/auth/reset-password', { token, password })
};

// ---- Photos (/api/photos/*) ----

export interface ApiPhoto {
	id: string;
	image: string;
	title: string;
	category: string;
	viewCount: number;
	likeCount: number;
	description: string;
	specs: string[];
	status: 'draft' | 'published' | 'flagged';
	liked: boolean;
}

export interface PhotoListParams {
	status?: 'draft' | 'published' | 'flagged';
	category?: string;
	random?: number;
	limit?: number;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
	const usp = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined && value !== null && value !== '') usp.set(key, String(value));
	}
	const qs = usp.toString();
	return qs ? `?${qs}` : '';
}

export const photosApi = {
	list: (params: PhotoListParams = {}) => get<ApiPhoto[]>(`/api/photos${buildQuery(params)}`),
	get: (id: string) => get<ApiPhoto>(`/api/photos/${id}`),
	getUploadUrl: (filename: string, contentType: string) =>
		post<{ objectKey: string; uploadUrl: string; publicUrl: string }>('/api/photos/upload-url', {
			filename,
			content_type: contentType
		}),
	create: (input: { objectKey: string; title: string; category: string; description: string; specs: string[] }) =>
		post<ApiPhoto>('/api/photos', input),
	update: (
		id: string,
		input: Partial<{ title: string; category: string; description: string; specs: string[]; status: string }>
	) => request<ApiPhoto>(`/api/photos/${id}`, { method: 'PATCH', body: JSON.stringify(input) }),
	remove: (id: string) => del<MessageResponse>(`/api/photos/${id}`),
	toggleLike: (id: string) => post<{ liked: boolean; likeCount: number }>(`/api/photos/${id}/like`, {}),
	/**
	 * Uploads a file directly to storage with the presigned URL from
	 * getUploadUrl(). Deliberately NOT routed through `request()` above --
	 * this goes straight to the storage provider, not this backend, and
	 * isn't JSON.
	 */
	uploadToStorage: async (uploadUrl: string, file: File) => {
		const res = await fetch(uploadUrl, { method: 'PUT', headers: { 'Content-Type': file.type }, body: file });
		if (!res.ok) throw new ApiError(res.status, 'Upload to storage failed');
	}
};

// ---- Comments ----
// Two backend routes: /api/photos/{id}/comments (public read + create,
// nested tree, scoped to one photo) and /api/comments (moderation, flat,
// cross-photo -- what the admin "Comments" page lists).

export interface ApiComment {
	id: string;
	author: string;
	authorId: string | null;
	text: string;
	timestamp: string;
	flagged: boolean;
	replies: ApiComment[];
}

export interface ApiAdminComment extends ApiComment {
	photoId: string;
	photoTitle: string;
}

export const commentsApi = {
	list: (photoId: string) => get<ApiComment[]>(`/api/photos/${photoId}/comments`),
	create: (photoId: string, text: string, parentId?: string) =>
		post<ApiComment>(`/api/photos/${photoId}/comments`, { text, parent_id: parentId ?? null }),
	// Moderation (comments:moderate only):
	listAll: () => get<ApiAdminComment[]>('/api/comments'),
	setFlagged: (id: string, flagged: boolean) =>
		request<MessageResponse>(`/api/comments/${id}`, { method: 'PATCH', body: JSON.stringify({ flagged }) }),
	remove: (id: string) => del<MessageResponse>(`/api/comments/${id}`)
};

// ---- Business conversations ----
// One thread shared between a customer and admin/staff. Customers see
// their own via GET /mine; admin/staff see everyone's via GET (no
// suffix), gated by requests:respond. Replying is the same endpoint for
// both sides -- the backend figures out which one you are.

export interface ApiConversationMessage {
	id: string;
	senderRole: 'customer' | 'admin' | 'staff';
	senderName: string;
	text: string;
	timestamp: string;
}

export interface ApiConversation {
	id: string;
	customerId: string;
	customerName: string;
	customerEmail: string;
	subject: string;
	status: 'new' | 'in_progress' | 'resolved';
	messages: ApiConversationMessage[];
	updatedAt: string;
}

export const conversationsApi = {
	// Customer side:
	listMine: () => get<ApiConversation[]>('/api/conversations/mine'),
	create: (subject: string, text: string) => post<ApiConversation>('/api/conversations', { subject, text }),
	// Admin/staff side (requests:respond only):
	listAll: () => get<ApiConversation[]>('/api/conversations'),
	setStatus: (id: string, status: ApiConversation['status']) =>
		request<ApiConversation>(`/api/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
	// Shared -- works for either side, backend resolves who's calling:
	reply: (id: string, text: string) => post<ApiConversation>(`/api/conversations/${id}/messages`, { text })
};

// ---- Notifications ----
// Customer-only (matches Navbar.svelte's bell, which only ever renders
// for the customer nav). Created server-side by comment replies and
// admin/staff conversation replies -- nothing here ever creates one
// directly.

export interface ApiNotification {
	id: string;
	userId: string;
	type: 'comment_reply' | 'conversation_reply' | 'system';
	message: string;
	href: string;
	read: boolean;
	timestamp: string;
}

export const notificationsApi = {
	list: () => get<ApiNotification[]>('/api/notifications'),
	unreadCount: () => get<{ count: number }>('/api/notifications/unread-count'),
	markRead: (id: string) => post<ApiNotification>(`/api/notifications/${id}/read`, {}),
	markAllRead: () => post<MessageResponse>('/api/notifications/read-all', {})
};
