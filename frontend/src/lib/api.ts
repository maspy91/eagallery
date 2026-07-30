import { PUBLIC_API_URL } from '$env/static/public';

/**
 * Every call includes `credentials: 'include'` so the httpOnly session
 * cookie (set by the backend on login/verify/accept-invite) is sent with
 * same-site requests. PUBLIC_API_URL is normally left empty: the
 * recommended deployment proxies /api/* through a Vercel rewrite straight
 * to the Render backend (see vercel.json + DEPLOY.md), so relative paths
 * already reach it and everything is same-origin from the browser's point
 * of view. Set PUBLIC_API_URL only if calling the Render URL directly,
 * cross-site, instead.
 */
const BASE = PUBLIC_API_URL?.replace(/\/$/, '') ?? '';

export class ApiError extends Error {
	status: number;
	constructor(status: number, message: string) {
		super(message);
		this.status = status;
	}
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
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
	 * Uploads a file directly to R2 with the presigned URL from
	 * getUploadUrl(). Deliberately NOT routed through `request()` above --
	 * this goes straight to R2, not this backend, and isn't JSON.
	 */
	uploadToStorage: async (uploadUrl: string, file: File) => {
		const res = await fetch(uploadUrl, { method: 'PUT', headers: { 'Content-Type': file.type }, body: file });
		if (!res.ok) throw new ApiError(res.status, 'Upload to storage failed');
	}
};
