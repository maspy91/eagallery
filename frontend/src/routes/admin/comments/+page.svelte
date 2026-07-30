<script lang="ts">
	import { Flag, Trash2, CircleCheckBig } from '@lucide/svelte';
	import { mockComments, galleryItems } from '$lib/data/mock';
	import type { CommentNode } from '$lib/types';

	interface FlatComment extends CommentNode {
		photoTitle: string;
		photoId: string;
	}

	function flatten(): FlatComment[] {
		const out: FlatComment[] = [];
		for (const [photoId, nodes] of Object.entries(mockComments)) {
			const photo = galleryItems.find((g) => g.id === photoId);
			const walk = (list: CommentNode[]) => {
				for (const c of list) {
					out.push({ ...c, photoTitle: photo?.title ?? 'Unknown', photoId });
					if (c.replies.length) walk(c.replies);
				}
			};
			walk(nodes);
		}
		return out;
	}

	let comments = flatten();

	function toggleFlag(id: number) {
		comments = comments.map((c) => (c.id === id ? { ...c, flagged: !c.flagged } : c));
	}

	function remove(id: number) {
		comments = comments.filter((c) => c.id !== id);
	}
</script>

<svelte:head><title>Comments — EddyArt Gallery Admin</title></svelte:head>

<div class="space-y-6">
	<div>
		<h1 class="text-3xl font-bold text-foreground">Comments</h1>
		<p class="text-muted-foreground mt-1">Moderate comments across the whole gallery.</p>
	</div>

	<div class="glass elevated rounded-xl divide-y divide-border/60">
		{#each comments as comment (comment.id)}
			<div class="p-5 flex items-start gap-4">
				<div
					class="w-9 h-9 shrink-0 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-xs font-semibold text-primary-foreground"
				>
					{comment.author.substring(0, 2).toUpperCase()}
				</div>
				<div class="flex-1 min-w-0">
					<div class="flex items-center gap-2 flex-wrap text-sm">
						<span class="font-semibold text-foreground">{comment.author}</span>
						<span class="text-muted-foreground">on</span>
						<a href="/image/{comment.photoId}" class="text-primary hover:underline">{comment.photoTitle}</a>
						<span class="text-xs text-muted-foreground">· {comment.timestamp}</span>
						{#if comment.flagged}
							<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-destructive/10 text-destructive">Flagged</span>
						{/if}
					</div>
					<p class="text-sm text-foreground/90 mt-1">{comment.text}</p>
				</div>
				<div class="flex items-center gap-1 shrink-0">
					<button
						on:click={() => toggleFlag(comment.id)}
						class="p-2 rounded-md transition-colors {comment.flagged ? 'bg-destructive/10 text-destructive' : 'hover:bg-muted text-muted-foreground'}"
						aria-label="Flag comment"
					>
						{#if comment.flagged}<CircleCheckBig class="w-4 h-4" />{:else}<Flag class="w-4 h-4" />{/if}
					</button>
					<button
						on:click={() => remove(comment.id)}
						class="p-2 rounded-md hover:bg-destructive/10 transition-colors"
						aria-label="Delete comment"
					>
						<Trash2 class="w-4 h-4 text-destructive" />
					</button>
				</div>
			</div>
		{/each}
		{#if comments.length === 0}
			<p class="text-center text-muted-foreground py-12">No comments to moderate.</p>
		{/if}
	</div>
</div>
