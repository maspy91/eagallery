import { z } from 'zod';

export const emailSchema = z.string().email('Invalid email address').max(255);
export const passwordSchema = z.string().min(8, 'Password must be at least 8 characters').max(100);

export const loginSchema = z.object({
	email: emailSchema,
	password: passwordSchema
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
