<script lang="ts">
	import { MessagesSquare, ArrowRight } from '@lucide/svelte';
	import { currentUser } from '$lib/stores/auth';
	import { galleryItems, mockComments } from '$lib/data/mock';
	import type { CommentNode } from '$lib/types';

	interface MyThread {
		photoId: string;
		photoTitle: string;
		photoImage: string;
		rootComment: CommentNode;
		replyCount: number;
	}

	function countReplies(node: CommentNode): number {
		let n = node.replies.length;
		for (const r of node.replies) n += countReplies(r);
		return n;
	}

	$: myId = $currentUser?.id;

	$: myThreads = ((): MyThread[] => {
		const out: MyThread[] = [];
		for (const [photoId, nodes] of Object.entries(mockComments)) {
			const photo = galleryItems.find((g) => g.id === photoId);
			if (!photo) continue;
			for (const node of nodes) {
				if (node.authorId === myId) {
					out.push({
						photoId,
						photoTitle: photo.title,
						photoImage: photo.image,
						rootComment: node,
						replyCount: countReplies(node)
					});
				}
			}
		}
		return out;
	})();
</script>

<svelte:head><title>My Conversations — EddyArt Gallery</title></svelte:head>

<div class="space-y-6">
	<div>
		<h1 class="text-3xl font-bold text-foreground">My Conversations</h1>
		<p class="text-muted-foreground mt-1">Comment threads you've started or joined across the gallery.</p>
	</div>

	<div class="space-y-4">
		{#each myThreads as t (t.rootComment.id)}
			<a
				href="/image/{t.photoId}"
				class="glass elevated rounded-xl p-5 flex items-start gap-4 hover:border-primary/30 border border-transparent transition-smooth"
			>
				<img src={t.photoImage} alt={t.photoTitle} class="w-16 h-16 rounded-lg object-cover shrink-0" />
				<div class="flex-1 min-w-0">
					<div class="flex items-center gap-2 flex-wrap">
						<p class="font-semibold text-foreground">{t.photoTitle}</p>
						{#if t.replyCount > 0}
							<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
								{t.replyCount} {t.replyCount === 1 ? 'reply' : 'replies'}
							</span>
						{/if}
					</div>
					<p class="text-sm text-muted-foreground mt-1 line-clamp-2">"{t.rootComment.text}"</p>
				</div>
				<ArrowRight class="w-4 h-4 text-muted-foreground shrink-0 mt-1" />
			</a>
		{/each}

		{#if myThreads.length === 0}
			<div class="glass elevated rounded-xl text-center py-16 text-muted-foreground">
				<MessagesSquare class="w-10 h-10 mx-auto mb-3 opacity-50" />
				<p>You haven't joined any conversations yet.</p>
				<a href="/" class="text-primary text-sm hover:underline mt-2 inline-block">Browse the gallery →</a>
			</div>
		{/if}
	</div>
</div>
