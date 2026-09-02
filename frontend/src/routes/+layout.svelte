<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Navbar from '$lib/components/Navbar.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import ChatWidget from '$lib/components/ChatWidget.svelte';
	import { restoreSession } from '$lib/stores/auth';

	onMount(() => {
		restoreSession();
	});

	// Admin has its own dedicated chat queue (Requests-style inbox, see
	// admin/chat/+page.svelte) -- the floating customer-facing widget
	// would be redundant (and mean an admin's own messages could
	// confusingly start a NEW customer-side chat thread) inside /admin.
	$: showWidget = !$page.url.pathname.startsWith('/admin');
</script>

<svelte:head>
	<title>EddyArt Gallery</title>
	<meta name="description" content="A curated gallery of cutting-edge products." />
</svelte:head>

<div class="min-h-screen flex flex-col">
	<Navbar />
	<main class="flex-1">
		<slot />
	</main>
	<Footer />
	{#if showWidget}
		<ChatWidget />
	{/if}
</div>
