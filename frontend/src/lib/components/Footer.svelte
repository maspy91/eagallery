<script lang="ts">
	import { Mail } from '@lucide/svelte';

	const year = new Date().getFullYear();

	const socials = [
		{ name: 'X (Twitter)', href: 'https://twitter.com', icon: 'x' },
		{ name: 'Instagram', href: 'https://instagram.com', icon: 'instagram' },
		{ name: 'LinkedIn', href: 'https://linkedin.com', icon: 'linkedin' },
		{ name: 'GitHub', href: 'https://github.com', icon: 'github' }
	];

	const companyLinks = [
		{ label: 'Vacancies', href: '/careers' },
		{ label: 'Contact', href: '/contact' }
	];

	const exploreLinks = [
		{ label: 'Gallery', href: '/' },
		{ label: 'Sign In', href: '/login' },
		{ label: 'Create Account', href: '/register' }
	];
</script>

<footer class="border-t border-border/40 glass">
	<div class="max-w-7xl mx-auto px-4 py-16">
		<div class="grid grid-cols-1 md:grid-cols-4 gap-10">
			<!-- Brand + socials -->
			<div class="md:col-span-2">
				<a href="/" class="text-xl font-bold text-gradient inline-block mb-3">EddyArt Gallery</a>
				<p class="text-sm text-muted-foreground max-w-sm mb-6">
					A curated gallery of cutting-edge products — discover, license, and share visuals that
					bring your ideas to life.
				</p>
				<div class="flex items-center gap-2">
					{#each socials as social (social.name)}
						<a
							href={social.href}
							target="_blank"
							rel="noopener noreferrer"
							aria-label={social.name}
							class="w-9 h-9 rounded-lg glass border-border/60 hover:border-primary/50 hover:text-primary transition-smooth flex items-center justify-center"
						>
							{#if social.icon === 'x'}
								<svg viewBox="0 0 24 24" class="w-4 h-4" fill="currentColor">
									<path
										d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"
									/>
								</svg>
							{:else if social.icon === 'instagram'}
								<svg viewBox="0 0 24 24" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2">
									<rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
									<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
									<line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
								</svg>
							{:else if social.icon === 'linkedin'}
								<svg viewBox="0 0 24 24" class="w-4 h-4" fill="currentColor">
									<path
										d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.34V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.38-1.85 3.61 0 4.28 2.38 4.28 5.47zM5.34 7.43a2.07 2.07 0 1 1 0-4.13 2.07 2.07 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56z"
									/>
								</svg>
							{:else if social.icon === 'github'}
								<svg viewBox="0 0 24 24" class="w-4 h-4" fill="currentColor">
									<path
										d="M12 2C6.48 2 2 6.58 2 12.2c0 4.5 2.87 8.32 6.84 9.67.5.1.68-.22.68-.49v-1.9c-2.78.62-3.37-1.36-3.37-1.36-.46-1.2-1.11-1.52-1.11-1.52-.91-.64.07-.63.07-.63 1 .07 1.53 1.05 1.53 1.05.9 1.57 2.34 1.12 2.91.85.09-.67.35-1.12.64-1.38-2.22-.26-4.56-1.14-4.56-5.05 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.71 0 0 .84-.28 2.75 1.05a9.3 9.3 0 0 1 5 0c1.9-1.33 2.75-1.05 2.75-1.05.55 1.41.2 2.45.1 2.71.64.72 1.03 1.63 1.03 2.75 0 3.92-2.34 4.78-4.57 5.04.36.32.68.94.68 1.9v2.82c0 .27.18.6.69.49A10.02 10.02 0 0 0 22 12.2C22 6.58 17.52 2 12 2z"
									/>
								</svg>
							{/if}
						</a>
					{/each}
				</div>
			</div>

			<!-- Explore -->
			<div>
				<h3 class="text-sm font-semibold text-foreground mb-4">Explore</h3>
				<ul class="space-y-2.5">
					{#each exploreLinks as link (link.label)}
						<li>
							<a href={link.href} class="text-sm text-muted-foreground hover:text-primary transition-smooth">
								{link.label}
							</a>
						</li>
					{/each}
				</ul>
			</div>

			<!-- Company -->
			<div>
				<h3 class="text-sm font-semibold text-foreground mb-4">Company</h3>
				<ul class="space-y-2.5">
					{#each companyLinks as link (link.label)}
						<li>
							<a href={link.href} class="text-sm text-muted-foreground hover:text-primary transition-smooth">
								{link.label}
							</a>
						</li>
					{/each}
					<li>
						<a
							href="mailto:hello@eddyartgallery.app"
							class="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-primary transition-smooth"
						>
							<Mail class="w-3.5 h-3.5" />
							hello@eddyartgallery.app
						</a>
					</li>
				</ul>
			</div>
		</div>

		<div
			class="mt-12 pt-6 border-t border-border/40 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground"
		>
			<p>&copy; {year} EddyArt Gallery. All rights reserved.</p>
			<p>
				Ready to build something amazing? 
				<a
					href="mailto:mapida.ishaya@gmail.com"
					class="text-primary hover:underline"
				>
					Mail the developer.
					</a>
			</p>
		</div>
	</div>
</footer>
