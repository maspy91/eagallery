<script lang="ts">
	import { MessageCircle, Send, LoaderCircle } from '@lucide/svelte';
	import type { CommentNode } from '$lib/types';
	import CommentItem from './CommentItem.svelte';
	import { currentUser } from '$lib/stores/auth';
	import { commentsApi, ApiError, type ApiComment } from '$lib/api';

	export let photoId: string;

	// ApiComment.authorId is string | null (mirrors the backend's Optional
	// column); CommentNode.authorId is string | undefined (the app-wide
	// convention -- see types.ts, and how CommentItem compares it against
	// currentUser). Normalize at this boundary rather than changing
	// CommentNode, which is also used with mock/demo data elsewhere.
	function toCommentNode(c: ApiComment): CommentNode {
		return {
			id: c.id,
			author: c.author,
			authorId: c.authorId ?? undefined,
			text: c.text,
			timestamp: c.timestamp,
			flagged: c.flagged,
			replies: c.replies.map(toCommentNode)
		};
	}

	let comments: CommentNode[] = [];
	let loading = true;
	let loadError = '';

	let newComment = '';
	let submitting = false;
	let error = '';

	async function load(id: string) {
		loading = true;
		loadError = '';
		try {
			comments = (await commentsApi.list(id)).map(toCommentNode);
		} catch (err) {
			loadError = err instanceof ApiError ? err.message : 'Could not load comments.';
		} finally {
			loading = false;
		}
	}

	$: load(photoId);

	function countAll(nodes: CommentNode[]): number {
		return nodes.reduce((sum, c) => sum + 1 + countAll(c.replies), 0);
	}
	$: totalCount = countAll(comments);

	async function submitComment() {
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
		try {
			const created = await commentsApi.create(photoId, trimmed);
			comments = [toCommentNode(created), ...comments];
			newComment = '';
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not post your comment. Please try again.';
		} finally {
			submitting = false;
		}
	}

	async function addReply(commentId: string, text: string) {
		try {
			const reply = await commentsApi.create(photoId, text, commentId);
			const replyNode = toCommentNode(reply);
			function walk(nodes: CommentNode[]): CommentNode[] {
				return nodes.map((c) => {
					if (c.id === commentId) return { ...c, replies: [...c.replies, replyNode] };
					if (c.replies.length > 0) return { ...c, replies: walk(c.replies) };
					return c;
				});
			}
			comments = walk(comments);
		} catch {
			// swallow -- the reply form in CommentItem simply stays open so
			// the person can see their text is still there and retry
		}
	}

	function handleReply(e: CustomEvent<{ commentId: string; text: string }>) {
		addReply(e.detail.commentId, e.detail.text);
	}
</script>

<div class="glass elevated rounded-xl p-6 space-y-6">
	<div class="flex items-center gap-2">
		<MessageCircle class="w-5 h-5 text-primary" />
		<h2 class="text-2xl font-bold text-foreground">Comments ({totalCount})</h2>
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
				{#if submitting}
					<LoaderCircle class="w-4 h-4 animate-spin" />
				{:else}
					<Send class="w-4 h-4" />
				{/if}
				Post Comment
			</button>
		</div>
	</div>

	<div class="space-y-4">
		{#if loading}
			<div class="text-center py-8 text-muted-foreground">
				<LoaderCircle class="w-6 h-6 mx-auto animate-spin" />
			</div>
		{:else if loadError}
			<p class="text-center text-sm text-destructive py-4">{loadError}</p>
		{:else if comments.length === 0}
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
