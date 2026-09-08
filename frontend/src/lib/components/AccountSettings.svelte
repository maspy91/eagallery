<script lang="ts">
	// Shared between /dashboard/settings (customer) and /admin/settings
	// (admin/staff) -- the three actions this calls (updateProfileName,
	// changeEmail, changePassword) already route to the correct backend
	// (/api/customer/* vs /api/auth/*) based on the current session's
	// role, so this component itself doesn't need to know which side
	// it's rendering on for anything except the one UX hint below about
	// re-verifying a changed email.

	import { User, Mail, Lock, Eye, EyeOff, CircleCheckBig, BadgeCheck, BadgeAlert } from '@lucide/svelte';
	import { invalidateAll } from '$app/navigation';
	import { currentUser, updateProfileName, changeEmail, changePassword } from '$lib/stores/auth';
	import { updateNameSchema, changeEmailSchema, changePasswordSchema } from '$lib/validation';
	import { ApiError } from '$lib/api';

	function errorMessage(err: unknown, fallback: string): string {
		return err instanceof ApiError ? err.message : fallback;
	}

	// ---- Profile (name) ----
	let name = $currentUser?.name ?? '';
	let nameSaving = false;
	let nameError = '';
	let nameSaved = false;

	async function saveName() {
		nameError = '';
		nameSaved = false;
		const parsed = updateNameSchema.safeParse({ name });
		if (!parsed.success) {
			nameError = parsed.error.issues[0].message;
			return;
		}
		nameSaving = true;
		try {
			await updateProfileName(parsed.data.name);
			nameSaved = true;
			// The sidebar's "Signed in as {data.user.name}" text comes from
			// the layout's server load, not this component's $currentUser
			// read -- without this it wouldn't reflect the new name until
			// the next unrelated navigation happened to rerun that load.
			await invalidateAll();
		} catch (err) {
			nameError = errorMessage(err, 'Could not update your name. Please try again.');
		} finally {
			nameSaving = false;
		}
	}

	// ---- Email ----
	let showEmailForm = false;
	let newEmail = '';
	let emailCurrentPassword = '';
	let emailSaving = false;
	let emailError = '';
	let emailChanged = false;

	async function saveEmail() {
		emailError = '';
		const parsed = changeEmailSchema.safeParse({ email: newEmail, currentPassword: emailCurrentPassword });
		if (!parsed.success) {
			emailError = parsed.error.issues[0].message;
			return;
		}
		emailSaving = true;
		try {
			await changeEmail(parsed.data.email, parsed.data.currentPassword);
			emailChanged = true;
			showEmailForm = false;
			newEmail = '';
			emailCurrentPassword = '';
			await invalidateAll();
		} catch (err) {
			emailError = errorMessage(err, 'Could not update your email. Please try again.');
		} finally {
			emailSaving = false;
		}
	}

	// ---- Password ----
	let currentPassword = '';
	let newPassword = '';
	let confirmNewPassword = '';
	let showPasswords = false;
	let passwordSaving = false;
	let passwordError = '';
	let passwordChanged = false;

	async function savePassword() {
		passwordError = '';
		passwordChanged = false;
		const parsed = changePasswordSchema.safeParse({ currentPassword, newPassword, confirmNewPassword });
		if (!parsed.success) {
			passwordError = parsed.error.issues[0].message;
			return;
		}
		passwordSaving = true;
		try {
			await changePassword(parsed.data.currentPassword, parsed.data.newPassword);
			passwordChanged = true;
			currentPassword = '';
			newPassword = '';
			confirmNewPassword = '';
		} catch (err) {
			passwordError = errorMessage(err, 'Could not update your password. Please try again.');
		} finally {
			passwordSaving = false;
		}
	}
</script>

