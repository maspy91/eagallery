<script lang="ts">
	import { onMount } from 'svelte';
	import GalleryCard from '$lib/components/GalleryCard.svelte';
	import StatsSection from '$lib/components/StatsSection.svelte';
	import Testimonials from '$lib/components/Testimonials.svelte';
	import { galleryItems, heroBanner } from '$lib/data/mock';
	import type { GalleryItem } from '$lib/types';

	const FEATURED_COUNT = 9;

	// Customers only ever see published items.
	const publishedItems = galleryItems.filter((i) => i.status === 'published');

	function pickRandom(items: GalleryItem[], count: number) {
		const pool = [...items];
		for (let i = pool.length - 1; i > 0; i--) {
			const j = Math.floor(Math.random() * (i + 1));
			[pool[i], pool[j]] = [pool[j], pool[i]];
		}
		return pool.slice(0, count);
	}

	// Randomized client-side after mount so the server-rendered markup and the
	// first client render match exactly (no hydration mismatch), then the
	// random selection fades in.
	let mounted = false;
	let featuredItems: GalleryItem[] = [];

	onMount(() => {
		featuredItems = pickRandom(publishedItems, FEATURED_COUNT);
		mounted = true;
	});
</script>

<section class="relative h-[70vh] flex items-center justify-center overflow-hidden">
	<div class="absolute inset-0 bg-cover bg-center" style="background-image: url({heroBanner})" />
	<div class="absolute inset-0 bg-linear-to-b from-background/80 via-background/60 to-background" />

	<div class="relative z-10 text-center px-4 animate-fade-in">
		<h1 class="text-6xl md:text-8xl font-bold mb-6 text-gradient">EddyArt Gallery</h1>
		<p class="text-xl md:text-2xl text-muted-foreground max-w-2xl mx-auto">
			World of creativity
		</p>
	</div>
</section>

<section class="max-w-7xl mx-auto px-4 py-20">
	<div class="mb-12 animate-fade-in">
		<h2 class="text-4xl font-bold text-foreground mb-4">Featured Collection</h2>
		<p class="text-lg text-muted-foreground">Explore our curated selection of cutting-edge products</p>
	</div>

	{#if !mounted}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
			{#each Array(FEATURED_COUNT) as _}
				<div class="aspect-square rounded-xl glass animate-pulse" />
			{/each}
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
			{#each featuredItems as item, index (item.id)}
				<div class="animate-fade-in" style="animation-delay: {index * 0.1}s">
					<GalleryCard {item} />
				</div>
			{/each}
		</div>

		{#if featuredItems.length === 0}
			<p class="text-center text-muted-foreground py-16">No items to show yet.</p>
		{/if}
	{/if}
</section>

<StatsSection />

<Testimonials />
