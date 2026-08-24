export type Permission =
	| 'photos:manage' // upload, edit, delete, organize
	| 'roles:manage' // create/assign/revoke admin-assigned roles
	| 'comments:moderate' // hide/delete/approve comments
	| 'requests:respond' // respond to business/contact requests
	| 'analytics:view'; // dashboard metrics

export type RoleName = 'admin' | 'staff' | 'customer';

export const ROLE_PERMISSIONS: Record<RoleName, Permission[]> = {
	// Full, unrestricted access.
	admin: ['photos:manage', 'roles:manage', 'comments:moderate', 'requests:respond', 'analytics:view'],
	// Admin-assigned role: everything admin can do, except managing roles.
	staff: ['photos:manage', 'comments:moderate', 'requests:respond', 'analytics:view'],
	// Regular platform user.
	customer: []
};

export interface AppUser {
	id: string;
	email: string;
	name: string;
	role: RoleName;
	avatarInitials: string;
}

export function hasPermission(user: AppUser | null, permission: Permission): boolean {
	if (!user) return false;
	return ROLE_PERMISSIONS[user.role].includes(permission);
}

export interface GalleryItem {
	id: string;
	image: string;
	title: string;
	category: string;
	viewCount: number;
	likeCount: number;
	description: string;
	specs: string[];
	status: 'published' | 'draft' | 'flagged';
}

export interface CommentNode {
	id: string;
	author: string;
	authorId?: string; // set when the comment was posted by a logged-in customer
	text: string;
	timestamp: string;
	flagged?: boolean;
	replies: CommentNode[];
}

export interface ConversationMessage {
	id: string;
	senderRole: 'customer' | 'admin' | 'staff';
	senderName: string;
	text: string;
	timestamp: string;
}

/**
 * A business conversation is a single thread shared between one customer
 * and the platform's admin/staff. The customer sees it in their dashboard
 * Inbox; admin/staff see the exact same thread in Admin > Requests. There
 * is only one copy of this data — replying from either side appends to
 * the same `messages` array.
 */
export interface BusinessConversation {
	id: string;
	customerId: string;
	customerName: string;
	customerEmail: string;
	subject: string;
	status: 'new' | 'in_progress' | 'resolved';
	messages: ConversationMessage[];
	updatedAt: string;
}

export interface Testimonial {
	id: number;
	name: string;
	role: string;
	initials: string;
	quote: string;
	rating: number;
}

export interface AppNotification {
	id: string;
	userId: string;
	type: 'comment_reply' | 'conversation_reply' | 'system';
	message: string;
	href: string;
	read: boolean;
	timestamp: string;
}
