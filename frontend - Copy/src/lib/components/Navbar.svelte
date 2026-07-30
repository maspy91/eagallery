<script lang="ts">
	import { page } from '$app/stores';
	import { currentUser, logout } from '$lib/stores/auth';
	import { mockNotifications } from '$lib/data/mock';
	import ThemeToggle from './ThemeToggle.svelte';
	import { Shield, LogOut, LayoutDashboard, Menu, X, Bell, User } from '@lucide/svelte';

	$: isStaffOrAdmin = $currentUser?.role === 'admin' || $currentUser?.role === 'staff';
	$: isCustomer = $currentUser?.role === 'customer';

	$: unreadCount = isCustomer
		? mockNotifications.filter((n) => n.userId === $currentUser!.id && !n.read).length
		: 0;

	let mobileOpen = false;
	$: $page.url.pathname, (mobileOpen = false);
</script>

<header class="sticky top-0 z-50 glass border-b border-border/40">
	<div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
		<a href="/" class="text-xl font-bold text-gradient shrink-0">
			EddyArt Gallery
		</a>

		<!-- Desktop nav -->
		<nav class="hidden md:flex items-center gap-6 text-sm font-medium">
			<a
				href="/"
				class="transition-smooth hover:text-primary {$page.url.pathname === '/'
					? 'text-primary'
					: 'text-muted-foreground'}"
			>
				Gallery
			</a>

			{#if isStaffOrAdmin}
				<a
					href="/admin"
					class="flex items-center gap-1.5 transition-smooth hover:text-primary {$page.url.pathname.startsWith(
						'/admin'
					)
						? 'text-primary'
						: 'text-muted-foreground'}"
				>
					<LayoutDashboard class="w-4 h-4" />
					Dashboard
				</a>
			{/if}

			{#if isCustomer}
				<a
					href="/dashboard"
					class="flex items-center gap-1.5 transition-smooth hover:text-primary {$page.url.pathname.startsWith(
						'/dashboard'
					)
						? 'text-primary'
						: 'text-muted-foreground'}"
				>
					<LayoutDashboard class="w-4 h-4" />
					Dashboard
				</a>
			{/if}
		</nav>

		<div class="flex items-center gap-2 sm:gap-3">
			<ThemeToggle />

			<!-- Desktop-only auth area -->
			<div class="hidden md:flex items-center gap-3">
				{#if isCustomer}
					<a
						href="/dashboard/notifications"
						class="relative w-9 h-9 rounded-lg glass border-border/60 hover:border-primary/50 transition-smooth flex items-center justify-center"
						aria-label="Notifications"
					>
						<Bell class="w-4 h-4" />
						{#if unreadCount > 0}
							<span
								class="absolute -top-1 -right-1 min-w-[1.1rem] h-[1.1rem] px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-semibold flex items-center justify-center"
							>
								{unreadCount}
							</span>
						{/if}
					</a>
				{/if}

				{#if $currentUser}
					<div class="flex items-center gap-2 text-sm text-muted-foreground">
						<div
							class="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-xs font-semibold text-primary-foreground"
						>
							{$currentUser.avatarInitials}
						</div>
						<span>{$currentUser.name}</span>
					</div>
					<button
						on:click={logout}
						class="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-destructive transition-smooth"
						aria-label="Sign out"
					>
						<LogOut class="w-4 h-4" />
					</button>
				{:else}
					<a
						href="/login"
						class="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm font-medium"
					>
						<User class="w-4 h-4" />
						Sign In
					</a>
					<a
						href="/auth"
						class="w-9 h-9 rounded-lg glass border-border/60 hover:border-primary/50 transition-smooth flex items-center justify-center shrink-0"
						aria-label="Admin sign in"
						title="Admin sign in"
					>
						<Shield class="w-4 h-4" />
					</a>
				{/if}
			</div>

			<!-- Mobile hamburger -->
			<button
				on:click={() => (mobileOpen = !mobileOpen)}
				class="md:hidden w-9 h-9 rounded-lg glass border-border/60 flex items-center justify-center relative"
				aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
				aria-expanded={mobileOpen}
				aria-controls="mobile-menu"
			>
				{#if mobileOpen}
					<X class="w-5 h-5" />
				{:else}
					<Menu class="w-5 h-5" />
					{#if unreadCount > 0}
						<span class="absolute top-0.5 right-0.5 w-2 h-2 rounded-full bg-primary" />
					{/if}
				{/if}
			</button>
		</div>
	</div>

	<!-- Mobile menu panel -->
	{#if mobileOpen}
		<nav
			id="mobile-menu"
			class="md:hidden border-t border-border/40 glass px-4 py-4 space-y-1 animate-fade-in"
		>
			<a
				href="/"
				class="flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-smooth {$page.url
					.pathname === '/'
					? 'bg-primary/10 text-primary'
					: 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
			>
				Gallery
			</a>

			{#if isStaffOrAdmin || isCustomer}
				<a
					href={isStaffOrAdmin ? '/admin' : '/dashboard'}
					class="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-smooth {$page.url.pathname.startsWith(
						isStaffOrAdmin ? '/admin' : '/dashboard'
					)
						? 'bg-primary/10 text-primary'
						: 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
				>
					<LayoutDashboard class="w-4 h-4" />
					Dashboard
				</a>
			{/if}

			{#if isCustomer}
				<a
					href="/dashboard/notifications"
					class="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-smooth"
				>
					<span class="flex items-center gap-2"><Bell class="w-4 h-4" />Notifications</span>
					{#if unreadCount > 0}
						<span class="min-w-[1.25rem] h-5 px-1 rounded-full bg-primary text-primary-foreground text-xs font-semibold flex items-center justify-center">
							{unreadCount}
						</span>
					{/if}
				</a>
			{/if}

			<div class="pt-3 mt-3 border-t border-border/40">
				{#if $currentUser}
					<div class="flex items-center justify-between px-3 py-2">
						<div class="flex items-center gap-2 text-sm">
							<div
								class="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-xs font-semibold text-primary-foreground"
							>
								{$currentUser.avatarInitials}
							</div>
							<div>
								<p class="font-medium text-foreground">{$currentUser.name}</p>
								<p class="text-xs text-muted-foreground capitalize">{$currentUser.role}</p>
							</div>
						</div>
						<button
							on:click={logout}
							class="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-destructive transition-smooth px-2 py-1"
						>
							<LogOut class="w-4 h-4" />
							Sign out
						</button>
					</div>
				{:else}
					<div class="flex flex-col gap-2">
						<a
							href="/login"
							class="flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm font-medium"
						>
							<User class="w-4 h-4" />
							Sign In
						</a>
						<a
							href="/register"
							class="flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg glass border-border/60 hover:border-primary/50 transition-smooth text-sm font-medium"
						>
							Create Account
						</a>
						<a
							href="/auth"
							class="flex items-center justify-center gap-2 px-3 py-2 text-xs text-muted-foreground hover:text-primary transition-smooth"
						>
							<Shield class="w-3.5 h-3.5" />
							Admin sign in
						</a>
					</div>
				{/if}
			</div>
		</nav>
	{/if}
</header>
