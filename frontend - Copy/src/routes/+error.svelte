<script lang="ts">
	import { page } from '$app/stores';
	import { ArrowLeft } from '@lucide/svelte';
</script>

<div class="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
	<div class="text-center animate-fade-in">
		<p class="text-7xl font-bold text-gradient mb-4">{$page.status}</p>
		<h1 class="text-2xl font-semibold text-foreground mb-2">
			{$page.status === 404 ? 'Page not found' : 'Something went wrong'}
		</h1>
		<p class="text-muted-foreground mb-8">
			{$page.error?.message ?? "The page you're looking for doesn't exist."}
		</p>
		<a
			href="/"
			class="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
		>
			<ArrowLeft class="w-4 h-4" />
			Back to Gallery
		</a>
	</div>
</div>
