<script lang="ts">
	// Simplified now that dashboard/+layout.server.ts does the actual
	// guarding: this component is never rendered at all for an
	// unauthenticated request (the server redirects before it gets here).
	// Uses `data.user` (from the server load) for the "Signed in as"
	// display instead of the client-side $currentUser store, since
	// that's the value the server just verified.

	import { page } from '$app/stores';
	import { unreadCount as unreadCountStore } from '$lib/stores/notifications';
	import { LayoutDashboard, Bell, Inbox, MessagesSquare, ArrowLeft } from '@lucide/svelte';
	import type { LayoutData } from './$types';

	export let data: LayoutData;

	$: navItems = [
		{ href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
		{ href: '/dashboard/notifications', label: 'Notifications', icon: Bell, badge: $unreadCountStore },
		{ href: '/dashboard/inbox', label: 'Inbox', icon: Inbox },
		{ href: '/dashboard/conversations', label: 'My Conversations', icon: MessagesSquare }
	];
</script>

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
			Signed in as <span class="text-foreground font-medium">{data.user.name}</span>
		</div>
	</aside>

	<div class="min-w-0">
		<slot />
	</div>
</div>
