<script lang="ts">
	import { onMount } from 'svelte';
	import { Images, Eye, Heart, Mail, MessageSquareWarning, Video, MessageCircle } from '@lucide/svelte';
	import { photosApi, videosApi, conversationsApi, commentsApi, adminChatApi } from '$lib/api';

	// Was deriving every number on this page from photosApi.list({limit:
	// 100})/conversationsApi.listAll()/commentsApi.listAll() and reducing
	// client-side -- correct until a gallery passed 100 photos (silent
	// undercount past that cap) and wasteful regardless, since it fetched
	// every row on every dashboard load just to show four numbers. Now
	// backed by dedicated SQL COUNT/SUM aggregate endpoints (analytics:view
	// / requests:respond), each accurate at any scale.
	//
	// Video stats and the AI chat handoff queue count were both entirely
	// absent from this page before, despite video being a full feature
	// (its own moderation queue, likes/views) and a waiting chat being the
	// single most time-sensitive thing on the whole platform -- a lead
	// sitting unanswered in the queue was invisible from the page admins
	// actually land on.
	let publishedCount = 0;
	let totalViews = 0;
	let totalLikes = 0;
	let flaggedCount = 0;
	let publishedVideoCount = 0;
	let totalVideoViews = 0;
	let totalVideoLikes = 0;
	let flaggedVideoCount = 0;
	let newRequests = 0;
	let totalComments = 0;
	let waitingChats = 0;
	let loading = true;

	onMount(async () => {
		try {
			const [photoStats, videoStats, conversationStats, commentStats, chatStats] = await Promise.all([
				photosApi.stats(),
				videosApi.stats(),
				conversationsApi.stats(),
				commentsApi.stats(),
				adminChatApi.stats()
			]);
			publishedCount = photoStats.publishedCount;
			totalViews = photoStats.totalViews;
			totalLikes = photoStats.totalLikes;
			flaggedCount = photoStats.flaggedCount;
			publishedVideoCount = videoStats.publishedCount;
			totalVideoViews = videoStats.totalViews;
			totalVideoLikes = videoStats.totalLikes;
			flaggedVideoCount = videoStats.flaggedCount;
			newRequests = conversationStats.openCount;
			totalComments = commentStats.count;
			waitingChats = chatStats.waitingCount;
		} catch {
			// leave whatever loaded -- stat cards below just show 0 for
			// whichever call failed rather than blocking the whole page
		} finally {
			loading = false;
		}
	});

	$: photoStatsRow = [
		{ label: 'Published photos', value: publishedCount, icon: Images },
		{ label: 'Photo views', value: totalViews.toLocaleString(), icon: Eye },
		{ label: 'Photo likes', value: totalLikes.toLocaleString(), icon: Heart },
		{ label: 'Open requests', value: newRequests, icon: Mail },
	];

	$: videoStatsRow = [
		{ label: 'Published videos', value: publishedVideoCount, icon: Video },
		{ label: 'Video views', value: totalVideoViews.toLocaleString(), icon: Eye },
		{ label: 'Video likes', value: totalVideoLikes.toLocaleString(), icon: Heart },
		{ label: 'Chats awaiting reply', value: waitingChats, icon: MessageCircle },
	];
</script>

<svelte:head><title>Dashboard — EddyArt Admin</title></svelte:head>

<div class="space-y-8">
	<div>
		<h1 class="text-3xl font-bold text-foreground">Overview</h1>
		<p class="text-muted-foreground mt-1">A quick look at what's happening on the platform.</p>
	</div>

	<div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
		{#each photoStatsRow as stat}
			<div class="glass elevated rounded-xl p-5">
				<div class="flex items-center justify-between mb-3">
					<div class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
						<svelte:component this={stat.icon} class="w-5 h-5 text-primary" />
					</div>
				</div>
				<p class="text-2xl font-bold text-foreground">{stat.value}</p>
				<p class="text-sm text-muted-foreground">{stat.label}</p>
			</div>
		{/each}
	</div>

	<div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
		{#each videoStatsRow as stat}
			<div class="glass elevated rounded-xl p-5">
				<div class="flex items-center justify-between mb-3">
					<div class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
						<svelte:component this={stat.icon} class="w-5 h-5 text-primary" />
					</div>
				</div>
				<p class="text-2xl font-bold text-foreground">{stat.value}</p>
				<p class="text-sm text-muted-foreground">{stat.label}</p>
			</div>
		{/each}
	</div>

	{#if waitingChats > 0}
		<div class="glass elevated rounded-xl p-5 border border-primary/30 flex items-start gap-3">
			<MessageCircle class="w-5 h-5 text-primary shrink-0 mt-0.5" />
			<div>
				<p class="font-medium text-foreground">{waitingChats} chat{waitingChats > 1 ? 's' : ''} waiting for a reply</p>
				<a href="/admin/chat" class="text-sm text-primary hover:underline">Respond in Chat →</a>
			</div>
		</div>
	{/if}

	{#if flaggedCount > 0}
		<div class="glass elevated rounded-xl p-5 border border-destructive/30 flex items-start gap-3">
			<MessageSquareWarning class="w-5 h-5 text-destructive shrink-0 mt-0.5" />
			<div>
				<p class="font-medium text-foreground">{flaggedCount} photo{flaggedCount > 1 ? 's' : ''} flagged for review</p>
				<a href="/admin/photos" class="text-sm text-primary hover:underline">Review in Photos →</a>
			</div>
		</div>
	{/if}

	{#if flaggedVideoCount > 0}
		<div class="glass elevated rounded-xl p-5 border border-destructive/30 flex items-start gap-3">
			<MessageSquareWarning class="w-5 h-5 text-destructive shrink-0 mt-0.5" />
			<div>
				<p class="font-medium text-foreground">{flaggedVideoCount} video{flaggedVideoCount > 1 ? 's' : ''} flagged for review</p>
				<a href="/admin/videos" class="text-sm text-primary hover:underline">Review in Videos →</a>
			</div>
		</div>
	{/if}

	<div class="glass elevated rounded-xl p-6">
		<h2 class="text-lg font-semibold text-foreground mb-4">Recent activity</h2>
		<ul class="space-y-3 text-sm">
			<li class="flex justify-between text-muted-foreground">
				<span>{totalComments} comments across the gallery</span>
				<a href="/admin/comments" class="text-primary hover:underline">Moderate →</a>
			</li>
			<li class="flex justify-between text-muted-foreground">
				<span>{newRequests} unanswered business request{newRequests === 1 ? '' : 's'}</span>
				<a href="/admin/requests" class="text-primary hover:underline">Respond →</a>
			</li>
			<li class="flex justify-between text-muted-foreground">
				<span>{waitingChats} chat{waitingChats === 1 ? '' : 's'} waiting in the AI handoff queue</span>
				<a href="/admin/chat" class="text-primary hover:underline">Respond →</a>
			</li>
		</ul>
	</div>
</div>
