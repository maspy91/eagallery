<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import GalleryVideoCard from '$lib/components/GalleryVideoCard.svelte';
	import { Search } from '@lucide/svelte';
	import { videosApi, type ApiVideo } from '$lib/api';

	// Same 100-row cap as the public photo/video list endpoints generally
	// (see sitemap.xml/+server.ts's KNOWN LIMIT note) -- no real pagination
	// UI exists anywhere else in this app either, so this matches that
	// existing ceiling rather than inventing a paginated experience nothing
	// else here has.
	const LIST_LIMIT = 100;

	let loading = true;
	let loadError = false;
	let videos: ApiVideo[] = [];

	let searchInput = '';
	let searchTimer: ReturnType<typeof setTimeout>;

	async function fetchVideos(q?: string) {
		loading = true;
		loadError = false;
		try {
			videos = await videosApi.list({ status: 'published', limit: LIST_LIMIT, ...(q ? { q } : {}) });
		} catch {
			loadError = true;
		} finally {
			loading = false;
		}
	}

	// Debounced so every keystroke doesn't fire a request -- same idea as
	// the admin list controls' search box, just simpler since this page
	// has no other filters to coordinate with.
	function handleSearchInput() {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => fetchVideos(searchInput.trim() || undefined), 350);
	}

	onMount(() => {
		fetchVideos();
	});
</script>

<svelte:head>
	<title>Videos — EddyArts</title>
	<meta
		name="description"
		content="Browse every published EddyArts product video — 3D signage, awards, and custom creative work in motion."
	/>
	<meta property="og:type" content="website" />
	<meta property="og:title" content="Videos — EddyArts" />
	<meta
		property="og:description"
		content="Browse every published EddyArts product video — 3D signage, awards, and custom creative work in motion."
	/>
	<meta property="og:image" content="{$page.url.origin}/og-image.png" />
	<meta property="og:url" content={$page.url.href} />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Videos — EddyArts" />
	<meta
		name="twitter:description"
		content="Browse every published EddyArts product video — 3D signage, awards, and custom creative work in motion."
	/>
	<meta name="twitter:image" content="{$page.url.origin}/og-image.png" />
</svelte:head>

<section class="max-w-7xl mx-auto px-4 py-16">
	<div class="mb-10 animate-fade-in">
		<h1 class="text-4xl md:text-5xl font-bold text-foreground mb-4">Videos</h1>
		<p class="text-lg text-muted-foreground">Short clips showing our products in action</p>
	</div>

	<div class="relative max-w-md mb-12">
		<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
		<input
			type="search"
			bind:value={searchInput}
			on:input={handleSearchInput}
			placeholder="Search videos by title or category…"
			class="w-full pl-10 pr-4 py-2.5 rounded-lg glass border-border/60 focus:border-primary/50 outline-none transition-smooth text-sm"
		/>
	</div>

	{#if loading}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
			{#each Array(6) as _}
				<div class="aspect-square rounded-xl glass animate-pulse" />
			{/each}
		</div>
	{:else if loadError}
		<p class="text-center text-muted-foreground py-16">Couldn't load videos right now. Please try again shortly.</p>
	{:else if videos.length === 0}
		<p class="text-center text-muted-foreground py-16">
			{searchInput ? `No videos match "${searchInput}".` : 'No videos published yet — check back soon.'}
		</p>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
			{#each videos as item, index (item.id)}
				<div class="animate-fade-in" style="animation-delay: {Math.min(index, 9) * 0.1}s">
					<GalleryVideoCard {item} />
				</div>
			{/each}
		</div>
	{/if}
</section>
