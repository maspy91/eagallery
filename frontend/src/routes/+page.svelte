<script lang="ts">
	import { onMount } from 'svelte';
	import GalleryCard from '$lib/components/GalleryCard.svelte';
	import StatsSection from '$lib/components/StatsSection.svelte';
	import Testimonials from '$lib/components/Testimonials.svelte';
	import { heroBanner } from '$lib/data/mock';
	import { photosApi, type ApiPhoto } from '$lib/api';

	const FEATURED_COUNT = 9;

	// The backend picks the random 9 (ORDER BY random() LIMIT 9, filtered
	// to published-only server-side) -- fetched client-side after mount so
	// the server-rendered markup and the first client render match exactly
	// (no hydration mismatch), then the selection fades in.
	let loading = true;
	let loadError = false;
	let featuredItems: ApiPhoto[] = [];

	onMount(async () => {
		try {
			featuredItems = await photosApi.list({ status: 'published', random: FEATURED_COUNT });
		} catch {
			loadError = true;
		} finally {
			loading = false;
		}
	});
</script>

<section class="relative h-[70vh] flex items-center justify-center overflow-hidden">
	<div class="absolute inset-0 bg-cover bg-center" style="background-image: url({heroBanner})" />
	<div class="absolute inset-0 bg-gradient-to-b from-background/80 via-background/60 to-background" />

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
		<p class="text-lg text-muted-foreground">Explore our curated selection of cutting-edge designs</p>
	</div>

	{#if loading}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
			{#each Array(FEATURED_COUNT) as _}
				<div class="aspect-square rounded-xl glass animate-pulse" />
			{/each}
		</div>
	{:else if loadError}
		<p class="text-center text-muted-foreground py-16">Couldn't load the gallery right now. Please try again shortly.</p>
	{:else if featuredItems.length === 0}
		<p class="text-center text-muted-foreground py-16">No photos published yet — check back soon.</p>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
			{#each featuredItems as item, index (item.id)}
				<div class="animate-fade-in" style="animation-delay: {index * 0.1}s">
					<GalleryCard {item} />
				</div>
			{/each}
		</div>
	{/if}
</section>

<StatsSection />

<Testimonials />
