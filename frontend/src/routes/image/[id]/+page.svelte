<script lang="ts">
	import { page } from '$app/stores';
	import { ArrowLeft, Eye, Heart, Share2, ExternalLink } from '@lucide/svelte';
	import { galleryItems, mockComments } from '$lib/data/mock';
	import CommentSection from '$lib/components/CommentSection.svelte';
	import type { CommentNode } from '$lib/types';

	$: id = Number($page.params.id);
	$: item = galleryItems.find((i) => i.id === id);
	$: comments = (mockComments[id] ?? []) as CommentNode[];

	let liked = false;
	let currentLikes = 0;
	let currentViews = 0;

	$: if (item) {
		currentLikes = item.likeCount;
		currentViews = item.viewCount + 1;
	}

	function toggleLike() {
		liked = !liked;
		currentLikes += liked ? 1 : -1;
	}

	async function share() {
		if (!item) return;
		const url = window.location.href;
		if (navigator.share) {
			navigator.share({ title: item.title, text: `Check out ${item.title} - ${item.category}`, url }).catch(() => {});
		} else {
			await navigator.clipboard.writeText(url);
		}
	}

	$: related = item
		? galleryItems.filter((i) => i.id !== item!.id && i.category === item!.category).slice(0, 3)
		: [];
</script>

<svelte:head>
	<title>{item ? `${item.title} — EddyArt Gallery` : 'Not found — EddyArt Gallery'}</title>
</svelte:head>

{#if !item}
	<div class="min-h-[70vh] flex items-center justify-center">
		<div class="text-center">
			<h1 class="text-4xl font-bold text-foreground mb-4">Image not found</h1>
			<a
				href="/"
				class="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
			>
				<ArrowLeft class="w-4 h-4" />
				Back to Gallery
			</a>
		</div>
	</div>
{:else}
	<main class="max-w-7xl mx-auto px-4 py-12">
		<a href="/" class="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-smooth mb-8">
			<ArrowLeft class="w-4 h-4" />
			Back to Gallery
		</a>

		<div class="grid lg:grid-cols-2 gap-12 items-start animate-fade-in">
			<div class="glass elevated rounded-2xl overflow-hidden lg:sticky lg:top-24">
				<div class="aspect-square">
					<img src={item.image} alt={item.title} class="w-full h-full object-cover" />
				</div>
			</div>

			<div class="space-y-8">
				<div class="space-y-4">
					<span class="inline-block text-sm px-3 py-1 rounded-full bg-primary/10 text-primary font-medium">
						{item.category}
					</span>
					<h1 class="text-4xl md:text-5xl font-bold text-foreground leading-tight">{item.title}</h1>
					<p class="text-xl text-muted-foreground leading-relaxed">{item.description}</p>
				</div>

				<div class="glass elevated rounded-xl p-6">
					<div class="flex items-center gap-8 flex-wrap">
						<div class="flex items-center gap-3">
							<div class="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
								<Eye class="w-5 h-5 text-primary" />
							</div>
							<div>
								<p class="text-2xl font-bold text-foreground">{currentViews.toLocaleString()}</p>
								<p class="text-sm text-muted-foreground">Views</p>
							</div>
						</div>

						<div class="flex items-center gap-3">
							<button
								on:click={toggleLike}
								class="w-12 h-12 rounded-full flex items-center justify-center transition-colors {liked
									? 'bg-primary text-primary-foreground'
									: 'bg-primary/10 text-primary hover:bg-primary/20'}"
							>
								<Heart class="w-5 h-5 {liked ? 'fill-current' : ''}" />
							</button>
							<div>
								<p class="text-2xl font-bold text-foreground">{currentLikes.toLocaleString()}</p>
								<p class="text-sm text-muted-foreground">Likes</p>
							</div>
						</div>

						<button
							on:click={share}
							class="ml-auto flex items-center gap-2 px-4 py-2.5 rounded-md border border-border hover:border-primary/50 transition-smooth text-sm font-medium"
						>
							<Share2 class="w-4 h-4" />
							Share
						</button>
					</div>
				</div>

				<div class="glass elevated rounded-xl p-6 space-y-4">
					<h2 class="text-2xl font-bold text-foreground">Key Features</h2>
					<div class="grid grid-cols-2 gap-4">
						{#each item.specs as spec}
							<div class="glass rounded-lg p-4 hover:bg-primary/5 transition-colors">
								<div class="flex items-center gap-2">
									<div class="w-2 h-2 rounded-full bg-primary" />
									<p class="text-foreground font-medium">{spec}</p>
								</div>
							</div>
						{/each}
					</div>
				</div>

				{#if related.length > 0}
					<div class="glass elevated rounded-xl p-6 space-y-4">
						<h2 class="text-2xl font-bold text-foreground">Related Products</h2>
						<div class="grid grid-cols-3 gap-4">
							{#each related as r (r.id)}
								<a
									href="/image/{r.id}"
									class="group relative aspect-square rounded-lg overflow-hidden glass hover:scale-105 transition-smooth"
								>
									<img src={r.image} alt={r.title} class="w-full h-full object-cover" />
									<div
										class="absolute inset-0 bg-linear-to-t from-background/90 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-3"
									>
										<p class="text-sm font-semibold text-foreground">{r.title}</p>
									</div>
								</a>
							{/each}
						</div>
					</div>
				{/if}

				<button
					class="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-lg font-medium"
				>
					Learn More
					<ExternalLink class="w-5 h-5" />
				</button>

				<CommentSection bind:comments />
			</div>
		</div>
	</main>
{/if}
