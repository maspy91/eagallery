<script lang="ts">
	// Same simplification as dashboard/+layout.svelte -- see that file for
	// the full reasoning. admin/+layout.server.ts now does the actual
	// guarding, and `data.user` (server-verified) replaces $currentUser
	// throughout this file.

	import { page } from '$app/stores';
	import { hasPermission } from '$lib/types';
	import {
		LayoutDashboard,
		Images,
		Video,
		Users,
		MessageSquareWarning,
		MessageCircle,
		Mail,
		ArrowLeft
	} from '@lucide/svelte';
	import type { LayoutData } from './$types';

	export let data: LayoutData;

	$: navItems = [
		{ href: '/admin', label: 'Overview', icon: LayoutDashboard, show: hasPermission(data.user, 'analytics:view') },
		{ href: '/admin/photos', label: 'Photos', icon: Images, show: hasPermission(data.user, 'photos:manage') },
		{ href: '/admin/videos', label: 'Videos', icon: Video, show: hasPermission(data.user, 'photos:manage') },
		{ href: '/admin/comments', label: 'Comments', icon: MessageSquareWarning, show: hasPermission(data.user, 'comments:moderate') },
		{ href: '/admin/requests', label: 'Requests', icon: Mail, show: hasPermission(data.user, 'requests:respond') },
		{ href: '/admin/chat', label: 'Live Chat', icon: MessageCircle, show: hasPermission(data.user, 'requests:respond') },
		{ href: '/admin/roles', label: 'Roles & Staff', icon: Users, show: hasPermission(data.user, 'roles:manage') }
	].filter((n) => n.show);
</script>

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
			Signed in as <span class="text-foreground font-medium">{data.user.name}</span>
			<span class="block mt-0.5 capitalize text-primary">{data.user.role}</span>
		</div>
	</aside>

	<div class="min-w-0">
		<slot />
	</div>
</div>
