<script lang="ts">
	// frontend/src/routes/admin/photos/+page.svelte
	// EDITED FILE — replaces: src/routes/admin/photos/+page.svelte (whole-file replacement)
	// Fix: the edit dialog that auto-opens right after upload had no status
	// control at all -- publishing only existed as a small, easy-to-miss
	// clickable badge back in the table, with no indication in the dialog
	// itself that it existed. Added a Status selector directly into the
	// dialog (editStatus, initialized in startEdit(), included in the
	// saveEdit() payload). The table badge still works too, for quickly
	// changing status without opening the dialog -- this is additive, not
	// a replacement.

	import { onMount } from 'svelte';
	import { Upload, Pencil, Trash2, Eye, Heart, LoaderCircle, X } from '@lucide/svelte';
	import { photosApi, type ApiPhoto, ApiError } from '$lib/api';

	let items: ApiPhoto[] = [];
	let loading = true;
	let listError = '';

	let fileInput: HTMLInputElement;
	let uploading = false;
	let uploadError = '';

	let editing: ApiPhoto | null = null;
	let editTitle = '';
	let editCategory = '';
	let editDescription = '';
	let editSpecs = '';
	let editStatus: ApiPhoto['status'] = 'draft';
	let savingEdit = false;
	let editError = '';

	let deletingId: string | null = null;

	const statusStyle: Record<ApiPhoto['status'], string> = {
		published: 'bg-success/10 text-success',
		draft: 'bg-muted text-muted-foreground',
		flagged: 'bg-destructive/10 text-destructive'
	};

	async function loadPhotos() {
		loading = true;
		listError = '';
		try {
			// Admin/staff see every status here, not just published.
			items = await photosApi.list({ limit: 100 });
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not load photos.';
		} finally {
			loading = false;
		}
	}

	onMount(loadPhotos);

	function triggerUpload() {
		uploadError = '';
		fileInput?.click();
	}

	async function handleFileSelected(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		(e.target as HTMLInputElement).value = '';
		if (!file) return;

		uploading = true;
		uploadError = '';
		try {
			const { objectKey, uploadUrl } = await photosApi.getUploadUrl(file.name, file.type);
			await photosApi.uploadToStorage(uploadUrl, file);

			const baseName = file.name.replace(/\.[^.]+$/, '');
			const created = await photosApi.create({
				objectKey,
				title: baseName || 'Untitled',
				category: 'Uncategorized',
				description: '',
				specs: []
			});
			items = [created, ...items];
			// Jump straight into editing so the title/category get filled in.
			startEdit(created);
		} catch (err) {
			uploadError = err instanceof ApiError ? err.message : 'Upload failed. Please try again.';
		} finally {
			uploading = false;
		}
	}

	async function cycleStatus(item: ApiPhoto) {
		const order: ApiPhoto['status'][] = ['draft', 'published', 'flagged'];
		const next = order[(order.indexOf(item.status) + 1) % order.length];
		try {
			const updated = await photosApi.update(item.id, { status: next });
			items = items.map((i) => (i.id === item.id ? updated : i));
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not update status.';
		}
	}

	function startEdit(item: ApiPhoto) {
		editing = item;
		editTitle = item.title;
		editCategory = item.category;
		editDescription = item.description;
		editSpecs = item.specs.join(', ');
		editStatus = item.status;
		editError = '';
	}

	function cancelEdit() {
		editing = null;
	}

	async function saveEdit() {
		if (!editing) return;
		savingEdit = true;
		editError = '';
		try {
			const updated = await photosApi.update(editing.id, {
				title: editTitle.trim(),
				category: editCategory.trim(),
				description: editDescription.trim(),
				specs: editSpecs
					.split(',')
					.map((s) => s.trim())
					.filter(Boolean),
				status: editStatus
			});
			items = items.map((i) => (i.id === updated.id ? updated : i));
			editing = null;
		} catch (err) {
			editError = err instanceof ApiError ? err.message : 'Could not save changes.';
		} finally {
			savingEdit = false;
		}
	}

	async function remove(id: string) {
		deletingId = id;
		try {
			await photosApi.remove(id);
			items = items.filter((i) => i.id !== id);
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not delete photo.';
		} finally {
			deletingId = null;
		}
	}
</script>

