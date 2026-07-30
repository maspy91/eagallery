<script lang="ts">
	import { Briefcase, Users, Activity } from '@lucide/svelte';
	import { siteStats } from '$lib/data/mock';

	const stats = [
		{
			icon: Briefcase,
			value: siteStats.jobsCompleted,
			label: 'Jobs Completed'
		},
		{
			icon: Users,
			value: siteStats.customers,
			label: 'Happy Customers'
		},
		{
			icon: Activity,
			value: siteStats.activeUsers,
			label: 'Active Users'
		}
	];

	function formatValue(value: number) {
		return value >= 1000 ? `${(value / 1000).toFixed(1).replace(/\.0$/, '')}k+` : `${value}+`;
	}
</script>

<section class="max-w-7xl mx-auto px-4 pb-20">
	<div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
		{#each stats as stat, index (stat.label)}
			<div
				class="glass elevated rounded-2xl p-8 text-center animate-fade-in transition-smooth hover:-translate-y-1"
				style="animation-delay: {index * 0.1}s"
			>
				<div
					class="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary mb-4"
				>
					<svelte:component this={stat.icon} class="w-6 h-6 text-primary-foreground" />
				</div>
				<p class="text-4xl font-bold text-gradient mb-1">{formatValue(stat.value)}</p>
				<p class="text-sm text-muted-foreground">{stat.label}</p>
			</div>
		{/each}
	</div>
</section>
