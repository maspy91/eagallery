<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { currentUser, authChecked } from '$lib/stores/auth';
	import { hasPermission } from '$lib/types';
	import {
		LayoutDashboard,
		Images,
		Users,
		MessageSquareWarning,
		Mail,
		ArrowLeft
	} from '@lucide/svelte';

	// PHASE 1 NOTE (still true in Phase 2): client-side guard, sufficient
	// because the real access boundary is server-side (every /api/auth/*
	// call re-checks the admin_session cookie and role on every request) —
	// this only avoids flashing protected UI before redirecting. Waits for
	// authChecked so a real logged-in admin isn't bounced to /auth while
	// the initial "who am I?" request is still in flight.
	onMount(() => {
		const unsub = authChecked.subscribe((done) => {
			if (!done) return;
			const u = $currentUser;
			if (!u || u.role === 'customer') goto('/auth');
		});
		return unsub;
	});

	$: navItems = [
		{ href: '/admin', label: 'Overview', icon: LayoutDashboard, show: hasPermission($currentUser, 'analytics:view') },
		{ href: '/admin/photos', label: 'Photos', icon: Images, show: hasPermission($currentUser, 'photos:manage') },
		{ href: '/admin/comments', label: 'Comments', icon: MessageSquareWarning, show: hasPermission($currentUser, 'comments:moderate') },
		{ href: '/admin/requests', label: 'Requests', icon: Mail, show: hasPermission($currentUser, 'requests:respond') },
		{ href: '/admin/roles', label: 'Roles & Staff', icon: Users, show: hasPermission($currentUser, 'roles:manage') }
	].filter((n) => n.show);
</script>

{#if $authChecked && $currentUser}
	<div class="max-w-7xl mx-auto px-4 py-8 grid lg:grid-cols-[220px_1fr] gap-8">
		<aside class="lg:sticky lg:top-24 lg:self-start space-y-1">
			<a href="/" class="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-smooth mb-4 px-2">
				<ArrowLeft class="w-3.5 h-3.5" />
				Back to site
			</a>
			<nav class="space-y-1">
				{#each navItems as item}
					<a
						href={item.href}
						class="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-smooth {$page.url.pathname === item.href
							? 'bg-primary/10 text-primary'
							: 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
					>
						<svelte:component this={item.icon} class="w-4 h-4" />
						{item.label}
					</a>
				{/each}
			</nav>
			<div class="glass rounded-lg p-3 mt-4 text-xs text-muted-foreground">
				Signed in as <span class="text-foreground font-medium">{$currentUser.name}</span>
				<span class="block mt-0.5 capitalize text-primary">{$currentUser.role}</span>
			</div>
		</aside>

		<div class="min-w-0">
			<slot />
		</div>
	</div>
{:else}
	<div class="min-h-[60vh] flex items-center justify-center text-muted-foreground">Loading…</div>
{/if}
