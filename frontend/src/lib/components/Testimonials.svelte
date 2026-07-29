<script lang="ts">
	import { Star, Quote } from '@lucide/svelte';
	import { testimonials } from '$lib/data/mock';
</script>

<section class="max-w-7xl mx-auto px-4 pb-20">
	<div class="mb-12 animate-fade-in">
		<h2 class="text-4xl font-bold text-foreground mb-4">What Customers Are Saying</h2>
		<p class="text-lg text-muted-foreground">Real feedback from the people who use EddyArt Gallery</p>
	</div>

	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
		{#each testimonials as t, index (t.id)}
			<div
				class="glass elevated rounded-2xl p-6 flex flex-col animate-fade-in transition-smooth hover:-translate-y-1"
				style="animation-delay: {index * 0.08}s"
			>
				<Quote class="w-7 h-7 text-primary/40 mb-3" />

				<div class="flex items-center gap-0.5 mb-3">
					{#each Array(5) as _, i}
						<Star
							class="w-4 h-4 {i < t.rating ? 'fill-current text-primary' : 'text-muted-foreground/30'}"
						/>
					{/each}
				</div>

				<p class="text-sm text-foreground/90 leading-relaxed flex-1 mb-6">"{t.quote}"</p>

				<div class="flex items-center gap-3 pt-4 border-t border-border/40">
					<div
						class="w-10 h-10 shrink-0 rounded-full bg-linear-to-br from-primary to-secondary flex items-center justify-center text-xs font-semibold text-primary-foreground"
					>
						{t.initials}
					</div>
					<div>
						<p class="text-sm font-semibold text-foreground">{t.name}</p>
						<p class="text-xs text-muted-foreground">{t.role}</p>
					</div>
				</div>
			</div>
		{/each}
	</div>
</section>
