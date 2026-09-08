<script lang="ts">
	// Shared search + date-range + CSV export bar for the five admin
	// list pages (photos, videos, comments, requests, customers). Each
	// page owns its own filter state and passes it in via bind: --
	// this component doesn't fetch anything itself, it just renders the
	// controls and tells the parent when to reload (debounced for the
	// search box, immediate for date changes) and where the current
	// export link points.

	import { Search, Download, X } from '@lucide/svelte';

	export let search = '';
	export let dateFrom = '';
	export let dateTo = '';
	export let exportHref: string;
	export let searchPlaceholder = 'Search…';
	// Called after a debounced search edit or an immediate date change --
	// the parent re-fetches its list using the (now-updated) bound values.
	export let onChange: () => void;

	let debounceTimer: ReturnType<typeof setTimeout>;
	function onSearchInput() {
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(onChange, 300);
	}

	function clearDates() {
		dateFrom = '';
		dateTo = '';
		onChange();
	}
</script>

<div class="glass elevated rounded-xl p-4 flex flex-col sm:flex-row flex-wrap gap-3 items-stretch sm:items-center">
	<div class="relative flex-1 min-w-[200px]">
		<Search class="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
		<input
			bind:value={search}
			on:input={onSearchInput}
			placeholder={searchPlaceholder}
			class="w-full h-10 pl-9 pr-3 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-sm"
		/>
	</div>

	<div class="flex items-center gap-2">
		<label class="sr-only" for="date-from">From date</label>
		<input
			id="date-from"
			type="date"
			bind:value={dateFrom}
			on:change={onChange}
			class="h-10 px-2.5 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-sm text-muted-foreground"
		/>
		<span class="text-muted-foreground text-sm">–</span>
		<label class="sr-only" for="date-to">To date</label>
		<input
			id="date-to"
			type="date"
			bind:value={dateTo}
			on:change={onChange}
			class="h-10 px-2.5 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-sm text-muted-foreground"
		/>
		{#if dateFrom || dateTo}
			<button
				type="button"
				on:click={clearDates}
				aria-label="Clear date range"
				class="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-destructive transition-colors"
			>
				<X class="w-3.5 h-3.5" />
			</button>
		{/if}
	</div>

	<!-- Page-specific extra filters (e.g. the customers page's active/
	     deactivated dropdown) that don't belong in this shared component
	     but should still sit in the same control bar. -->
	<slot />

	<a
		href={exportHref}
		target="_blank"
		rel="noopener noreferrer"
		class="flex items-center gap-2 px-4 h-10 rounded-lg glass border-border/60 hover:border-primary/50 transition-smooth text-sm font-medium whitespace-nowrap"
	>
		<Download class="w-4 h-4" />
		Export CSV
	</a>
</div>
