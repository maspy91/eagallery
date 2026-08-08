<script lang="ts">
	// frontend/src/routes/register/+page.svelte
	// EDITED FILE — replaces: src/routes/register/+page.svelte (whole-file replacement)
	// Adds the Turnstile widget where the Phase 2 placeholder comment was.
	// If PUBLIC_TURNSTILE_SITE_KEY isn't set, the widget renders nothing
	// and turnstileRequired stays false, so submission behaves exactly as
	// it did before this change.

	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { UserPlus, Lock, Mail, User, Eye, EyeOff, CircleCheckBig } from '@lucide/svelte';
	import { currentUser, registerCustomer } from '$lib/stores/auth';
	import { registerSchema } from '$lib/validation';
	import { ApiError } from '$lib/api';
	import { PUBLIC_TURNSTILE_SITE_KEY } from '$env/static/public';
	import TurnstileWidget from '$lib/components/TurnstileWidget.svelte';

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';
	let showPassword = false;
	let loading = false;
	let formError = '';
	let submitted = false;

	const turnstileRequired = Boolean(PUBLIC_TURNSTILE_SITE_KEY);
	let turnstileToken: string | undefined;
	let turnstileWidget: TurnstileWidget;

	onMount(() => {
		if ($currentUser?.role === 'customer') goto('/dashboard');
	});

	async function handleSubmit() {
		formError = '';
		const parsed = registerSchema.safeParse({ name, email, password, confirmPassword });
		if (!parsed.success) {
			formError = parsed.error.errors[0].message;
			return;
		}
		if (turnstileRequired && !turnstileToken) {
			formError = 'Please complete the verification challenge.';
			return;
		}

		loading = true;
		try {
			await registerCustomer(name.trim(), email.trim(), password, turnstileToken);
			submitted = true;
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'Something went wrong. Please try again.';
			turnstileWidget?.reset();
			turnstileToken = undefined;
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Create Account — EddyArt Gallery</title>
</svelte:head>

<div class="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-16">
	<div class="w-full max-w-md animate-fade-in">
		{#if submitted}
			<div class="text-center mb-8">
				<div
					class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary mb-6"
				>
					<Mail class="w-8 h-8 text-primary-foreground" />
				</div>
				<h1 class="text-3xl font-bold text-foreground mb-2">Check your email</h1>
				<p class="text-muted-foreground">
					We've sent a verification link to <span class="text-foreground font-medium">{email}</span>. Click it
					to activate your account and sign in.
				</p>
			</div>
			<div class="glass elevated rounded-2xl p-8 text-center">
				<a href="/login" class="text-primary font-medium hover:underline">Back to sign in</a>
			</div>
		{:else}
			<div class="text-center mb-8">
				<div
					class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary mb-6"
				>
					<UserPlus class="w-8 h-8 text-primary-foreground" />
				</div>
				<h1 class="text-3xl font-bold text-foreground mb-2">Create your account</h1>
				<p class="text-muted-foreground">Follow conversations, get notified on replies, message us directly</p>
			</div>

			<div class="glass elevated rounded-2xl p-8">
				<form on:submit|preventDefault={handleSubmit} class="space-y-5">
					<div class="space-y-2">
						<label for="name" class="flex items-center gap-2 text-sm font-medium text-foreground">
							<User class="w-4 h-4 text-primary" />
							Full name
						</label>
						<input
							id="name"
							type="text"
							bind:value={name}
							required
							autocomplete="name"
							placeholder="Jane Doe"
							class="w-full h-12 px-4 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
						/>
					</div>

					<div class="space-y-2">
						<label for="email" class="flex items-center gap-2 text-sm font-medium text-foreground">
							<Mail class="w-4 h-4 text-primary" />
							Email
						</label>
						<input
							id="email"
							type="email"
							bind:value={email}
							required
							autocomplete="email"
							placeholder="you@example.com"
							class="w-full h-12 px-4 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
						/>
					</div>

					<div class="space-y-2">
						<label for="password" class="flex items-center gap-2 text-sm font-medium text-foreground">
							<Lock class="w-4 h-4 text-primary" />
							Password
						</label>
						<div class="relative">
							<input
								id="password"
								type={showPassword ? 'text' : 'password'}
								bind:value={password}
								required
								autocomplete="new-password"
								placeholder="••••••••"
								class="w-full h-12 px-4 pr-11 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
							/>
							<button
								type="button"
								on:click={() => (showPassword = !showPassword)}
								class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors"
								aria-label={showPassword ? 'Hide password' : 'Show password'}
							>
								{#if showPassword}<EyeOff class="w-4 h-4" />{:else}<Eye class="w-4 h-4" />{/if}
							</button>
						</div>
						<p class="flex items-center gap-1.5 text-xs text-muted-foreground">
							<CircleCheckBig class="w-3 h-3" />
							Minimum 8 characters
						</p>
					</div>

					<div class="space-y-2">
						<label for="confirm" class="flex items-center gap-2 text-sm font-medium text-foreground">
							<Lock class="w-4 h-4 text-primary" />
							Confirm password
						</label>
						<input
							id="confirm"
							type={showPassword ? 'text' : 'password'}
							bind:value={confirmPassword}
							required
							autocomplete="new-password"
							placeholder="••••••••"
							class="w-full h-12 px-4 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
						/>
					</div>

					<!-- Renders nothing when Turnstile isn't configured -->
					<TurnstileWidget
						bind:this={turnstileWidget}
						on:verified={(e) => (turnstileToken = e.detail)}
						on:expired={() => (turnstileToken = undefined)}
						on:error={() => (turnstileToken = undefined)}
					/>

					{#if formError}
						<p class="text-sm text-destructive text-center">{formError}</p>
					{/if}

					<button
						type="submit"
						disabled={loading}
						class="w-full h-12 rounded-xl bg-primary text-primary-foreground font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
					>
						{#if loading}
							<div class="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin" />
							Creating account...
						{:else}
							Create Account
						{/if}
					</button>
				</form>

				<p class="text-center text-sm text-muted-foreground mt-6">
					Already have an account?
					<a href="/login" class="text-primary font-medium hover:underline">Sign in</a>
				</p>
			</div>
		{/if}
	</div>
</div>
