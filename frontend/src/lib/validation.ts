import { z } from 'zod';

export const emailSchema = z.string().email('Invalid email address').max(255);
export const passwordSchema = z.string().min(8, 'Password must be at least 8 characters').max(100);
// Deliberately looser than passwordSchema, matching the backend's
// LoginRequest (min_length=1, vs. RegisterRequest/ResetPasswordRequest's
// min_length=8) -- login must accept whatever an account's password
// already is, not what a *new* password is required to be. This matters
// most for the one bootstrap admin account: ADMIN_PASSWORD has no length
// validation at all server-side (see Settings in app/core/config.py), so
// requiring 8 chars here could lock an admin out of the only way into
// /admin even though the backend would have accepted their password.
export const loginPasswordSchema = z.string().min(1, 'Password is required').max(100);

export const loginSchema = z.object({
	email: emailSchema,
	password: loginPasswordSchema
});

export const registerSchema = z
	.object({
		name: z.string().trim().min(2, 'Name must be at least 2 characters').max(100),
		email: emailSchema,
		password: passwordSchema,
		confirmPassword: z.string()
	})
	.refine((data) => data.password === data.confirmPassword, {
		message: 'Passwords do not match',
		path: ['confirmPassword']
	});

export const forgotPasswordSchema = z.object({
	email: emailSchema
});

export const resetPasswordSchema = z
	.object({
		password: passwordSchema,
		confirmPassword: z.string()
	})
	.refine((data) => data.password === data.confirmPassword, {
		message: 'Passwords do not match',
		path: ['confirmPassword']
	});