<div class="space-y-6">
	<!-- Profile -->
	<div class="glass elevated rounded-xl p-6">
		<h2 class="text-lg font-semibold text-foreground flex items-center gap-2 mb-1">
			<User class="w-4 h-4 text-primary" />
			Profile
		</h2>
		<p class="text-sm text-muted-foreground mb-4">Your display name across the site.</p>

		<form on:submit|preventDefault={saveName} class="flex flex-col sm:flex-row gap-3 sm:items-end">
			<div class="flex-1 space-y-1.5">
				<label for="name" class="text-sm font-medium text-foreground">Name</label>
				<input
					id="name"
					type="text"
					bind:value={name}
					required
					class="w-full h-11 px-4 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
				/>
			</div>
			<button
				type="submit"
				disabled={nameSaving}
				class="h-11 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 whitespace-nowrap"
			>
				{nameSaving ? 'Saving...' : 'Save name'}
			</button>
		</form>
		{#if nameError}
			<p class="text-sm text-destructive mt-2">{nameError}</p>
		{/if}
		{#if nameSaved}
			<p class="text-sm text-success mt-2 flex items-center gap-1.5">
				<CircleCheckBig class="w-3.5 h-3.5" /> Name updated.
			</p>
		{/if}
	</div>

	<!-- Email -->
	<div class="glass elevated rounded-xl p-6">
		<h2 class="text-lg font-semibold text-foreground flex items-center gap-2 mb-1">
			<Mail class="w-4 h-4 text-primary" />
			Email address
		</h2>
		<p class="text-sm text-muted-foreground mb-4">
			Changing your email requires your current password{#if $currentUser?.role === 'customer'} and a new
				verification link{/if}.
		</p>

		<div class="flex items-center justify-between gap-3 flex-wrap">
			<div class="flex items-center gap-2">
				<span class="text-foreground">{$currentUser?.email}</span>
				{#if $currentUser?.emailVerified}
					<span class="inline-flex items-center gap-1 text-xs text-success">
						<BadgeCheck class="w-3.5 h-3.5" /> Verified
					</span>
				{:else}
					<span class="inline-flex items-center gap-1 text-xs text-amber-500">
						<BadgeAlert class="w-3.5 h-3.5" /> Not verified
					</span>
				{/if}
			</div>
			{#if !showEmailForm}
				<button
					type="button"
					on:click={() => (showEmailForm = true)}
					class="text-sm text-primary hover:underline"
				>
					Change email
				</button>
			{/if}
		</div>

		{#if showEmailForm}
			<form on:submit|preventDefault={saveEmail} class="space-y-3 mt-4 pt-4 border-t border-border/60">
				<div class="space-y-1.5">
					<label for="new-email" class="text-sm font-medium text-foreground">New email</label>
					<input
						id="new-email"
						type="email"
						bind:value={newEmail}
						required
						autocomplete="email"
						class="w-full h-11 px-4 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
					/>
				</div>
				<div class="space-y-1.5">
					<label for="email-current-password" class="text-sm font-medium text-foreground">
						Current password
					</label>
					<input
						id="email-current-password"
						type="password"
						bind:value={emailCurrentPassword}
						required
						autocomplete="current-password"
						class="w-full h-11 px-4 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
					/>
				</div>
				{#if emailError}
					<p class="text-sm text-destructive">{emailError}</p>
				{/if}
				<div class="flex gap-3">
					<button
						type="submit"
						disabled={emailSaving}
						class="h-11 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
					>
						{emailSaving ? 'Saving...' : 'Save email'}
					</button>
					<button
						type="button"
						on:click={() => {
							showEmailForm = false;
							emailError = '';
						}}
						class="h-11 px-5 rounded-lg glass border-border/60 text-sm font-medium hover:border-primary/50 transition-smooth"
					>
						Cancel
					</button>
				</div>
			</form>
		{/if}
		{#if emailChanged}
			<p class="text-sm text-success mt-3 flex items-center gap-1.5">
				<CircleCheckBig class="w-3.5 h-3.5" />
				{#if $currentUser?.role === 'customer'}
					Email updated. Check your new inbox for a verification link.
				{:else}
					Email updated.
				{/if}
			</p>
		{/if}
	</div>

	<!-- Password -->
	<div class="glass elevated rounded-xl p-6">
		<h2 class="text-lg font-semibold text-foreground flex items-center gap-2 mb-1">
			<Lock class="w-4 h-4 text-primary" />
			Password
		</h2>
		<p class="text-sm text-muted-foreground mb-4">You'll stay signed in on this device after changing it.</p>

		<form on:submit|preventDefault={savePassword} class="space-y-3">
			<div class="space-y-1.5">
				<label for="current-password" class="text-sm font-medium text-foreground">Current password</label>
				<div class="relative">
					<input
						id="current-password"
						type={showPasswords ? 'text' : 'password'}
						bind:value={currentPassword}
						required
						autocomplete="current-password"
						class="w-full h-11 px-4 pr-11 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
					/>
					<button
						type="button"
						on:click={() => (showPasswords = !showPasswords)}
						class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors"
						aria-label={showPasswords ? 'Hide passwords' : 'Show passwords'}
					>
						{#if showPasswords}<EyeOff class="w-4 h-4" />{:else}<Eye class="w-4 h-4" />{/if}
					</button>
				</div>
			</div>
			<div class="space-y-1.5">
				<label for="new-password" class="text-sm font-medium text-foreground">New password</label>
				<input
					id="new-password"
					type={showPasswords ? 'text' : 'password'}
					bind:value={newPassword}
					required
					autocomplete="new-password"
					class="w-full h-11 px-4 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
				/>
			</div>
			<div class="space-y-1.5">
				<label for="confirm-new-password" class="text-sm font-medium text-foreground">
					Confirm new password
				</label>
				<input
					id="confirm-new-password"
					type={showPasswords ? 'text' : 'password'}
					bind:value={confirmNewPassword}
					required
					autocomplete="new-password"
					class="w-full h-11 px-4 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-smooth"
				/>
			</div>
			{#if passwordError}
				<p class="text-sm text-destructive">{passwordError}</p>
			{/if}
			<button
				type="submit"
				disabled={passwordSaving}
				class="h-11 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
			>
				{passwordSaving ? 'Saving...' : 'Update password'}
			</button>
			{#if passwordChanged}
				<p class="text-sm text-success flex items-center gap-1.5">
					<CircleCheckBig class="w-3.5 h-3.5" /> Password updated.
				</p>
			{/if}
		</form>
	</div>
</div>
