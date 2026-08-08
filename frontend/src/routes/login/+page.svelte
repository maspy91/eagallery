<script lang="ts">
	// frontend/src/routes/login/+page.svelte
	// EDITED FILE — replaces: src/routes/login/+page.svelte (whole-file replacement)
	// Adds the Turnstile widget where the Phase 2 placeholder comment was.
	// Same graceful no-op behavior as register/+page.svelte when
	// PUBLIC_TURNSTILE_SITE_KEY isn't set.

	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { User, Lock, Mail, Eye, EyeOff } from '@lucide/svelte';
	import { currentUser, loginCustomer } from '$lib/stores/auth';
	import { loginSchema } from '$lib/validation';
	import { ApiError } from '$lib/api';
	import { PUBLIC_TURNSTILE_SITE_KEY } from '$env/static/public';
	import TurnstileWidget from '$lib/components/TurnstileWidget.svelte';

	let email = '';
	let password = '';
	let showPassword = false;
	let loading = false;
	let formError = '';

	const turnstileRequired = Boolean(PUBLIC_TURNSTILE_SITE_KEY);
	let turnstileToken: string | undefined;
	let turnstileWidget: TurnstileWidget;

	onMount(() => {
		if ($currentUser?.role === 'customer') goto('/dashboard');
	});

	async function handleSubmit() {
		formError = '';
		const parsed = loginSchema.safeParse({ email, password });
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
			await loginCustomer(email.trim(), password, turnstileToken);
			goto('/dashboard');
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
	<title>Sign In — EddyArt Gallery</title>
</svelte:head>

<div class="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-16">
	<div class="w-full max-w-md animate-fade-in">
		<div class="text-center mb-8">
			<div
				class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary mb-6"
			>
				<User class="w-8 h-8 text-primary-foreground" />
			</div>
			<h1 class="text-3xl font-bold text-foreground mb-2">Welcome back</h1>
			<p class="text-muted-foreground">Sign in to follow your conversations and updates</p>
		</div>

		<div class="glass elevated rounded-2xl p-8">
			<form on:submit|preventDefault={handleSubmit} class="space-y-5">
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
						autocomplete="username"
						placeholder="you@example.com"
						class="w-full h-12 px-4 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
					/>
				</div>

				<div class="space-y-2">
					<div class="flex items-center justify-between">
						<label for="password" class="flex items-center gap-2 text-sm font-medium text-foreground">
							<Lock class="w-4 h-4 text-primary" />
							Password
						</label>
						<a href="/forgot-password" class="text-xs text-primary hover:underline">Forgot password?</a>
					</div>
					<div class="relative">
						<input
							id="password"
							type={showPassword ? 'text' : 'password'}
							bind:value={password}
							required
							autocomplete="current-password"
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
						Signing in...
					{:else}
						Sign In
					{/if}
				</button>
			</form>

			<p class="text-center text-sm text-muted-foreground mt-6">
				Don't have an account?
				<a href="/register" class="text-primary font-medium hover:underline">Create one</a>
			</p>
		</div>

		<p class="text-center text-xs text-muted-foreground mt-6">
			Platform team?
			<a href="/auth" class="text-primary hover:underline">Admin sign in</a>
		</p>
	</div>
</div>
