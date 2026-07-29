<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import Navbar from '$lib/components/Navbar.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { restoreSession } from '$lib/stores/auth';

	onMount(() => {
		restoreSession();
	});
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
</div>
