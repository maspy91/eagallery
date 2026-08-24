<script lang="ts">
	import { onMount } from 'svelte';
	import { Bell, MessageCircle, MessagesSquare, Info, CheckCheck, LoaderCircle } from '@lucide/svelte';
	import {
		notifications,
		loadNotifications,
		markNotificationRead,
		markAllNotificationsRead
	} from '$lib/stores/notifications';

	let loading = true;

	onMount(async () => {
		await loadNotifications();
		loading = false;
	});

	const icon = { comment_reply: MessageCircle, conversation_reply: MessagesSquare, system: Info };
</script>

<svelte:head><title>Notifications — EddyArt Gallery</title></svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between flex-wrap gap-4">
		<div>
			<h1 class="text-3xl font-bold text-foreground">Notifications</h1>
			<p class="text-muted-foreground mt-1">Replies to your comments and messages, in one place.</p>
		</div>
		<button
			on:click={markAllNotificationsRead}
			class="flex items-center gap-2 px-3 py-2 rounded-lg glass border-border/60 hover:border-primary/50 transition-smooth text-sm font-medium"
		>
			<CheckCheck class="w-4 h-4" />
			Mark all read
		</button>
	</div>

	<div class="glass elevated rounded-xl divide-y divide-border/60">
		{#if loading}
			<p class="text-center text-muted-foreground py-16">
				<LoaderCircle class="w-4 h-4 animate-spin inline-block mr-2" />
				Loading…
			</p>
		{:else}
			{#each $notifications as n (n.id)}
				<a
					href={n.href}
					on:click={() => markNotificationRead(n.id)}
					class="flex items-start gap-4 p-5 transition-colors {n.read ? '' : 'bg-primary/5'} hover:bg-muted/40"
				>
					<div class="w-9 h-9 shrink-0 rounded-full bg-primary/10 flex items-center justify-center">
						<svelte:component this={icon[n.type]} class="w-4 h-4 text-primary" />
					</div>
					<div class="flex-1 min-w-0">
						<p class="text-sm {n.read ? 'text-foreground/80' : 'font-medium text-foreground'}">{n.message}</p>
						<p class="text-xs text-muted-foreground mt-1">{new Date(n.timestamp).toLocaleString()}</p>
					</div>
					{#if !n.read}
						<span class="w-2 h-2 rounded-full bg-primary shrink-0 mt-1.5" />
					{/if}
				</a>
			{:else}
				<div class="text-center py-16 text-muted-foreground">
					<Bell class="w-10 h-10 mx-auto mb-3 opacity-50" />
					<p>You're all caught up.</p>
				</div>
			{/each}
		{/if}
	</div>
</div>
