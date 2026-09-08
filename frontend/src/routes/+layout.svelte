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
	<title>EddyArt</title>
	<!-- Deliberately no <meta name="description"> or page-specific og:*
	     tags here -- each content page (homepage, photo/video detail)
	     sets its own. Two <meta name="description"> tags in the DOM is
	     invalid HTML and most crawlers only honor the first one, which
	     would silently be this generic fallback instead of the page's
	     actual, more specific description. Only truly page-independent
	     tags belong here. Pages without their own override (login,
	     dashboard, admin, etc.) simply have no description/og tags at
	     all -- fine, since those are already disallowed in robots.txt
	     and never meant to be shared/indexed. -->
	<meta property="og:site_name" content="EddyArt" />
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
