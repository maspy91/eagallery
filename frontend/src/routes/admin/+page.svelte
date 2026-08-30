<script lang="ts">
	import { onMount } from 'svelte';
	import { Images, Eye, Heart, Mail, MessageSquareWarning } from '@lucide/svelte';
	import { photosApi, conversationsApi, commentsApi, type ApiPhoto, type ApiConversation, type ApiAdminComment } from '$lib/api';

	// Was reading galleryItems/mockConversations/mockComments from
	// $lib/data/mock -- static demo data completely disconnected from
	// the real backend, so every stat here was frozen regardless of what
	// was actually happening on the platform. Wired to the same
	// admin-facing endpoints the Photos/Requests/Comments admin pages
	// already use.
	//
	// Note: photosApi.list() and commentsApi.listAll() aren't paginated
	// beyond a single page (list() caps at 100 rows; listAll() has no
	// limit param at all), so these stats are exact only up to that
	// backend-side cap -- a real analytics endpoint would be needed for
	// an exact count on a gallery with 100+ photos.
	let photos: ApiPhoto[] = [];
	let conversations: ApiConversation[] = [];
	let comments: ApiAdminComment[] = [];
	let loading = true;

	onMount(async () => {
		try {
			[photos, conversations, comments] = await Promise.all([
				photosApi.list({ limit: 100 }),
				conversationsApi.listAll(),
				commentsApi.listAll()
			]);
		} catch {
			// leave whatever loaded -- stat cards below just show 0 for
			// whichever call failed rather than blocking the whole page
		} finally {
			loading = false;
		}
	});

	$: totalViews = photos.reduce((s, i) => s + i.viewCount, 0);
	$: totalLikes = photos.reduce((s, i) => s + i.likeCount, 0);
	$: flaggedCount = photos.filter((i) => i.status === 'flagged').length;
	$: newRequests = conversations.filter((c) => c.status !== 'resolved').length;
	$: totalComments = comments.length;

	$: stats = [
		{ label: 'Published photos', value: photos.filter((i) => i.status === 'published').length, icon: Images },
		{ label: 'Total views', value: totalViews.toLocaleString(), icon: Eye },
		{ label: 'Total likes', value: totalLikes.toLocaleString(), icon: Heart },
		{ label: 'Open requests', value: newRequests, icon: Mail },
	];
</script>

<svelte:head><title>Dashboard — EddyArt Gallery Admin</title></svelte:head>

<div class="space-y-8">
	<div>
		<h1 class="text-3xl font-bold text-foreground">Overview</h1>
		<p class="text-muted-foreground mt-1">A quick look at what's happening on the platform.</p>
	</div>

	<div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
		{#each stats as stat}
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

	{#if flaggedCount > 0}
		<div class="glass elevated rounded-xl p-5 border border-destructive/30 flex items-start gap-3">
			<MessageSquareWarning class="w-5 h-5 text-destructive shrink-0 mt-0.5" />
			<div>
				<p class="font-medium text-foreground">{flaggedCount} photo{flaggedCount > 1 ? 's' : ''} flagged for review</p>
				<a href="/admin/photos" class="text-sm text-primary hover:underline">Review in Photos →</a>
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
		</ul>
	</div>
</div>
