<script lang="ts">
	import { Reply, Send } from '@lucide/svelte';
	import type { CommentNode } from '$lib/types';
	import { createEventDispatcher } from 'svelte';

	export let comment: CommentNode;
	export let depth = 0;

	const dispatch = createEventDispatcher<{ reply: { commentId: string; text: string } }>();

	let showReplyForm = false;
	let replyText = '';
	let submitting = false;
	let error = '';

	const maxDepth = 3;
	$: canReply = depth < maxDepth;

	function submitReply() {
		const trimmed = replyText.trim();
		if (trimmed.length === 0) {
			error = 'Reply cannot be empty';
			return;
		}
		if (trimmed.length > 500) {
			error = 'Reply must be less than 500 characters';
			return;
		}
		error = '';
		submitting = true;
		setTimeout(() => {
			dispatch('reply', { commentId: comment.id, text: trimmed });
			replyText = '';
			showReplyForm = false;
			submitting = false;
		}, 300);
	}

	function forwardReply(e: CustomEvent<{ commentId: string; text: string }>) {
		dispatch('reply', e.detail);
	}
</script>

<div class={depth > 0 ? 'ml-8 mt-4' : ''}>
	<div class="glass rounded-xl p-4 space-y-3">
		<div class="flex items-start gap-3">
			<div
				class="w-10 h-10 shrink-0 rounded-full ring-2 ring-primary/20 bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-primary-foreground font-semibold text-sm"
			>
				{comment.author.substring(0, 2).toUpperCase()}
			</div>

			<div class="flex-1 space-y-1 min-w-0">
				<div class="flex items-center gap-2">
					<p class="font-semibold text-foreground">{comment.author}</p>
					<span class="text-xs text-muted-foreground">{comment.timestamp}</span>
				</div>
				<p class="text-sm text-foreground/90 leading-relaxed break-words">{comment.text}</p>

				{#if canReply}
					<button
						on:click={() => (showReplyForm = !showReplyForm)}
						class="flex items-center gap-1.5 h-8 text-xs -ml-2 px-2 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/5 transition-colors"
					>
						<Reply class="w-3 h-3" />
						Reply
					</button>
				{/if}
			</div>
		</div>

		{#if showReplyForm}
			<div class="ml-0 sm:ml-13 space-y-2 animate-fade-in">
				<textarea
					bind:value={replyText}
					placeholder="Write a reply..."
					maxlength="500"
					class="w-full min-h-[80px] resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
				/>
				{#if error}
					<p class="text-xs text-destructive">{error}</p>
				{/if}
				<div class="flex justify-between items-center">
					<span class="text-xs text-muted-foreground">{replyText.length}/500</span>
					<div class="flex gap-2">
						<button
							on:click={() => {
								showReplyForm = false;
								replyText = '';
								error = '';
							}}
							class="px-3 py-1.5 text-sm rounded-md text-muted-foreground hover:bg-muted transition-colors"
						>
							Cancel
						</button>
						<button
							on:click={submitReply}
							disabled={!replyText.trim() || submitting}
							class="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity"
						>
							<Send class="w-3 h-3" />
							Reply
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>

	{#if comment.replies.length > 0}
		<div class="mt-2">
			{#each comment.replies as reply (reply.id)}
				<svelte:self comment={reply} depth={depth + 1} on:reply={forwardReply} />
			{/each}
		</div>
	{/if}
</div>
