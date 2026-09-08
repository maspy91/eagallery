export type Permission =
	| 'photos:manage' // upload, edit, delete, organize
	| 'roles:manage' // create/assign/revoke admin-assigned roles
	| 'comments:moderate' // hide/delete/approve comments
	| 'requests:respond' // respond to business/contact requests
	| 'analytics:view' // dashboard metrics
	| 'customers:manage'; // view/search/(de)activate customer accounts

export type RoleName = 'admin' | 'staff' | 'customer';

export const ROLE_PERMISSIONS: Record<RoleName, Permission[]> = {
	// Full, unrestricted access.
	admin: ['photos:manage', 'roles:manage', 'comments:moderate', 'requests:respond', 'analytics:view', 'customers:manage'],
	// Admin-assigned role: everything admin can do, except managing roles
	// and customer accounts -- both are account-level control over
	// someone else's account, kept at the same tier.
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
	emailVerified: boolean;
}

export function hasPermission(user: AppUser | null, permission: Permission): boolean {
	if (!user) return false;
	return ROLE_PERMISSIONS[user.role].includes(permission);
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
