<script lang="ts">
	import { onMount } from 'svelte';
	import { Upload, Pencil, Trash2, Eye, Heart, LoaderCircle, X, Image as ImageIcon, Sparkles } from '@lucide/svelte';
	import { videosApi, photosApi, aiApi, type ApiVideo, ApiError } from '$lib/api';
	import { PUBLIC_MAX_VIDEO_SIZE_MB, PUBLIC_MAX_VIDEO_DURATION_SECONDS } from '$env/static/public';

	// These mirror the backend's real limits (settings.MAX_VIDEO_SIZE_BYTES /
	// MAX_VIDEO_DURATION_SECONDS) purely so this page can reject an obviously
	// oversized/too-long file instantly, before spending a round trip on
	// getUploadUrl(). The backend re-checks both independently and is the
	// real enforcement boundary (ultimately backstopped by the videos
	// bucket's file_size_limit at the storage layer) -- see videos.py's
	// get_upload_url/create_video docstrings. If these two ever drift from
	// the backend's actual settings, the worst case is a slightly-too-late
	// rejection, never a wrongly-accepted upload.
	const MAX_SIZE_BYTES = Number(PUBLIC_MAX_VIDEO_SIZE_MB) * 1024 * 1024;
	const MAX_DURATION_SECONDS = Number(PUBLIC_MAX_VIDEO_DURATION_SECONDS);

	let items: ApiVideo[] = [];
	let loading = true;
	let listError = '';

	let fileInput: HTMLInputElement;
	let uploading = false;
	let uploadError = '';

	let posterInputs: Record<string, HTMLInputElement> = {};
	let uploadingPosterFor: string | null = null;

	let editing: ApiVideo | null = null;
	let editTitle = '';
	let editCategory = '';
	let editDescription = '';
	let editSpecs = '';
	let editStatus: ApiVideo['status'] = 'draft';

	// Same AI upload-assist feature as admin/photos -- see that page's
	// suggestDescription() for the full reasoning (suggestion only, never
	// auto-applied; aiUnavailable hides the button entirely rather than
	// showing an error for a deployment that never had AI_API_KEY set).
	let suggesting = false;
	let suggestError = '';
	let aiUnavailable = false;

	async function suggestDescription() {
		if (!editing) return;
		suggesting = true;
		suggestError = '';
		try {
			const suggestion = await aiApi.describeMedia(editing.objectKey, 'video');
			if (suggestion.title) editTitle = suggestion.title;
			if (suggestion.description) editDescription = suggestion.description;
			if (suggestion.specs.length > 0) editSpecs = suggestion.specs.join(', ');
		} catch (err) {
			if (err instanceof ApiError && err.status === 404) {
				aiUnavailable = true;
			} else {
				suggestError = err instanceof ApiError ? err.message : 'Could not generate a suggestion.';
			}
		} finally {
			suggesting = false;
		}
	}
	let savingEdit = false;
	let editError = '';

	let deletingId: string | null = null;
	let confirmingId: string | null = null;

	const statusStyle: Record<ApiVideo['status'], string> = {
		published: 'bg-success/10 text-success',
		draft: 'bg-muted text-muted-foreground',
		flagged: 'bg-destructive/10 text-destructive'
	};

	async function loadVideos() {
		loading = true;
		listError = '';
		try {
			items = await videosApi.list({ limit: 100 });
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not load videos.';
		} finally {
			loading = false;
		}
	}

	onMount(loadVideos);

	function triggerUpload() {
		uploadError = '';
		fileInput?.click();
	}

	/** Reads a video file's duration in the browser without uploading it
	 * anywhere -- an off-DOM <video> element + its loadedmetadata event is
	 * the standard way to do this; there's no File API that returns
	 * duration directly. Rejecting a too-long file at this point (before
	 * even requesting a presigned URL) is purely a faster/friendlier error
	 * for an honest admin -- the backend's own duration check in
	 * create_video is what actually matters, since a client could skip
	 * this page entirely and call the API directly. */
	function readVideoDuration(file: File): Promise<number> {
		return new Promise((resolve, reject) => {
			const video = document.createElement('video');
			video.preload = 'metadata';
			video.onloadedmetadata = () => {
				URL.revokeObjectURL(video.src);
				resolve(video.duration);
			};
			video.onerror = () => {
				URL.revokeObjectURL(video.src);
				reject(new Error('Could not read video file.'));
			};
			video.src = URL.createObjectURL(file);
		});
	}

	async function handleFileSelected(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		(e.target as HTMLInputElement).value = '';
		if (!file) return;

		uploadError = '';

		if (file.type !== 'video/mp4') {
			uploadError = 'Only MP4 video is supported.';
			return;
		}
		if (file.size > MAX_SIZE_BYTES) {
			uploadError = `Video exceeds the ${PUBLIC_MAX_VIDEO_SIZE_MB}MB size limit.`;
			return;
		}

		uploading = true;
		try {
			const duration = await readVideoDuration(file);
			if (duration > MAX_DURATION_SECONDS) {
				uploadError = `Video exceeds the ${MAX_DURATION_SECONDS}-second duration limit (this one is ${duration.toFixed(1)}s).`;
				return;
			}

			const { objectKey, uploadUrl } = await videosApi.getUploadUrl(file.name, file.type, file.size, duration);
			await videosApi.uploadToStorage(uploadUrl, file);

			const baseName = file.name.replace(/\.[^.]+$/, '');
			const created = await videosApi.create({
				objectKey,
				title: baseName || 'Untitled',
				category: 'Uncategorized',
				description: '',
				specs: [],
				durationSeconds: duration,
				mimeType: file.type
			});
			items = [created, ...items];
			startEdit(created);
		} catch (err) {
			uploadError = err instanceof ApiError ? err.message : 'Upload failed. Please try again.';
		} finally {
			uploading = false;
		}
	}

	function triggerPosterUpload(videoId: string) {
		posterInputs[videoId]?.click();
	}

	/** Poster is a plain still image, so it goes through photosApi's
	 * upload flow (same photos bucket, same 10MB image limit) -- not
	 * videosApi -- then the resulting objectKey is attached to the video
	 * via a normal PATCH. See Video.poster_object_key's backend docstring
	 * for why a poster lives in the photos bucket rather than the videos
	 * one. */
	async function handlePosterSelected(e: Event, video: ApiVideo) {
		const file = (e.target as HTMLInputElement).files?.[0];
		(e.target as HTMLInputElement).value = '';
		if (!file) return;

		uploadingPosterFor = video.id;
		listError = '';
		try {
			const { objectKey, uploadUrl } = await photosApi.getUploadUrl(file.name, file.type);
			await photosApi.uploadToStorage(uploadUrl, file);
			const updated = await videosApi.update(video.id, { posterObjectKey: objectKey });
			items = items.map((i) => (i.id === updated.id ? updated : i));
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not upload poster image.';
		} finally {
			uploadingPosterFor = null;
		}
	}

	async function cycleStatus(item: ApiVideo) {
		const order: ApiVideo['status'][] = ['draft', 'published', 'flagged'];
		const next = order[(order.indexOf(item.status) + 1) % order.length];
		try {
			const updated = await videosApi.update(item.id, { status: next });
			items = items.map((i) => (i.id === item.id ? updated : i));
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not update status.';
		}
	}

	function startEdit(item: ApiVideo) {
		editing = item;
		editTitle = item.title;
		editCategory = item.category;
		editDescription = item.description;
		editSpecs = item.specs.join(', ');
		editStatus = item.status;
		editError = '';
		confirmingId = null;
		suggestError = '';
	}

	function cancelEdit() {
		editing = null;
	}

	async function saveEdit() {
		if (!editing) return;
		savingEdit = true;
		editError = '';
		try {
			const updated = await videosApi.update(editing.id, {
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
		confirmingId = null;
		try {
			await videosApi.remove(id);
			items = items.filter((i) => i.id !== id);
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not delete video.';
		} finally {
			deletingId = null;
		}
	}

	function requestDelete(id: string) {
		confirmingId = id;
	}

	function cancelDelete() {
		confirmingId = null;
	}

	function formatDuration(seconds: number): string {
		const s = Math.round(seconds);
		return `0:${s.toString().padStart(2, '0')}`;
	}
</script>

<svelte:head><title>Videos — EddyArt Gallery Admin</title></svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between flex-wrap gap-4">
		<div>
			<h1 class="text-3xl font-bold text-foreground">Videos</h1>
			<p class="text-muted-foreground mt-1">
				Upload short product clips — MP4, up to {PUBLIC_MAX_VIDEO_SIZE_MB}MB, {PUBLIC_MAX_VIDEO_DURATION_SECONDS}s max.
			</p>
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
					Upload video
				{/if}
			</button>
			<input bind:this={fileInput} on:change={handleFileSelected} type="file" accept="video/mp4" class="hidden" />
			{#if uploadError}
				<p class="text-xs text-destructive max-w-xs text-right">{uploadError}</p>
			{/if}
		</div>
	</div>

	<div class="glass elevated rounded-xl overflow-hidden">
		{#if loading}
			<p class="text-center text-muted-foreground py-12">
				<LoaderCircle class="w-4 h-4 animate-spin inline-block mr-2" />
				Loading videos…
			</p>
		{:else if listError}
			<p class="text-center text-destructive py-12">{listError}</p>
		{:else}
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-border text-left text-muted-foreground">
						<th class="px-5 py-3 font-medium">Video</th>
						<th class="px-5 py-3 font-medium">Category</th>
						<th class="px-5 py-3 font-medium">Duration</th>
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
									{#if item.poster}
										<img src={item.poster} alt={item.title} class="w-12 h-12 rounded-lg object-cover shrink-0" />
									{:else}
										<!-- No poster set yet -- the raw video itself becomes the
										     thumbnail via the `poster` attribute (browsers draw the
										     first available frame when no explicit poster is given). -->
										<video src={item.video} class="w-12 h-12 rounded-lg object-cover shrink-0" muted playsinline />
									{/if}
									<div class="min-w-0">
										<span class="font-medium text-foreground block truncate max-w-[16rem]">{item.title}</span>
										<button
											on:click={() => triggerPosterUpload(item.id)}
											disabled={uploadingPosterFor === item.id}
											class="text-xs text-primary hover:underline flex items-center gap-1 disabled:opacity-50"
										>
											{#if uploadingPosterFor === item.id}
												<LoaderCircle class="w-3 h-3 animate-spin" />
											{:else}
												<ImageIcon class="w-3 h-3" />
											{/if}
											{item.poster ? 'Change poster' : 'Set poster'}
										</button>
										<input
											bind:this={posterInputs[item.id]}
											on:change={(e) => handlePosterSelected(e, item)}
											type="file"
											accept="image/jpeg,image/png,image/webp,image/gif"
											class="hidden"
										/>
									</div>
								</div>
							</td>
							<td class="px-5 py-3 text-muted-foreground">{item.category}</td>
							<td class="px-5 py-3 text-muted-foreground">{formatDuration(item.durationSeconds)}</td>
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
									{#if confirmingId === item.id}
										<button
											on:click={() => remove(item.id)}
											disabled={deletingId === item.id}
											class="px-2 py-1.5 rounded-md bg-destructive text-destructive-foreground text-xs font-medium hover:bg-destructive/90 transition-colors disabled:opacity-50 flex items-center gap-1"
											aria-label="Confirm delete {item.title}"
										>
											{#if deletingId === item.id}
												<LoaderCircle class="w-3.5 h-3.5 animate-spin" />
											{:else}
												Confirm
											{/if}
										</button>
										<button
											on:click={cancelDelete}
											disabled={deletingId === item.id}
											class="p-2 rounded-md hover:bg-muted transition-colors disabled:opacity-50"
											aria-label="Cancel delete"
										>
											<X class="w-4 h-4 text-muted-foreground" />
										</button>
									{:else}
										<button
											on:click={() => requestDelete(item.id)}
											class="p-2 rounded-md hover:bg-destructive/10 transition-colors"
											aria-label="Delete {item.title}"
										>
											<Trash2 class="w-4 h-4 text-destructive" />
										</button>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
			{#if items.length === 0}
				<p class="text-center text-muted-foreground py-12">No videos yet. Upload the first one.</p>
			{/if}
		{/if}
	</div>
</div>

{#if editing}
	<div class="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
		<div class="glass elevated rounded-2xl p-6 w-full max-w-lg space-y-4">
			<div class="flex items-center justify-between">
				<h2 class="text-lg font-semibold text-foreground">Edit video</h2>
				<button on:click={cancelEdit} class="p-1.5 rounded-md hover:bg-muted transition-colors" aria-label="Close">
					<X class="w-4 h-4" />
				</button>
			</div>

			{#if !aiUnavailable}
				<div class="flex items-center justify-between gap-2">
					<button
						on:click={suggestDescription}
						disabled={suggesting}
						class="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-primary/30 text-primary hover:bg-primary/5 transition-colors disabled:opacity-50 text-xs font-medium"
					>
						{#if suggesting}
							<LoaderCircle class="w-3.5 h-3.5 animate-spin" />
							Generating…
						{:else}
							<Sparkles class="w-3.5 h-3.5" />
							Suggest with AI
						{/if}
					</button>
					{#if suggestError}
						<p class="text-xs text-destructive">{suggestError}</p>
					{/if}
				</div>
			{/if}

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
						placeholder="e.g. 720p, 30fps"
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
