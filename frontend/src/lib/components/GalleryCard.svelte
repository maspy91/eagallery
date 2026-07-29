<script lang="ts">
	import { Eye, Heart, Share2 } from '@lucide/svelte';
	import type { GalleryItem } from '$lib/types';

	export let item: GalleryItem;

	let liked = false;
	let currentLikes = item.likeCount;
	let hovered = false;

	function handleLike(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		liked = !liked;
		currentLikes += liked ? 1 : -1;
	}

	async function handleShare(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		const url = `${window.location.origin}/image/${item.id}`;
		if (navigator.share) {
			navigator.share({ title: item.title, text: `Check out ${item.title} - ${item.category}`, url }).catch(() => {});
		} else {
			await navigator.clipboard.writeText(url);
		}
	}
</script>

<a
	href="/image/{item.id}"
	class="group relative overflow-hidden rounded-xl glass elevated cursor-pointer transition-smooth block"
	on:mouseenter={() => (hovered = true)}
	on:mouseleave={() => (hovered = false)}
	style="transform: {hovered ? 'translateY(-8px) scale(1.02)' : 'translateY(0) scale(1)'}"
>
	<div class="aspect-square overflow-hidden">
		<img
			src={item.image}
			alt={item.title}
			class="w-full h-full object-cover transition-smooth"
			style="transform: {hovered ? 'scale(1.1)' : 'scale(1)'}"
			loading="lazy"
		/>
	</div>

	<div
		class="absolute inset-0 bg-linear-to-t from-background via-background/50 to-transparent transition-smooth"
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
			<button
				on:click={handleLike}
				class="flex items-center gap-1.5 transition-colors {liked ? 'text-primary' : 'hover:text-primary'}"
			>
				<Heart class="w-4 h-4 {liked ? 'fill-current' : ''}" />
				<span>{currentLikes.toLocaleString()}</span>
			</button>
			<button
				on:click={handleShare}
				class="flex items-center gap-1.5 hover:text-primary transition-colors ml-auto"
				aria-label="Share"
			>
				<Share2 class="w-4 h-4" />
			</button>
		</div>
	</div>
</a>
