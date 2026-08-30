<script lang="ts">
	import { KeyRound, Mail, ArrowLeft, CircleCheckBig } from '@lucide/svelte';
	import { forgotPasswordSchema } from '$lib/validation';
	import { passwordApi, ApiError } from '$lib/api';

	let email = '';
	let loading = false;
	let formError = '';
	let sent = false;

	async function handleSubmit() {
		formError = '';
		const parsed = forgotPasswordSchema.safeParse({ email });
		if (!parsed.success) {
			formError = parsed.error.issues[0].message;
			return;
		}
		loading = true;
		try {
			// Always the same "check your email" response whether or not the
			// address exists -- see app/routers/admin_auth.py -- so there's
			// nothing role- or existence-specific to branch on here.
			await passwordApi.forgot(email.trim());
			sent = true;
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'Something went wrong. Please try again.';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Reset Password — EddyArt Gallery</title>
</svelte:head>

<div class="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-16">
	<div class="w-full max-w-md animate-fade-in">
		<div class="text-center mb-8">
			<div
				class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary mb-6"
			>
				<KeyRound class="w-8 h-8 text-primary-foreground" />
			</div>
			<h1 class="text-3xl font-bold text-foreground mb-2">Forgot your password?</h1>
			<p class="text-muted-foreground">Enter your email and we'll send you a reset link</p>
		</div>

		<div class="glass elevated rounded-2xl p-8">
			{#if sent}
				<div class="text-center space-y-4 animate-fade-in">
					<div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-success/10">
						<CircleCheckBig class="w-7 h-7 text-success" />
					</div>
					<div>
						<p class="font-semibold text-foreground">Check your email</p>
						<p class="text-sm text-muted-foreground mt-1">
							If an account exists for <span class="text-foreground">{email}</span>, a reset link is on its way.
						</p>
					</div>
				</div>
			{:else}
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
							autocomplete="email"
							placeholder="you@example.com"
							class="w-full h-12 px-4 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
						/>
					</div>

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
							Sending...
						{:else}
							Send Reset Link
						{/if}
					</button>
				</form>
			{/if}
		</div>

		<a
			href="/login"
			class="flex items-center justify-center gap-2 text-sm text-muted-foreground hover:text-primary transition-smooth mt-6"
		>
			<ArrowLeft class="w-4 h-4" />
			Back to sign in
		</a>
	</div>
</div>
