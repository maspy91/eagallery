<script lang="ts">
	import { Eye, Heart, Play } from '@lucide/svelte';
	import type { ApiVideo } from '$lib/api';

	// Deliberately a separate component from GalleryCard.svelte rather than
	// widening GalleryItem/GalleryCard into a photo|video union -- that type
	// is also used with mock/demo data elsewhere, and a video card needs a
	// couple of genuinely different things (a play-icon overlay instead of
	// a static image, a duration badge) that don't belong bolted onto the
	// photo card's props.
	//
	// Unlike GalleryCard's handleLike (which only mutates local state and
	// never calls the API -- a pre-existing issue, not something this file
	// introduces), likes aren't toggleable from this card at all; liking
	// happens on the video's own detail page where it can call
	// videosApi.toggleLike() and reflect a real, persisted result.
	export let item: ApiVideo;

	let hovered = false;
</script>

<a
	href="/video/{item.id}"
	class="group relative overflow-hidden rounded-xl glass elevated cursor-pointer transition-smooth block"
	on:mouseenter={() => (hovered = true)}
	on:mouseleave={() => (hovered = false)}
	style="transform: {hovered ? 'translateY(-8px) scale(1.02)' : 'translateY(0) scale(1)'}"
>
	<div class="aspect-square overflow-hidden relative bg-black/20">
		{#if item.poster}
			<img
				src={item.poster}
				alt={item.title}
				class="w-full h-full object-cover transition-smooth"
				style="transform: {hovered ? 'scale(1.1)' : 'scale(1)'}"
				loading="lazy"
			/>
		{:else}
			<video src={item.video} class="w-full h-full object-cover" muted playsinline preload="metadata" />
		{/if}
		<div class="absolute inset-0 flex items-center justify-center">
			<div class="w-14 h-14 rounded-full bg-background/80 flex items-center justify-center transition-smooth" style="transform: scale({hovered ? 1.1 : 1})">
				<Play class="w-6 h-6 text-primary fill-current ml-1" />
			</div>
		</div>
		<span class="absolute top-3 right-3 px-2 py-0.5 rounded-full text-xs font-medium bg-background/80 text-foreground">
			{Math.round(item.durationSeconds)}s
		</span>
	</div>

	<div
		class="absolute inset-0 bg-gradient-to-t from-background via-background/50 to-transparent transition-smooth"
		style="opacity: {hovered ? 1 : 0.7}"
	/>

	<div class="absolute bottom-0 left-0 right-0 p-6">
		<p
			class="text-sm font-medium text-primary mb-1 transition-smooth"
			style="transform: {hovered ? 'translateY(0)' : 'translateY(10px)'}; opacity: {hovered ? 1 : 0}"
		>
			{item.category}
		</p>
		<h3 class="text-xl font-bold text-foreground mb-3">{item.title}</h3>

		<div class="flex items-center gap-4 text-sm text-muted-foreground">
			<div class="flex items-center gap-1.5">
				<Eye class="w-4 h-4" />
				<span>{item.viewCount.toLocaleString()}</span>
			</div>
			<div class="flex items-center gap-1.5">
				<Heart class="w-4 h-4 {item.liked ? 'fill-current text-primary' : ''}" />
				<span>{item.likeCount.toLocaleString()}</span>
			</div>
		</div>
	</div>
</a>
