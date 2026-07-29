<script lang="ts">
	import { theme } from '$lib/stores/theme';
	import { Sun, Moon } from '@lucide/svelte';
</script>

<button
	on:click={() => theme.toggle()}
	class="relative w-9 h-9 rounded-lg glass border-border/60 hover:border-primary/50 transition-smooth flex items-center justify-center"
	aria-label={$theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
	title={$theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
>
	{#if $theme === 'dark'}
		<Sun class="w-4 h-4 text-primary" />
	{:else}
		<Moon class="w-4 h-4 text-primary" />
	{/if}
</button>
