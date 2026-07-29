<script lang="ts">
	import { MessageCircle, Send } from '@lucide/svelte';
	import type { CommentNode } from '$lib/types';
	import CommentItem from './CommentItem.svelte';
	import { currentUser } from '$lib/stores/auth';

	export let comments: CommentNode[] = [];

	let newComment = '';
	let submitting = false;
	let error = '';
	let nextId = 1000;

	$: authorName = $currentUser?.role === 'customer' ? $currentUser.name : 'Anonymous User';
	$: authorId = $currentUser?.role === 'customer' ? $currentUser.id : undefined;

	function submitComment() {
		const trimmed = newComment.trim();
		if (trimmed.length === 0) {
			error = 'Comment cannot be empty';
			return;
		}
		if (trimmed.length > 500) {
			error = 'Comment must be less than 500 characters';
			return;
		}
		error = '';
		submitting = true;
		setTimeout(() => {
			comments = [
				{ id: nextId++, author: authorName, authorId, text: trimmed, timestamp: 'Just now', replies: [] },
				...comments
			];
			newComment = '';
			submitting = false;
		}, 300);
	}

	function addReply(commentId: number, text: string) {
		function walk(nodes: CommentNode[]): CommentNode[] {
			return nodes.map((c) => {
				if (c.id === commentId) {
					return {
						...c,
						replies: [
							...c.replies,
							{ id: nextId++, author: authorName, authorId, text, timestamp: 'Just now', replies: [] }
						]
					};
				}
				if (c.replies.length > 0) return { ...c, replies: walk(c.replies) };
				return c;
			});
		}
		comments = walk(comments);
	}

	function handleReply(e: CustomEvent<{ commentId: number; text: string }>) {
		addReply(e.detail.commentId, e.detail.text);
	}
</script>

<div class="glass elevated rounded-xl p-6 space-y-6">
	<div class="flex items-center gap-2">
		<MessageCircle class="w-5 h-5 text-primary" />
		<h2 class="text-2xl font-bold text-foreground">Comments ({comments.length})</h2>
	</div>

	<div class="space-y-3">
		{#if !$currentUser}
			<p class="text-xs text-muted-foreground">
				Posting as a guest. <a href="/login" class="text-primary hover:underline">Sign in</a> to get notified when someone replies.
			</p>
		{/if}
		<textarea
			bind:value={newComment}
			placeholder="Share your thoughts..."
			maxlength="500"
			class="w-full min-h-[100px] resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
		/>
		{#if error}
			<p class="text-xs text-destructive">{error}</p>
		{/if}
		<div class="flex justify-between items-center">
			<span class="text-xs text-muted-foreground">{newComment.length}/500</span>
			<button
				on:click={submitComment}
				disabled={!newComment.trim() || submitting}
				class="flex items-center gap-2 px-4 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity"
			>
				<Send class="w-4 h-4" />
				Post Comment
			</button>
		</div>
	</div>

	<div class="space-y-4">
		{#if comments.length === 0}
			<div class="text-center py-8 text-muted-foreground">
				<MessageCircle class="w-12 h-12 mx-auto mb-3 opacity-50" />
				<p>No comments yet. Be the first to share your thoughts!</p>
			</div>
		{:else}
			{#each comments as comment (comment.id)}
				<CommentItem {comment} on:reply={handleReply} />
			{/each}
		{/if}
	</div>
</div>
