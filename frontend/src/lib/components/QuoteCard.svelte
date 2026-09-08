<script lang="ts">
	// Shared between /admin/requests (staff/admin: can withdraw a pending
	// quote) and /dashboard/inbox (customer: can accept/decline a
	// pending quote) -- the display is identical either way, only which
	// action buttons show differs, driven by the `role` prop.

	import { Receipt, CircleCheck, CircleX, Ban, LoaderCircle } from '@lucide/svelte';
	import { conversationsApi, ApiError, type ApiConversation, type ApiQuote } from '$lib/api';

	export let quote: ApiQuote;
	export let conversationId: string;
	export let role: 'customer' | 'staff';
	// Called with the fresh conversation after any action succeeds --
	// the parent page owns the actual conversation list/selection state,
	// this component just reports the result upward.
	export let onUpdated: (updated: ApiConversation) => void;

	let acting = false;
	let error = '';

	function formatAmount(cents: number, currency: string): string {
		return `${currency} ${(cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
	}

	const statusStyle: Record<ApiQuote['status'], string> = {
		pending: 'bg-primary/10 text-primary',
		accepted: 'bg-success/10 text-success',
		declined: 'bg-destructive/10 text-destructive',
		withdrawn: 'bg-muted text-muted-foreground'
	};

	async function act(action: 'accept' | 'decline' | 'withdraw') {
		acting = true;
		error = '';
		try {
			const updated =
				action === 'accept'
					? await conversationsApi.acceptQuote(conversationId, quote.id)
					: action === 'decline'
						? await conversationsApi.declineQuote(conversationId, quote.id)
						: await conversationsApi.withdrawQuote(conversationId, quote.id);
			onUpdated(updated);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not update this quote.';
		} finally {
			acting = false;
		}
	}
</script>

<div class="rounded-xl border border-primary/20 bg-primary/5 p-4 max-w-[85%]">
	<div class="flex items-start justify-between gap-3">
		<div class="flex items-center gap-2 text-sm font-semibold text-foreground">
			<Receipt class="w-4 h-4 text-primary" />
			Quote from {quote.createdByName}
		</div>
		<span class="shrink-0 px-2 py-0.5 rounded-full text-xs font-medium capitalize {statusStyle[quote.status]}">
			{quote.status}
		</span>
	</div>

	<p class="text-2xl font-bold text-foreground mt-2">{formatAmount(quote.amountCents, quote.currency)}</p>
	<p class="text-sm text-muted-foreground mt-1">{quote.description}</p>
	<p class="text-[10px] text-muted-foreground/70 mt-2">
		{new Date(quote.createdAt).toLocaleString()}
		{#if quote.respondedAt}
			· {quote.status} {new Date(quote.respondedAt).toLocaleString()}
		{/if}
	</p>

	{#if error}
		<p class="text-sm text-destructive mt-2">{error}</p>
	{/if}

	{#if quote.status === 'pending'}
		<div class="flex gap-2 mt-3">
			{#if role === 'customer'}
				<button
					on:click={() => act('accept')}
					disabled={acting}
					class="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-success text-success-foreground text-xs font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
				>
					{#if acting}<LoaderCircle class="w-3.5 h-3.5 animate-spin" />{:else}<CircleCheck class="w-3.5 h-3.5" />{/if}
					Accept
				</button>
				<button
					on:click={() => act('decline')}
					disabled={acting}
					class="flex items-center gap-1.5 px-3 py-1.5 rounded-md glass border-border/60 text-xs font-medium hover:border-destructive/50 hover:text-destructive disabled:opacity-50 transition-smooth"
				>
					<CircleX class="w-3.5 h-3.5" />
					Decline
				</button>
			{:else}
				<button
					on:click={() => act('withdraw')}
					disabled={acting}
					class="flex items-center gap-1.5 px-3 py-1.5 rounded-md glass border-border/60 text-xs font-medium hover:border-destructive/50 hover:text-destructive disabled:opacity-50 transition-smooth"
				>
					{#if acting}<LoaderCircle class="w-3.5 h-3.5 animate-spin" />{:else}<Ban class="w-3.5 h-3.5" />{/if}
					Withdraw
				</button>
			{/if}
		</div>
	{/if}
</div>
