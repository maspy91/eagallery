<script lang="ts">
	import { onMount } from 'svelte';
	import { UserX, UserCheck, LoaderCircle, BadgeCheck, BadgeAlert } from '@lucide/svelte';
	import { customersApi, ApiError, type ApiCustomer } from '$lib/api';
	import AdminListControls from '$lib/components/AdminListControls.svelte';

	let customers: ApiCustomer[] = [];
	let totalCount = 0;
	let loading = true;
	let listError = '';

	let search = '';
	let dateFrom = '';
	let dateTo = '';
	let statusFilter: 'all' | 'active' | 'inactive' = 'all';
	$: exportHref = customersApi.exportUrl({
		q: search,
		date_from: dateFrom,
		date_to: dateTo,
		is_active: statusFilter === 'all' ? undefined : statusFilter === 'active'
	});

	let updatingId: string | null = null;

	async function load() {
		loading = true;
		listError = '';
		try {
			const [result, stats] = await Promise.all([
				customersApi.list({
					q: search,
					date_from: dateFrom,
					date_to: dateTo,
					is_active: statusFilter === 'all' ? undefined : statusFilter === 'active'
				}),
				customersApi.stats()
			]);
			customers = result;
			totalCount = stats.totalCount;
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not load customers.';
		} finally {
			loading = false;
		}
	}

	onMount(load);

	async function toggleActive(customer: ApiCustomer) {
		updatingId = customer.id;
		try {
			const updated = await customersApi.setActive(customer.id, !customer.isActive);
			customers = customers.map((c) => (c.id === updated.id ? updated : c));
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'Could not update this customer.';
		} finally {
			updatingId = null;
		}
	}

	function formatDate(iso: string): string {
		if (!iso) return '—';
		try {
			return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
		} catch {
			return '—';
		}
	}
</script>

<svelte:head><title>Customers — EddyArt Admin</title></svelte:head>

<div class="space-y-6">
	<div class="flex items-end justify-between flex-wrap gap-3">
		<div>
			<h1 class="text-3xl font-bold text-foreground">Customers</h1>
			<p class="text-muted-foreground mt-1">
				{totalCount} registered customer{totalCount === 1 ? '' : 's'}.
			</p>
		</div>
	</div>

	<AdminListControls bind:search bind:dateFrom bind:dateTo {exportHref} searchPlaceholder="Search by name or email…" onChange={load}>
		<select
			bind:value={statusFilter}
			on:change={load}
			class="h-10 px-3 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-sm"
		>
			<option value="all">All statuses</option>
			<option value="active">Active only</option>
			<option value="inactive">Deactivated only</option>
		</select>
	</AdminListControls>

	<div class="glass elevated rounded-xl overflow-hidden">
		{#if listError}
			<p class="text-sm text-destructive text-center py-6">{listError}</p>
		{:else}
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-border text-left text-muted-foreground">
						<th class="px-5 py-3 font-medium">Name</th>
						<th class="px-5 py-3 font-medium">Email</th>
						<th class="px-5 py-3 font-medium">Joined</th>
						<th class="px-5 py-3 font-medium">Status</th>
						<th class="px-5 py-3 font-medium text-right">Actions</th>
					</tr>
				</thead>
				<tbody>
					{#if loading}
						<tr>
							<td colspan="5" class="px-5 py-6 text-center text-muted-foreground">
								<LoaderCircle class="w-4 h-4 animate-spin inline-block mr-2" />
								Loading customers…
							</td>
						</tr>
					{:else}
						{#each customers as c (c.id)}
							<tr class="border-b border-border/60 last:border-0 hover:bg-muted/40 transition-colors">
								<td class="px-5 py-3 font-medium text-foreground">{c.name}</td>
								<td class="px-5 py-3 text-muted-foreground">
									<div class="flex items-center gap-1.5">
										{c.email}
										{#if c.emailVerified}
											<BadgeCheck class="w-3.5 h-3.5 text-success shrink-0" />
										{:else}
											<BadgeAlert class="w-3.5 h-3.5 text-amber-500 shrink-0" />
										{/if}
									</div>
								</td>
								<td class="px-5 py-3 text-muted-foreground">{formatDate(c.createdAt)}</td>
								<td class="px-5 py-3">
									{#if c.isActive}
										<span class="px-2.5 py-1 rounded-full text-xs font-medium bg-success/10 text-success">active</span>
									{:else}
										<span class="px-2.5 py-1 rounded-full text-xs font-medium bg-destructive/10 text-destructive">deactivated</span>
									{/if}
								</td>
								<td class="px-5 py-3">
									<div class="flex justify-end">
										<button
											on:click={() => toggleActive(c)}
											disabled={updatingId === c.id}
											class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs transition-colors disabled:opacity-50 {c.isActive
												? 'text-destructive hover:bg-destructive/10'
												: 'text-success hover:bg-success/10'}"
										>
											{#if updatingId === c.id}
												<LoaderCircle class="w-3.5 h-3.5 animate-spin" />
											{:else if c.isActive}
												<UserX class="w-3.5 h-3.5" />
											{:else}
												<UserCheck class="w-3.5 h-3.5" />
											{/if}
											{c.isActive ? 'Deactivate' : 'Reactivate'}
										</button>
									</div>
								</td>
							</tr>
						{:else}
							<tr>
								<td colspan="5" class="px-5 py-6 text-center text-muted-foreground">
									{search || dateFrom || dateTo || statusFilter !== 'all'
										? 'No customers match your search.'
										: 'No customers yet.'}
								</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		{/if}
	</div>
</div>
