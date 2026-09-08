<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import GalleryCard from '$lib/components/GalleryCard.svelte';
	import GalleryVideoCard from '$lib/components/GalleryVideoCard.svelte';
	import heroBanner from '$lib/assets/hero-banner.png';
	import { Phone, MessageCircle } from '@lucide/svelte';
	import { photosApi, videosApi, type ApiPhoto, type ApiVideo } from '$lib/api';

	// Real business contact -- see Footer.svelte for the same numbers/note
	// about the social handles being a best guess from the flyer's icons.
	const phoneDisplay = '0706 430 0005';
	const phoneIntl = '2347064300005';
	const socials = [
		{ name: 'Facebook', href: 'https://facebook.com/eddyarts', icon: 'facebook' },
		{ name: 'Instagram', href: 'https://instagram.com/eddyarts', icon: 'instagram' },
		{ name: 'TikTok', href: 'https://tiktok.com/@eddyarts', icon: 'tiktok' }
	];

	const FEATURED_COUNT = 9;
	const FEATURED_VIDEO_COUNT = 3;

	// The backend picks the random 9 (ORDER BY random() LIMIT 9, filtered
	// to published-only server-side) -- fetched client-side after mount so
	// the server-rendered markup and the first client render match exactly
	// (no hydration mismatch), then the selection fades in.
	let loading = true;
	let loadError = false;
	let featuredItems: ApiPhoto[] = [];

	// Videos load independently of photos -- a slow/failed video fetch
	// shouldn't block or blank out the photo grid above it, and vice
	// versa, so this has its own loading/error state rather than sharing
	// the photo grid's.
	let videosLoading = true;
	let videosLoadError = false;
	let featuredVideos: ApiVideo[] = [];

	onMount(async () => {
		try {
			featuredItems = await photosApi.list({ status: 'published', random: FEATURED_COUNT });
		} catch {
			loadError = true;
		} finally {
			loading = false;
		}

		try {
			featuredVideos = await videosApi.list({ status: 'published', random: FEATURED_VIDEO_COUNT });
		} catch {
			videosLoadError = true;
		} finally {
			videosLoading = false;
		}
	});
</script>

<svelte:head>
	<meta
		name="description"
		content="EddyArts — World Of Creativity."
	/>
	<meta property="og:type" content="website" />
	<meta property="og:title" content="EddyArt — World Of Creativity" />
	<meta
		property="og:description"
		content="3D signage, awards, and custom creative arts. Your brand deserves to stand out — bold, clear, and unforgettable."
	/>
	<meta property="og:image" content="{$page.url.origin}/og-image.png" />
	<meta property="og:url" content={$page.url.href} />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="EddyArt — World Of Creativity" />
	<meta
		name="twitter:description"
		content="3D signage, awards, and custom creative arts. Your brand deserves to stand out — bold, clear, and unforgettable."
	/>
	<meta name="twitter:image" content="{$page.url.origin}/og-image.png" />
</svelte:head>

<section class="relative h-[70vh] flex items-center justify-center overflow-hidden">
	<div class="absolute inset-0 bg-cover bg-center" style="background-image: url({heroBanner})" />
	<div class="absolute inset-0 bg-gradient-to-b from-background/80 via-background/60 to-background" />

	<div class="relative z-10 text-center px-4 animate-fade-in">
		<h1 class="mb-6 text-5xl md:text-7xl font-bold tracking-tight text-foreground">
			Eddy<span class="text-primary">Arts</span>
		</h1>
		<p class="text-xl md:text-2xl text-muted-foreground max-w-2xl mx-auto">
			World Of Creativity...
		</p>
	</div>
</section>

<section class="max-w-7xl mx-auto px-4 py-20">
	<div class="mb-12 animate-fade-in">
		<h2 class="text-4xl font-bold text-foreground mb-4">Featured Collection</h2>
		<p class="text-lg text-muted-foreground">Explore our curated selection of cutting-edge products</p>
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

{#if !videosLoading && !videosLoadError && featuredVideos.length > 0}
	<section class="max-w-7xl mx-auto px-4 pb-20">
		<div class="mb-12 animate-fade-in">
			<h2 class="text-4xl font-bold text-foreground mb-4">Featured Videos</h2>
			<p class="text-lg text-muted-foreground">Short clips showing our products in action</p>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
			{#each featuredVideos as item, index (item.id)}
				<div class="animate-fade-in" style="animation-delay: {index * 0.1}s">
					<GalleryVideoCard {item} />
				</div>
			{/each}
		</div>
	</section>
{/if}

<section class="max-w-4xl mx-auto px-4 pb-20">
	<div class="glass elevated rounded-2xl p-8 md:p-12 text-center">
		<h2 class="text-3xl md:text-4xl font-bold text-foreground mb-3">Let's make it unforgettable</h2>
		<p class="text-muted-foreground max-w-xl mx-auto mb-8">
			Your brand deserves to stand out — bold, clear, and unforgettable. Reach out and let's talk
			about your next project.
		</p>

		<div class="flex flex-wrap items-center justify-center gap-3 mb-8">
			<a
				href="tel:+{phoneIntl}"
				class="flex items-center gap-2 px-5 py-3 rounded-lg glass border-border/60 hover:border-primary/50 transition-smooth font-medium"
			>
				<Phone class="w-4 h-4 text-primary" />
				{phoneDisplay}
			</a>
			<a
				href="https://wa.me/{phoneIntl}"
				target="_blank"
				rel="noopener noreferrer"
				class="flex items-center gap-2 px-5 py-3 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity font-medium"
			>
				<MessageCircle class="w-4 h-4" />
				Chat on WhatsApp
			</a>
		</div>

		<div class="flex items-center justify-center gap-3">
			{#each socials as social (social.name)}
				<a
					href={social.href}
					target="_blank"
					rel="noopener noreferrer"
					aria-label={social.name}
					class="w-10 h-10 rounded-full glass border-border/60 hover:border-primary/50 hover:text-primary transition-smooth flex items-center justify-center"
				>
					{#if social.icon === 'facebook'}
						<svg viewBox="0 0 24 24" class="w-4 h-4" fill="currentColor">
							<path
								d="M13.5 21v-8.06h2.7l.4-3.14h-3.1V7.86c0-.91.25-1.53 1.56-1.53h1.66V3.51C15.9 3.42 15 3.36 13.94 3.36c-2.42 0-4.08 1.48-4.08 4.19v2.35H7.15v3.14h2.71V21z"
							/>
						</svg>
					{:else if social.icon === 'instagram'}
						<svg viewBox="0 0 24 24" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2">
							<rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
							<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
							<line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
						</svg>
					{:else if social.icon === 'tiktok'}
						<svg viewBox="0 0 24 24" class="w-4 h-4" fill="currentColor">
							<path
								d="M16.5 2h-3.1v13.7c0 1.4-1.1 2.5-2.5 2.5s-2.5-1.1-2.5-2.5 1.1-2.5 2.5-2.5c.28 0 .55.05.8.13V10.2a5.6 5.6 0 0 0-.8-.06 5.6 5.6 0 1 0 5.6 5.6V8.9a7.8 7.8 0 0 0 4.4 1.36V7.16A4.6 4.6 0 0 1 16.5 2z"
							/>
						</svg>
					{/if}
				</a>
			{/each}
		</div>
	</div>
</section>