<svelte:head><title>Photos — EddyArt Gallery Admin</title></svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between flex-wrap gap-4">
		<div>
			<h1 class="text-3xl font-bold text-foreground">Photos</h1>
			<p class="text-muted-foreground mt-1">Upload, edit, and organize gallery items.</p>
		</div>
		<div class="flex flex-col items-end gap-1">
			<button
				on:click={triggerUpload}
				disabled={uploading}
				class="flex items-center gap-2 px-4 py-2.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50 text-sm font-medium"
			>
				{#if uploading}
					<LoaderCircle class="w-4 h-4 animate-spin" />
					Uploading...
				{:else}
					<Upload class="w-4 h-4" />
					Upload photo
				{/if}
			</button>
			<input
				bind:this={fileInput}
				on:change={handleFileSelected}
				type="file"
				accept="image/jpeg,image/png,image/webp,image/gif"
				class="hidden"
			/>
			{#if uploadError}
				<p class="text-xs text-destructive">{uploadError}</p>
			{/if}
		</div>
	</div>

	<div class="glass elevated rounded-xl overflow-hidden">
		{#if loading}
			<p class="text-center text-muted-foreground py-12">
				<LoaderCircle class="w-4 h-4 animate-spin inline-block mr-2" />
				Loading photos…
			</p>
		{:else if listError}
			<p class="text-center text-destructive py-12">{listError}</p>
		{:else}
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
									<button
										on:click={() => startEdit(item)}
										class="p-2 rounded-md hover:bg-muted transition-colors"
										aria-label="Edit {item.title}"
									>
										<Pencil class="w-4 h-4 text-muted-foreground" />
									</button>
									<button
										on:click={() => remove(item.id)}
										disabled={deletingId === item.id}
										class="p-2 rounded-md hover:bg-destructive/10 transition-colors disabled:opacity-50"
										aria-label="Delete {item.title}"
									>
										{#if deletingId === item.id}
											<LoaderCircle class="w-4 h-4 text-destructive animate-spin" />
										{:else}
											<Trash2 class="w-4 h-4 text-destructive" />
										{/if}
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
		{/if}
	</div>
</div>

{#if editing}
	<div class="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
		<div class="glass elevated rounded-2xl p-6 w-full max-w-lg space-y-4">
			<div class="flex items-center justify-between">
				<h2 class="text-lg font-semibold text-foreground">Edit photo</h2>
				<button on:click={cancelEdit} class="p-1.5 rounded-md hover:bg-muted transition-colors" aria-label="Close">
					<X class="w-4 h-4" />
				</button>
			</div>

			<div class="space-y-3">
				<div class="space-y-1.5">
					<label for="edit-title" class="text-sm font-medium text-foreground">Title</label>
					<input
						id="edit-title"
						bind:value={editTitle}
						class="w-full h-10 px-3 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					/>
				</div>
				<div class="space-y-1.5">
					<label for="edit-status" class="text-sm font-medium text-foreground">Status</label>
					<select
						id="edit-status"
						bind:value={editStatus}
						class="w-full h-10 px-3 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					>
						<option value="draft">Draft — hidden from the public gallery</option>
						<option value="published">Published — visible on the site</option>
						<option value="flagged">Flagged — hidden, needs review</option>
					</select>
				</div>
				<div class="space-y-1.5">
					<label for="edit-category" class="text-sm font-medium text-foreground">Category</label>
					<input
						id="edit-category"
						bind:value={editCategory}
						class="w-full h-10 px-3 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					/>
				</div>
				<div class="space-y-1.5">
					<label for="edit-description" class="text-sm font-medium text-foreground">Description</label>
					<textarea
						id="edit-description"
						bind:value={editDescription}
						rows="3"
						class="w-full px-3 py-2 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
					/>
				</div>
				<div class="space-y-1.5">
					<label for="edit-specs" class="text-sm font-medium text-foreground">Specs (comma-separated)</label>
					<input
						id="edit-specs"
						bind:value={editSpecs}
						placeholder="e.g. 10-Day Battery, Water Resistant"
						class="w-full h-10 px-3 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					/>
				</div>
			</div>

			{#if editError}
				<p class="text-sm text-destructive">{editError}</p>
			{/if}

			<div class="flex justify-end gap-2 pt-2">
				<button
					on:click={cancelEdit}
					class="px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors text-sm font-medium"
				>
					Cancel
				</button>
				<button
					on:click={saveEdit}
					disabled={savingEdit}
					class="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50 text-sm font-medium flex items-center gap-2"
				>
					{#if savingEdit}<LoaderCircle class="w-4 h-4 animate-spin" />{/if}
					Save changes
				</button>
			</div>
		</div>
	</div>
{/if}
