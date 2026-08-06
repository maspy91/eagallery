<script lang="ts">
	// frontend/src/routes/dashboard/+page.svelte
	// EDITED FILE — replaces: src/routes/dashboard/+page.svelte (whole-file replacement)
	// Changes: "Unread notifications" now reads the real notifications
	// store. "Open conversations" now fetches real data via
	// conversationsApi.listMine() (this was flagged as a stale-data gap
	// after the conversations round, fixed here since this file needed
	// touching anyway). "Post threads you're in" is UNCHANGED and still
	// reads mockComments -- that's the separate dashboard/conversations
	// comment-thread feature, still out of scope.

	import { onMount } from 'svelte';
	import { Bell, Inbox, MessagesSquare, Plus } from '@lucide/svelte';
	import { currentUser } from '$lib/stores/auth';
	import { notifications } from '$lib/stores/notifications';
	import { mockComments, galleryItems } from '$lib/data/mock';
	import { conversationsApi, type ApiConversation } from '$lib/api';
	import type { CommentNode } from '$lib/types';

	$: myId = $currentUser?.id;

	$: unreadNotifications = $notifications.filter((n) => !n.read);

	let openConversations = 0;
	onMount(async () => {
		try {
			const mine: ApiConversation[] = await conversationsApi.listMine();
			openConversations = mine.filter((c) => c.status !== 'resolved').length;
		} catch {
			// leave at 0 -- not worth surfacing an error for a dashboard stat card
		}
	});

	function countMyThreads(): number {
		let count = 0;
		for (const nodes of Object.values(mockComments)) {
			const walk = (list: CommentNode[]) => {
				for (const c of list) {
					if (c.authorId === myId) count++;
					if (c.replies.length) walk(c.replies);
				}
			};
			walk(nodes);
		}
		return count;
	}
	$: myThreadCount = countMyThreads();
</script>

<svelte:head><title>Dashboard — EddyArt Gallery</title></svelte:head>

<div class="space-y-8">
	<div>
		<h1 class="text-3xl font-bold text-foreground">Welcome back{$currentUser ? `, ${$currentUser.name.split(' ')[0]}` : ''}</h1>
		<p class="text-muted-foreground mt-1">Here's what's new since your last visit.</p>
	</div>

	<div class="grid sm:grid-cols-3 gap-4">
		<a href="/dashboard/notifications" class="glass elevated rounded-xl p-5 hover:border-primary/30 border border-transparent transition-smooth">
			<div class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-3">
				<Bell class="w-5 h-5 text-primary" />
			</div>
			<p class="text-2xl font-bold text-foreground">{unreadNotifications.length}</p>
			<p class="text-sm text-muted-foreground">Unread notifications</p>
		</a>

		<a href="/dashboard/inbox" class="glass elevated rounded-xl p-5 hover:border-primary/30 border border-transparent transition-smooth">
			<div class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-3">
				<Inbox class="w-5 h-5 text-primary" />
			</div>
			<p class="text-2xl font-bold text-foreground">{openConversations}</p>
			<p class="text-sm text-muted-foreground">Open conversations</p>
		</a>

		<a href="/dashboard/conversations" class="glass elevated rounded-xl p-5 hover:border-primary/30 border border-transparent transition-smooth">
			<div class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-3">
				<MessagesSquare class="w-5 h-5 text-primary" />
			</div>
			<p class="text-2xl font-bold text-foreground">{myThreadCount}</p>
			<p class="text-sm text-muted-foreground">Post threads you're in</p>
		</a>
	</div>

	<div class="glass elevated rounded-xl p-6 flex items-center justify-between flex-wrap gap-4">
		<div>
			<h2 class="text-lg font-semibold text-foreground">Have a question for the team?</h2>
			<p class="text-sm text-muted-foreground mt-1">
				Start a direct conversation with the platform owner — licensing, partnerships, or anything else.
			</p>
		</div>
		<a
			href="/dashboard/inbox?new=1"
			class="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm font-medium whitespace-nowrap"
		>
			<Plus class="w-4 h-4" />
			New conversation
		</a>
	</div>

	{#if unreadNotifications.length > 0}
		<div class="glass elevated rounded-xl p-6">
			<h2 class="text-lg font-semibold text-foreground mb-4">Recent notifications</h2>
			<ul class="space-y-3">
				{#each unreadNotifications.slice(0, 3) as n (n.id)}
					<li>
						<a href={n.href} class="flex items-start gap-3 text-sm hover:text-primary transition-colors">
							<span class="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
							<span class="text-foreground/90">{n.message}</span>
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if galleryItems.length > 0}
		<div class="glass elevated rounded-xl p-6">
			<h2 class="text-lg font-semibold text-foreground mb-1">Browse the gallery</h2>
			<p class="text-sm text-muted-foreground mb-4">Leave a comment on any item — you'll get notified when someone replies.</p>
			<a href="/" class="text-sm text-primary hover:underline">Go to gallery →</a>
		</div>
	{/if}
</div>
