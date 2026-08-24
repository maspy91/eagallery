<script lang="ts">
	import { goto } from '$app/navigation';
	import { z } from 'zod';
	import { Eye, EyeOff, Shield, Lock, Mail, Sparkles, CircleCheckBig } from '@lucide/svelte';
	import { currentUser, loginAdmin } from '$lib/stores/auth';
	import { onMount } from 'svelte';
	import { ApiError } from '$lib/api';
	import { PUBLIC_TURNSTILE_SITE_KEY } from '$env/static/public';
	import TurnstileWidget from '$lib/components/TurnstileWidget.svelte';

	const authSchema = z.object({
		email: z.string().email('Invalid email address').max(255),
		password: z.string().min(8, 'Password must be at least 8 characters').max(100)
	});

	let email = '';
	let password = '';
	let showPassword = false;
	let loading = false;
	let formError = '';

	const turnstileRequired = Boolean(PUBLIC_TURNSTILE_SITE_KEY);
	let turnstileToken: string | undefined;
	let turnstileWidget: TurnstileWidget;

	onMount(() => {
		if ($currentUser) goto('/admin');
	});

	async function handleSubmit() {
		formError = '';
		const parsed = authSchema.safeParse({ email, password });
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
			await loginAdmin(email.trim(), password, turnstileToken);
			goto('/admin');
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
	<title>Admin Access — EddyArt Gallery</title>
</svelte:head>

<div class="min-h-[calc(100vh-4rem)] flex items-center justify-center relative overflow-hidden py-16 px-4">
	<div class="absolute inset-0 -z-10 bg-gradient-to-br from-background via-background to-primary/5" />
	<div
		class="absolute inset-0 -z-10"
		style="background-image: linear-gradient(hsl(var(--primary) / 0.06) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--primary) / 0.06) 1px, transparent 1px); background-size: 50px 50px;"
	/>
	<div class="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl -z-10" />
	<div class="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/10 rounded-full blur-3xl -z-10" />

	<div class="relative z-10 w-full max-w-md animate-fade-in">
		<div class="text-center mb-8">
			<div class="relative inline-block mb-6">
				<div
					class="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-primary via-secondary to-primary rotate-45 transition-transform hover:rotate-[405deg] duration-500"
				>
					<Shield class="w-10 h-10 text-primary-foreground -rotate-45" />
				</div>
			</div>
			<h1 class="text-4xl font-bold text-gradient mb-3">Admin Access</h1>
			<div class="flex items-center justify-center gap-2 text-muted-foreground">
				<Lock class="w-4 h-4" />
				<p>Sign in to manage the gallery</p>
			</div>
		</div>

		<div class="glass elevated rounded-3xl p-8 animate-scale-in">
			<form on:submit|preventDefault={handleSubmit} class="space-y-6">
				<div class="space-y-2">
					<label for="email" class="flex items-center gap-2 text-sm font-medium text-foreground">
						<Mail class="w-4 h-4 text-primary" />
						Email Address
					</label>
					<input
						id="email"
						type="email"
						placeholder="admin@eddyartgallery.app"
						bind:value={email}
						required
						autocomplete="username"
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
						{#if showPassword}
							<input
								id="password"
								type="text"
								placeholder="••••••••"
								bind:value={password}
								required
								autocomplete="current-password"
								class="w-full h-12 px-4 pr-11 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
							/>
						{:else}
							<input
								id="password"
								type="password"
								placeholder="••••••••"
								bind:value={password}
								required
								autocomplete="current-password"
								class="w-full h-12 px-4 pr-11 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
							/>
						{/if}
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
					class="w-full h-12 rounded-xl bg-gradient-to-r from-primary via-secondary to-primary text-primary-foreground font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
				>
					{#if loading}
						<div class="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin" />
						Signing in...
					{:else}
						<Shield class="w-4 h-4" />
						Sign In
					{/if}
				</button>
			</form>
		</div>

		<div class="mt-8 grid grid-cols-3 gap-4 animate-fade-in">
			{#each [{ icon: Shield, label: 'Secure' }, { icon: Lock, label: 'Encrypted' }, { icon: CircleCheckBig, label: 'Verified' }] as f}
				<div class="glass rounded-xl p-3 text-center hover:border-primary/30 transition-smooth border border-border/40">
					<svelte:component this={f.icon} class="w-5 h-5 text-primary mx-auto mb-1" />
					<p class="text-xs text-muted-foreground">{f.label}</p>
				</div>
			{/each}
		</div>

		<p class="text-center text-xs text-muted-foreground mt-6">
			This area is restricted to gallery administrators and assigned staff.
		</p>
	</div>
</div>
