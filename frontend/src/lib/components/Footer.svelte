<script lang="ts">
	import { Mail, Phone, MessageCircle } from '@lucide/svelte';

	const year = new Date().getFullYear();

	// Real business contact, taken from the current EddyArts flyer/contact
	// card -- both the call and WhatsApp buttons go to the same number.
	const phoneDisplay = '0706 430 0005';
	const phoneIntl = '2347064300005';

	// NOTE: exact @handles weren't visible on the flyer (icons only, no
	// usernames) -- these use the obvious "eddyarts" handle as the best
	// guess. Worth confirming/correcting with the real profile URLs.
	const socials = [
		{ name: 'Facebook', href: 'https://facebook.com/eddyarts', icon: 'facebook' },
		{ name: 'Instagram', href: 'https://instagram.com/eddyarts', icon: 'instagram' },
		{ name: 'TikTok', href: 'https://tiktok.com/@eddyarts', icon: 'tiktok' }
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
			<!-- Brand + contact + socials -->
			<div class="md:col-span-2">
				<a href="/" class="inline-block mb-4" aria-label="EddyArts — World Of Creativity">
					<span class="text-2xl font-bold tracking-tight text-foreground">
						Eddy<span class="text-primary">Arts</span>
					</span>
				</a>
				<p class="text-sm text-muted-foreground max-w-sm mb-6">
					EddyArt — 3D signage, awards, and general creative arts. Your brand deserves to stand
					out: bold, clear, and unforgettable.
				</p>

				<!-- Call / WhatsApp -->
				<div class="flex flex-wrap items-center gap-2 mb-5">
					<a
						href="tel:+{phoneIntl}"
						class="flex items-center gap-2 px-3 py-2 rounded-lg glass border-border/60 hover:border-primary/50 transition-smooth text-sm font-medium"
					>
						<Phone class="w-3.5 h-3.5 text-primary" />
						{phoneDisplay}
					</a>
					<a
						href="https://wa.me/{phoneIntl}"
						target="_blank"
						rel="noopener noreferrer"
						class="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm font-medium"
					>
						<MessageCircle class="w-3.5 h-3.5" />
						WhatsApp us
					</a>
				</div>

				<div class="flex items-center gap-2">
					{#each socials as social (social.name)}
						<a
							href={social.href}
							target="_blank"
							rel="noopener noreferrer"
							aria-label={social.name}
							class="w-9 h-9 rounded-lg glass border-border/60 hover:border-primary/50 hover:text-primary transition-smooth flex items-center justify-center"
						>
							{#if social.icon === 'facebook'}
								<svg viewBox="0 0 24 24" class="w-4 h-4" fill="currentColor">
									<path
										d="M13.5 21v-8.06h2.7l.4-3.14h-3.1V7.86c0-.91.25-1.53 1.56-1.53h1.66V3.51C15.9 3.42 15 3.36 13.94 3.36c-2.42 0-4.08 1.48-4.08 4.19v2.35H7.15v3.14h2.71V21z"
									/>
								</svg>
							{:else if social.icon === 'instagram'}
								<svg viewBox="0 0 24 24" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2">
									<rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
									<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
									<line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
								</svg>
							{:else if social.icon === 'tiktok'}
								<svg viewBox="0 0 24 24" class="w-4 h-4" fill="currentColor">
									<path
										d="M16.5 2h-3.1v13.7c0 1.4-1.1 2.5-2.5 2.5s-2.5-1.1-2.5-2.5 1.1-2.5 2.5-2.5c.28 0 .55.05.8.13V10.2a5.6 5.6 0 0 0-.8-.06 5.6 5.6 0 1 0 5.6 5.6V8.9a7.8 7.8 0 0 0 4.4 1.36V7.16A4.6 4.6 0 0 1 16.5 2z"
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
			<p>&copy; {year} EddyArt. All rights reserved.</p>
			<p>
				Developed by
				<a
					href="https://github.com"
					target="_blank"
					rel="noopener noreferrer"
					class="text-primary hover:underline"
				>
					Eddy
				</a>
			</p>
		</div>
	</div>
</footer>
