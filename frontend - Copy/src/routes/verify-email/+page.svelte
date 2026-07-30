<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { MailCheck, CircleX, LoaderCircle } from '@lucide/svelte';
	import { verifyEmail, ApiError } from '$lib/stores/auth';

	$: token = $page.url.searchParams.get('token');

	let state: 'checking' | 'success' | 'error' = 'checking';
	let errorMessage = '';

	onMount(async () => {
		if (!token) {
			state = 'error';
			errorMessage = 'This link is missing its verification token.';
			return;
		}
		try {
			await verifyEmail(token);
			state = 'success';
		} catch (err) {
			state = 'error';
			errorMessage = err instanceof ApiError ? err.message : 'Something went wrong. Please try again.';
		}
	});
</script>

<svelte:head>
	<title>Verify Email — EddyArt Gallery</title>
</svelte:head>

<div class="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-16">
	<div class="w-full max-w-md animate-fade-in">
		<div class="glass elevated rounded-2xl p-8 text-center space-y-4">
			{#if state === 'checking'}
				<div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-primary/10">
					<LoaderCircle class="w-7 h-7 text-primary animate-spin" />
				</div>
				<p class="font-semibold text-foreground">Verifying your email…</p>
			{:else if state === 'success'}
				<div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-success/10">
					<MailCheck class="w-7 h-7 text-success" />
				</div>
				<div>
					<p class="font-semibold text-foreground">Email verified</p>
					<p class="text-sm text-muted-foreground mt-1">Your account is active and you're signed in.</p>
				</div>
				<a
					href="/dashboard"
					class="inline-block px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity"
				>
					Go to your dashboard
				</a>
			{:else}
				<div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-destructive/10">
					<CircleX class="w-7 h-7 text-destructive" />
				</div>
				<div>
					<p class="font-semibold text-foreground">Verification failed</p>
					<p class="text-sm text-muted-foreground mt-1">{errorMessage}</p>
				</div>
				<a href="/login" class="inline-block text-sm text-primary hover:underline">Back to sign in</a>
			{/if}
		</div>
	</div>
</div>
