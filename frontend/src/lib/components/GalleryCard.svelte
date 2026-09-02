<script lang="ts">
	import { Eye, Heart, Share2 } from '@lucide/svelte';
	import { photosApi, ApiError, type ApiPhoto } from '$lib/api';
	import { currentUser, authChecked } from '$lib/stores/auth';

	// Was `item: GalleryItem` with a purely local, never-persisted like
	// toggle (flip a local boolean, +/-1 on a local counter) -- clicking
	// like here did nothing server-side; a page refresh silently reverted
	// it. GalleryCard's only real caller (src/routes/+page.svelte) already
	// passes a live ApiPhoto, so this switches to that type and calls
	// photosApi.toggleLike() for real, matching the same
	// login-gate-then-toggle pattern image/[id]/+page.svelte already uses.
	export let item: ApiPhoto;

	let hovered = false;
	let likePending = false;

	async function handleLike(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		if (likePending || !$authChecked) return;
		if ($currentUser?.role !== 'customer') {
			window.location.href = '/login';
			return;
		}
		likePending = true;
		try {
			const result = await photosApi.toggleLike(item.id);
			item = { ...item, liked: result.liked, likeCount: result.likeCount };
		} catch {
			// swallow -- same as the detail page: a failed toggle isn't
			// worth interrupting the card grid for, the button just stays
			// at its last known-good state
		} finally {
			likePending = false;
		}
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
			<button
				on:click={handleLike}
				disabled={likePending || !$authChecked}
				class="flex items-center gap-1.5 transition-colors disabled:opacity-50 {item.liked ? 'text-primary' : 'hover:text-primary'}"
			>
				<Heart class="w-4 h-4 {item.liked ? 'fill-current' : ''}" />
				<span>{item.likeCount.toLocaleString()}</span>
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
