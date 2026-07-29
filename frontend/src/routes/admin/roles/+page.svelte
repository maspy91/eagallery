<script lang="ts">
	import { onMount } from 'svelte';
	import { UserPlus, ShieldOff, LoaderCircle } from '@lucide/svelte';
	import { ROLE_PERMISSIONS } from '$lib/types';
	import type { AppUser } from '$lib/types';
	import { currentUser } from '$lib/stores/auth';
	import { adminApi, ApiError } from '$lib/api';

	let staff: AppUser[] = [];
	let loadingStaff = true;
	let listError = '';

	let inviteEmail = '';
	let inviteName = '';
	let inviting = false;
	let inviteError = '';
	let inviteSentMessage = '';

	let revokingId: string | null = null;

	function toAppUser(u: {
		id: string;
		email: string;
		name: string;
		role: 'admin' | 'staff' | 'customer';
		avatarInitials: string;
	}): AppUser {
		return { id: u.id, email: u.email, name: u.name, role: u.role, avatarInitials: u.avatarInitials };
	}

	async function loadStaff() {
		loadingStaff = true;
		listError = '';
		try {
			const result = await adminApi.listStaff();
			staff = result.map(toAppUser);
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not load staff list.';
		} finally {
			loadingStaff = false;
		}
	}

	onMount(loadStaff);

	async function invite() {
		inviteError = '';
		inviteSentMessage = '';
		if (!inviteEmail.trim() || !inviteName.trim()) return;

		inviting = true;
		try {
			await adminApi.inviteStaff(inviteName.trim(), inviteEmail.trim());
			inviteSentMessage = `Invite sent to ${inviteEmail.trim()}. They'll show up here once they accept it.`;
			inviteName = '';
			inviteEmail = '';
		} catch (err) {
			inviteError = err instanceof ApiError ? err.message : 'Could not send invite.';
		} finally {
			inviting = false;
		}
	}

	async function revoke(id: string) {
		revokingId = id;
		try {
			await adminApi.revokeStaff(id);
			staff = staff.filter((s) => s.id !== id);
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not revoke access.';
		} finally {
			revokingId = null;
		}
	}
</script>

<svelte:head><title>Roles & Staff — EddyArt Gallery Admin</title></svelte:head>

<div class="space-y-6">
	<div>
		<h1 class="text-3xl font-bold text-foreground">Roles & Staff</h1>
		<p class="text-muted-foreground mt-1">
			Assign the <span class="text-foreground font-medium">staff</span> role to give someone full admin
			capabilities except managing other roles.
		</p>
	</div>

	<div class="glass elevated rounded-xl p-6 grid sm:grid-cols-2 gap-6">
		<div class="rounded-lg border border-border p-4">
			<p class="font-semibold text-foreground mb-2">admin</p>
			<ul class="text-sm text-muted-foreground space-y-1">
				{#each ROLE_PERMISSIONS.admin as p}<li>• {p}</li>{/each}
			</ul>
		</div>
		<div class="rounded-lg border border-border p-4">
			<p class="font-semibold text-foreground mb-2">staff <span class="text-xs text-muted-foreground font-normal">(admin-assigned)</span></p>
			<ul class="text-sm text-muted-foreground space-y-1">
				{#each ROLE_PERMISSIONS.staff as p}<li>• {p}</li>{/each}
			</ul>
		</div>
	</div>

	<div class="glass elevated rounded-xl p-6">
		<h2 class="text-lg font-semibold text-foreground mb-4">Invite staff member</h2>
		<form on:submit|preventDefault={invite} class="flex flex-col sm:flex-row gap-3">
			<input
				bind:value={inviteName}
				placeholder="Full name"
				required
				class="flex-1 h-11 px-3 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			/>
			<input
				bind:value={inviteEmail}
				type="email"
				placeholder="email@example.com"
				required
				class="flex-1 h-11 px-3 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			/>
			<button
				type="submit"
				disabled={inviting}
				class="flex items-center justify-center gap-2 px-4 h-11 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50 text-sm font-medium whitespace-nowrap"
			>
				{#if inviting}
					<LoaderCircle class="w-4 h-4 animate-spin" />
				{:else}
					<UserPlus class="w-4 h-4" />
				{/if}
				Send invite
			</button>
		</form>
		{#if inviteError}
			<p class="text-xs text-destructive mt-2">{inviteError}</p>
		{:else if inviteSentMessage}
			<p class="text-xs text-success mt-2">{inviteSentMessage}</p>
		{:else}
			<p class="text-xs text-muted-foreground mt-2">
				Sends an invite email; the account isn't active until the invitee opens the link and sets a password.
			</p>
		{/if}
	</div>

	<div class="glass elevated rounded-xl overflow-hidden">
		{#if listError}
			<p class="text-sm text-destructive text-center py-6">{listError}</p>
		{:else}
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-border text-left text-muted-foreground">
						<th class="px-5 py-3 font-medium">Name</th>
						<th class="px-5 py-3 font-medium">Email</th>
						<th class="px-5 py-3 font-medium">Role</th>
						<th class="px-5 py-3 font-medium text-right">Actions</th>
					</tr>
				</thead>
				<tbody>
					{#if $currentUser}
						<tr class="border-b border-border/60">
							<td class="px-5 py-3 font-medium text-foreground">{$currentUser.name}</td>
							<td class="px-5 py-3 text-muted-foreground">{$currentUser.email}</td>
							<td class="px-5 py-3"><span class="px-2.5 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">admin</span></td>
							<td class="px-5 py-3 text-right text-xs text-muted-foreground">Owner</td>
						</tr>
					{/if}
					{#if loadingStaff}
						<tr>
							<td colspan="4" class="px-5 py-6 text-center text-muted-foreground">
								<LoaderCircle class="w-4 h-4 animate-spin inline-block mr-2" />
								Loading staff…
							</td>
						</tr>
					{:else}
						{#each staff as s (s.id)}
							<tr class="border-b border-border/60 last:border-0 hover:bg-muted/40 transition-colors">
								<td class="px-5 py-3 font-medium text-foreground">{s.name}</td>
								<td class="px-5 py-3 text-muted-foreground">{s.email}</td>
								<td class="px-5 py-3"><span class="px-2.5 py-1 rounded-full text-xs font-medium bg-secondary/10 text-secondary">staff</span></td>
								<td class="px-5 py-3">
									<div class="flex justify-end">
										<button
											on:click={() => revoke(s.id)}
											disabled={revokingId === s.id}
											class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
										>
											{#if revokingId === s.id}
												<LoaderCircle class="w-3.5 h-3.5 animate-spin" />
											{:else}
												<ShieldOff class="w-3.5 h-3.5" />
											{/if}
											Revoke
										</button>
									</div>
								</td>
							</tr>
						{:else}
							<tr>
								<td colspan="4" class="px-5 py-6 text-center text-muted-foreground">No staff members yet.</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		{/if}
	</div>
</div>
