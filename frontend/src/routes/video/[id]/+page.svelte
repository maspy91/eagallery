<script lang="ts">
	import { page } from '$app/stores';
	import { ArrowLeft, Eye, Heart, Share2, ExternalLink, LoaderCircle } from '@lucide/svelte';
	import CommentSection from '$lib/components/CommentSection.svelte';
	import { currentUser, authChecked } from '$lib/stores/auth';
	import { videosApi, type ApiVideo } from '$lib/api';

	// Mirrors src/routes/image/[id]/+page.svelte closely -- see that file
	// for the reasoning behind the `$: if (id) load(id)` pattern and the
	// share()/toggleLike() logic, which is identical here. The two
	// genuinely different things: a <video> element instead of <img>
	// (with the poster attribute, so a still image shows before playback
	// starts), and no "related items" carousel -- videosApi.list()
	// filtered by category would work the same way photosApi's does, but
	// the catalog is expected to stay small enough for a while that a
	// related-videos rail isn't worth the added surface yet.

	$: id = $page.params.id;

	let loading = true;
	let notFound = false;
	let item: ApiVideo | null = null;
	let likePending = false;

	async function load(videoId: string) {
		loading = true;
		notFound = false;
		item = null;
		try {
			item = await videosApi.get(videoId);
		} catch {
			notFound = true;
		} finally {
			loading = false;
		}
	}

	$: if (id) load(id);

	async function toggleLike() {
		if (!item || likePending || !$authChecked) return;
		if ($currentUser?.role !== 'customer') {
			window.location.href = '/login';
			return;
		}
		likePending = true;
		try {
			const result = await videosApi.toggleLike(item.id);
			item = { ...item, liked: result.liked, likeCount: result.likeCount };
		} catch {
			// swallow -- a failed like toggle isn't worth interrupting the page for
		} finally {
			likePending = false;
		}
	}

	async function share() {
		if (!item) return;
		const url = window.location.href;
		if (navigator.share) {
			navigator.share({ title: item.title, text: `Check out ${item.title} - ${item.category}`, url }).catch(() => {});
		} else {
			await navigator.clipboard.writeText(url);
		}
	}
</script>

<svelte:head>
	<title>{item ? `${item.title} — EddyArt Gallery` : 'Not found — EddyArt Gallery'}</title>
</svelte:head>

{#if loading}
	<div class="min-h-[70vh] flex items-center justify-center">
		<LoaderCircle class="w-8 h-8 text-primary animate-spin" />
	</div>
{:else if notFound || !item}
	<div class="min-h-[70vh] flex items-center justify-center">
		<div class="text-center">
			<h1 class="text-4xl font-bold text-foreground mb-4">Video not found</h1>
			<a
				href="/"
				class="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
			>
				<ArrowLeft class="w-4 h-4" />
				Back to Gallery
			</a>
		</div>
	</div>
{:else}
	<main class="max-w-7xl mx-auto px-4 py-12">
		<a href="/" class="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-smooth mb-8">
			<ArrowLeft class="w-4 h-4" />
			Back to Gallery
		</a>

		<div class="grid lg:grid-cols-2 gap-12 items-start animate-fade-in">
			<div class="glass elevated rounded-2xl overflow-hidden lg:sticky lg:top-24">
				<div class="aspect-square bg-black">
					<!-- svelte-ignore a11y-media-has-caption -->
					<video
						src={item.video}
						poster={item.poster ?? undefined}
						controls
						playsinline
						class="w-full h-full object-contain"
					/>
				</div>
			</div>

			<div class="space-y-8">
				<div class="space-y-4">
					<div class="flex items-center gap-2 flex-wrap">
						<span class="inline-block text-sm px-3 py-1 rounded-full bg-primary/10 text-primary font-medium">
							{item.category}
						</span>
						<span class="inline-block text-sm px-3 py-1 rounded-full bg-muted text-muted-foreground font-medium">
							{Math.round(item.durationSeconds)}s
						</span>
					</div>
					<h1 class="text-4xl md:text-5xl font-bold text-foreground leading-tight">{item.title}</h1>
					<p class="text-xl text-muted-foreground leading-relaxed">{item.description}</p>
				</div>

				<div class="glass elevated rounded-xl p-6">
					<div class="flex items-center gap-8 flex-wrap">
						<div class="flex items-center gap-3">
							<div class="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
								<Eye class="w-5 h-5 text-primary" />
							</div>
							<div>
								<p class="text-2xl font-bold text-foreground">{item.viewCount.toLocaleString()}</p>
								<p class="text-sm text-muted-foreground">Views</p>
							</div>
						</div>

						<div class="flex items-center gap-3">
							<button
								on:click={toggleLike}
								disabled={likePending || !$authChecked}
								class="w-12 h-12 rounded-full flex items-center justify-center transition-colors disabled:opacity-50 {item.liked
									? 'bg-primary text-primary-foreground'
									: 'bg-primary/10 text-primary hover:bg-primary/20'}"
								aria-label={item.liked ? 'Unlike' : 'Like'}
							>
								<Heart class="w-5 h-5 {item.liked ? 'fill-current' : ''}" />
							</button>
							<div>
								<p class="text-2xl font-bold text-foreground">{item.likeCount.toLocaleString()}</p>
								<p class="text-sm text-muted-foreground">Likes</p>
							</div>
						</div>

						<button
							on:click={share}
							class="ml-auto flex items-center gap-2 px-4 py-2.5 rounded-md border border-border hover:border-primary/50 transition-smooth text-sm font-medium"
						>
							<Share2 class="w-4 h-4" />
							Share
						</button>
					</div>
				</div>

				{#if item.specs.length > 0}
					<div class="glass elevated rounded-xl p-6 space-y-4">
						<h2 class="text-2xl font-bold text-foreground">Key Features</h2>
						<div class="grid grid-cols-2 gap-4">
							{#each item.specs as spec}
								<div class="glass rounded-lg p-4 hover:bg-primary/5 transition-colors">
									<div class="flex items-center gap-2">
										<div class="w-2 h-2 rounded-full bg-primary" />
										<p class="text-foreground font-medium">{spec}</p>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<button
					class="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-lg font-medium"
				>
					Learn More
					<ExternalLink class="w-5 h-5" />
				</button>

				<CommentSection videoId={item.id} />
			</div>
		</div>
	</main>
{/if}
