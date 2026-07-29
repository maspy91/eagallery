<script lang="ts">
	import { Upload, Pencil, Trash2, Eye, Heart } from '@lucide/svelte';
	import { galleryItems } from '$lib/data/mock';
	import type { GalleryItem } from '$lib/types';

	// Local copy so the table is interactive in Phase 1. Phase 2 swaps
	// these handlers for calls to POST/PATCH/DELETE /api/photos.
	let items: GalleryItem[] = [...galleryItems];

	const statusStyle: Record<GalleryItem['status'], string> = {
		published: 'bg-success/10 text-success',
		draft: 'bg-muted text-muted-foreground',
		flagged: 'bg-destructive/10 text-destructive'
	};

	function cycleStatus(item: GalleryItem) {
		const order: GalleryItem['status'][] = ['draft', 'published', 'flagged'];
		const next = order[(order.indexOf(item.status) + 1) % order.length];
		items = items.map((i) => (i.id === item.id ? { ...i, status: next } : i));
	}

	function remove(id: number) {
		items = items.filter((i) => i.id !== id);
	}
</script>

<svelte:head><title>Photos — EddyArt Gallery Admin</title></svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between flex-wrap gap-4">
		<div>
			<h1 class="text-3xl font-bold text-foreground">Photos</h1>
			<p class="text-muted-foreground mt-1">Upload, edit, and organize gallery items.</p>
		</div>
		<button
			class="flex items-center gap-2 px-4 py-2.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm font-medium"
		>
			<Upload class="w-4 h-4" />
			Upload photo
		</button>
	</div>

	<div class="glass elevated rounded-xl overflow-hidden">
		<table class="w-full text-sm">
			<thead>
				<tr class="border-b border-border text-left text-muted-foreground">
					<th class="px-5 py-3 font-medium">Photo</th>
					<th class="px-5 py-3 font-medium">Category</th>
					<th class="px-5 py-3 font-medium">Stats</th>
					<th class="px-5 py-3 font-medium">Status</th>
					<th class="px-5 py-3 font-medium text-right">Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each items as item (item.id)}
					<tr class="border-b border-border/60 last:border-0 hover:bg-muted/40 transition-colors">
						<td class="px-5 py-3">
							<div class="flex items-center gap-3">
								<img src={item.image} alt={item.title} class="w-12 h-12 rounded-lg object-cover" />
								<span class="font-medium text-foreground">{item.title}</span>
							</div>
						</td>
						<td class="px-5 py-3 text-muted-foreground">{item.category}</td>
						<td class="px-5 py-3 text-muted-foreground">
							<div class="flex items-center gap-3">
								<span class="flex items-center gap-1"><Eye class="w-3.5 h-3.5" />{item.viewCount.toLocaleString()}</span>
								<span class="flex items-center gap-1"><Heart class="w-3.5 h-3.5" />{item.likeCount.toLocaleString()}</span>
							</div>
						</td>
						<td class="px-5 py-3">
							<button
								on:click={() => cycleStatus(item)}
								class="px-2.5 py-1 rounded-full text-xs font-medium capitalize {statusStyle[item.status]}"
								title="Click to change status"
							>
								{item.status}
							</button>
						</td>
						<td class="px-5 py-3">
							<div class="flex items-center justify-end gap-1">
								<button class="p-2 rounded-md hover:bg-muted transition-colors" aria-label="Edit {item.title}">
									<Pencil class="w-4 h-4 text-muted-foreground" />
								</button>
								<button
									on:click={() => remove(item.id)}
									class="p-2 rounded-md hover:bg-destructive/10 transition-colors"
									aria-label="Delete {item.title}"
								>
									<Trash2 class="w-4 h-4 text-destructive" />
								</button>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
		{#if items.length === 0}
			<p class="text-center text-muted-foreground py-12">No photos yet. Upload the first one.</p>
		{/if}
	</div>
</div>
