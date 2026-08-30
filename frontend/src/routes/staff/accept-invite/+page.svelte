<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { UserCheck, Lock, Eye, EyeOff, CircleCheckBig } from '@lucide/svelte';
	import { resetPasswordSchema } from '$lib/validation';
	import { acceptStaffInvite, ApiError } from '$lib/stores/auth';

	$: token = $page.url.searchParams.get('token');

	let password = '';
	let confirmPassword = '';
	let showPassword = false;
	let loading = false;
	let formError = '';
	let done = false;

	async function handleSubmit() {
		formError = '';
		const parsed = resetPasswordSchema.safeParse({ password, confirmPassword });
		if (!parsed.success) {
			formError = parsed.error.issues[0].message;
			return;
		}
		if (!token) return;

		loading = true;
		try {
			await acceptStaffInvite(token, password);
			done = true;
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'Something went wrong. Please try again.';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Accept Invite — EddyArt Gallery</title>
</svelte:head>

<div class="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-16">
	<div class="w-full max-w-md animate-fade-in">
		<div class="text-center mb-8">
			<div
				class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary mb-6"
			>
				<UserCheck class="w-8 h-8 text-primary-foreground" />
			</div>
			<h1 class="text-3xl font-bold text-foreground mb-2">Join the team</h1>
			<p class="text-muted-foreground">Set a password to activate your staff account</p>
		</div>

		<div class="glass elevated rounded-2xl p-8">
			{#if !token}
				<p class="text-center text-sm text-destructive">
					This invite link is missing or invalid. Ask an admin to send you a new one.
				</p>
			{:else if done}
				<div class="text-center space-y-4 animate-fade-in">
					<div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-success/10">
						<CircleCheckBig class="w-7 h-7 text-success" />
					</div>
					<div>
						<p class="font-semibold text-foreground">You're all set</p>
						<p class="text-sm text-muted-foreground mt-1">Your staff account is active and you're signed in.</p>
					</div>
					<a
						href="/admin"
						class="inline-block px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity"
					>
						Go to admin dashboard
					</a>
				</div>
			{:else}
				<form on:submit|preventDefault={handleSubmit} class="space-y-5">
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
							Activating...
						{:else}
							Activate Account
						{/if}
					</button>
				</form>
			{/if}
		</div>
	</div>
</div>
