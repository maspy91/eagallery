<script lang="ts">
	// frontend/src/routes/dashboard/+layout.svelte
	// EDITED FILE — replaces: src/routes/dashboard/+layout.svelte (whole-file replacement)
	// Only change: unreadCount now reads from the real notifications store
	// instead of mockNotifications. Everything else (the route guard,
	// layout, nav items) is unchanged.

	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { currentUser, authChecked } from '$lib/stores/auth';
	import { unreadCount as unreadCountStore } from '$lib/stores/notifications';
	import { LayoutDashboard, Bell, Inbox, MessagesSquare, ArrowLeft } from '@lucide/svelte';

	// PHASE 1 NOTE (still true in Phase 2): this is a client-side guard,
	// sufficient because the actual access boundary is server-side (every
	// /api/customer/* call re-checks the session cookie) -- this only
	// avoids flashing protected UI before redirecting. A hardened setup
	// would also add dashboard/+layout.server.ts reading the cookie so the
	// protected HTML/JS is never even sent, but that's a further step.
	onMount(() => {
		const unsub = authChecked.subscribe((done) => {
			if (!done) return;
			const u = $currentUser;
			if (!u) {
				goto('/login');
			} else if (u.role !== 'customer') {
				// Admin/staff have their own dashboard — keep the two areas separate.
				goto('/admin');
			}
		});
		return unsub;
	});

	$: unreadCount = $currentUser ? $unreadCountStore : 0;

	$: navItems = [
		{ href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
		{ href: '/dashboard/notifications', label: 'Notifications', icon: Bell, badge: unreadCount },
		{ href: '/dashboard/inbox', label: 'Inbox', icon: Inbox },
		{ href: '/dashboard/conversations', label: 'My Conversations', icon: MessagesSquare }
	];
</script>

{#if $authChecked && $currentUser?.role === 'customer'}
	<div class="max-w-6xl mx-auto px-4 py-8 grid lg:grid-cols-[220px_1fr] gap-8">
		<aside class="lg:sticky lg:top-24 lg:self-start space-y-1">
			<a href="/" class="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-smooth mb-4 px-2">
				<ArrowLeft class="w-3.5 h-3.5" />
				Back to site
			</a>
			<nav class="space-y-1">
				{#each navItems as item}
					<a
						href={item.href}
						class="flex items-center justify-between gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-smooth {$page.url.pathname === item.href
							? 'bg-primary/10 text-primary'
							: 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
					>
						<span class="flex items-center gap-2.5">
							<svelte:component this={item.icon} class="w-4 h-4" />
							{item.label}
						</span>
						{#if item.badge}
							<span class="min-w-[1.25rem] h-5 px-1 rounded-full bg-primary text-primary-foreground text-xs font-semibold flex items-center justify-center">
								{item.badge}
							</span>
						{/if}
					</a>
				{/each}
			</nav>
			<div class="glass rounded-lg p-3 mt-4 text-xs text-muted-foreground">
				Signed in as <span class="text-foreground font-medium">{$currentUser.name}</span>
			</div>
		</aside>

		<div class="min-w-0">
			<slot />
		</div>
	</div>
{:else}
	<div class="min-h-[60vh] flex items-center justify-center text-muted-foreground">Loading…</div>
{/if}
