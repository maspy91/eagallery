<script lang="ts">
	// frontend/src/routes/admin/comments/+page.svelte
	// EDITED FILE — replaces: src/routes/admin/comments/+page.svelte (whole-file replacement)
	// Replaced the mock-data flatten() of mockComments/galleryItems with a
	// real fetch from GET /api/comments (comments:moderate only, already
	// flat/cross-photo server-side -- no client-side tree-walking needed
	// anymore). Flag/delete now call the real moderation endpoints.

	import { onMount } from 'svelte';
	import { Flag, Trash2, CircleCheckBig, LoaderCircle } from '@lucide/svelte';
	import { commentsApi, ApiError, type ApiAdminComment } from '$lib/api';

	let comments: ApiAdminComment[] = [];
	let loading = true;
	let loadError = '';
	let pendingId: string | null = null;

	async function load() {
		loading = true;
		loadError = '';
		try {
			comments = await commentsApi.listAll();
		} catch (err) {
			loadError = err instanceof ApiError ? err.message : 'Could not load comments.';
		} finally {
			loading = false;
		}
	}

	onMount(load);

	async function toggleFlag(comment: ApiAdminComment) {
		pendingId = comment.id;
		try {
			await commentsApi.setFlagged(comment.id, !comment.flagged);
			comments = comments.map((c) => (c.id === comment.id ? { ...c, flagged: !c.flagged } : c));
		} catch (err) {
			loadError = err instanceof ApiError ? err.message : 'Could not update comment.';
		} finally {
			pendingId = null;
		}
	}

	async function remove(id: string) {
		pendingId = id;
		try {
			await commentsApi.remove(id);
			comments = comments.filter((c) => c.id !== id);
		} catch (err) {
			loadError = err instanceof ApiError ? err.message : 'Could not delete comment.';
		} finally {
			pendingId = null;
		}
	}
</script>

<svelte:head><title>Comments — EddyArt Gallery Admin</title></svelte:head>

<div class="space-y-6">
	<div>
		<h1 class="text-3xl font-bold text-foreground">Comments</h1>
		<p class="text-muted-foreground mt-1">Moderate comments across the whole gallery.</p>
	</div>

	<div class="glass elevated rounded-xl divide-y divide-border/60">
		{#if loading}
			<p class="text-center text-muted-foreground py-12">
				<LoaderCircle class="w-4 h-4 animate-spin inline-block mr-2" />
				Loading comments…
			</p>
		{:else if loadError}
			<p class="text-center text-destructive py-12">{loadError}</p>
		{:else}
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
							<span class="text-xs text-muted-foreground">· {new Date(comment.timestamp).toLocaleString()}</span>
							{#if comment.flagged}
								<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-destructive/10 text-destructive">Flagged</span>
							{/if}
						</div>
						<p class="text-sm text-foreground/90 mt-1">{comment.text}</p>
					</div>
					<div class="flex items-center gap-1 shrink-0">
						<button
							on:click={() => toggleFlag(comment)}
							disabled={pendingId === comment.id}
							class="p-2 rounded-md transition-colors disabled:opacity-50 {comment.flagged
								? 'bg-destructive/10 text-destructive'
								: 'hover:bg-muted text-muted-foreground'}"
							aria-label="Flag comment"
						>
							{#if comment.flagged}<CircleCheckBig class="w-4 h-4" />{:else}<Flag class="w-4 h-4" />{/if}
						</button>
						<button
							on:click={() => remove(comment.id)}
							disabled={pendingId === comment.id}
							class="p-2 rounded-md hover:bg-destructive/10 transition-colors disabled:opacity-50"
							aria-label="Delete comment"
						>
							{#if pendingId === comment.id}
								<LoaderCircle class="w-4 h-4 text-destructive animate-spin" />
							{:else}
								<Trash2 class="w-4 h-4 text-destructive" />
							{/if}
						</button>
					</div>
				</div>
			{:else}
				<p class="text-center text-muted-foreground py-12">No comments to moderate.</p>
			{/each}
		{/if}
	</div>
</div>
