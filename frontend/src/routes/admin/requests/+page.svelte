<script lang="ts">
	import { onMount } from 'svelte';
	import { Mail, Send, CircleCheckBig, LoaderCircle, Receipt, Plus } from '@lucide/svelte';
	import { conversationsApi, ApiError, type ApiConversation } from '$lib/api';
	import QuoteCard from '$lib/components/QuoteCard.svelte';
	import AdminListControls from '$lib/components/AdminListControls.svelte';

	let search = '';
	let dateFrom = '';
	let dateTo = '';
	$: exportHref = conversationsApi.exportUrl({ q: search, date_from: dateFrom, date_to: dateTo });

	type TimelineItem =
		| { kind: 'message'; timestamp: string; message: ApiConversation['messages'][number] }
		| { kind: 'quote'; timestamp: string; quote: ApiConversation['quotes'][number] };

	function buildTimeline(c: ApiConversation): TimelineItem[] {
		const items: TimelineItem[] = [
			...c.messages.map((m) => ({ kind: 'message' as const, timestamp: m.timestamp, message: m })),
			...c.quotes.map((q) => ({ kind: 'quote' as const, timestamp: q.createdAt, quote: q }))
		];
		return items.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
	}

	function handleUpdated(updated: ApiConversation) {
		conversations = conversations.map((c) => (c.id === updated.id ? updated : c));
		selected = updated;
	}

	let showQuoteForm = false;
	let quoteDescription = '';
	let quoteAmount = '';
	let quoteSending = false;
	let quoteError = '';

	function toggleQuoteForm() {
		showQuoteForm = !showQuoteForm;
		quoteError = '';
	}

	async function sendQuote() {
		if (!selected) return;
		const amount = Number(quoteAmount);
		if (!quoteDescription.trim() || !amount || amount <= 0) {
			quoteError = 'Enter a description and an amount greater than zero.';
			return;
		}
		quoteSending = true;
		quoteError = '';
		try {
			const updated = await conversationsApi.createQuote(selected.id, quoteDescription.trim(), amount);
			handleUpdated(updated);
			quoteDescription = '';
			quoteAmount = '';
			showQuoteForm = false;
		} catch (err) {
			quoteError = err instanceof ApiError ? err.message : 'Could not send this quote.';
		} finally {
			quoteSending = false;
		}
	}

	let conversations: ApiConversation[] = [];
	let loading = true;
	let loadError = '';
	let selected: ApiConversation | null = null;
	let reply = '';
	let sending = false;
	let formError = '';

	const statusStyle: Record<ApiConversation['status'], string> = {
		new: 'bg-primary/10 text-primary',
		in_progress: 'bg-secondary/10 text-secondary',
		resolved: 'bg-success/10 text-success'
	};

	async function load() {
		loading = true;
		loadError = '';
		try {
			conversations = await conversationsApi.listAll({ q: search, date_from: dateFrom, date_to: dateTo });
			if (!selected && conversations.length > 0) selected = conversations[0];
		} catch (err) {
			loadError = err instanceof ApiError ? err.message : 'Could not load requests.';
		} finally {
			loading = false;
		}
	}

	onMount(load);

	function select(c: ApiConversation) {
		selected = c;
		reply = '';
		formError = '';
		showQuoteForm = false;
		quoteError = '';
	}

	async function send() {
		if (!selected || !reply.trim()) return;
		sending = true;
		formError = '';
		try {
			const updated = await conversationsApi.reply(selected.id, reply.trim());
			handleUpdated(updated);
			reply = '';
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'Could not send your reply.';
		} finally {
			sending = false;
		}
	}

	async function resolve() {
		if (!selected) return;
		try {
			const updated = await conversationsApi.setStatus(selected.id, 'resolved');
			handleUpdated(updated);
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'Could not update status.';
		}
	}
</script>

<svelte:head><title>Requests — EddyArt Admin</title></svelte:head>

<div class="space-y-6">
	<div>
		<h1 class="text-3xl font-bold text-foreground">Business Requests</h1>
		<p class="text-muted-foreground mt-1">
			Every conversation a customer starts from their dashboard Inbox shows up here. Replies here appear back in
			their Inbox — it's the same thread.
		</p>
	</div>

	<AdminListControls bind:search bind:dateFrom bind:dateTo {exportHref} searchPlaceholder="Search by subject, customer name, or email…" onChange={load} />

	<div class="grid lg:grid-cols-[320px_1fr] gap-6">
		<div class="glass elevated rounded-xl divide-y divide-border/60 overflow-hidden">
			{#if loading}
				<p class="text-center text-muted-foreground py-12 px-4">
					<LoaderCircle class="w-4 h-4 animate-spin inline-block mr-2" />
					Loading…
				</p>
			{:else if loadError}
				<p class="text-center text-destructive py-12 px-4">{loadError}</p>
			{:else}
				{#each conversations as c (c.id)}
					<button
						on:click={() => select(c)}
						class="w-full text-left p-4 transition-colors {selected?.id === c.id ? 'bg-primary/5' : 'hover:bg-muted/40'}"
					>
						<div class="flex items-center justify-between gap-2">
							<span class="font-medium text-foreground text-sm truncate">{c.customerName}</span>
							<span class="shrink-0 px-2 py-0.5 rounded-full text-xs font-medium capitalize {statusStyle[c.status]}">
								{c.status.replace('_', ' ')}
							</span>
						</div>
						<p class="text-sm text-muted-foreground truncate mt-0.5">{c.subject}</p>
					</button>
				{:else}
					<p class="text-center text-muted-foreground py-12 px-4">No requests yet.</p>
				{/each}
			{/if}
		</div>

		<div class="glass elevated rounded-xl p-6">
			{#if selected}
				<div class="flex items-start justify-between gap-4 mb-1">
					<div>
						<h2 class="text-xl font-bold text-foreground">{selected.subject}</h2>
						<p class="text-sm text-muted-foreground mt-1 flex items-center gap-1.5">
							<Mail class="w-3.5 h-3.5" />
							{selected.customerName} · {selected.customerEmail}
						</p>
					</div>
					<span class="shrink-0 px-2.5 py-1 rounded-full text-xs font-medium capitalize {statusStyle[selected.status]}">
						{selected.status.replace('_', ' ')}
					</span>
				</div>

				<div class="space-y-4 max-h-[380px] overflow-y-auto pr-1 mt-4">
					{#each buildTimeline(selected) as item (item.kind === 'message' ? item.message.id : item.quote.id)}
						{#if item.kind === 'message'}
							<div class="flex {item.message.senderRole === 'customer' ? 'justify-start' : 'justify-end'}">
								<div
									class="max-w-[80%] rounded-xl px-4 py-2.5 text-sm {item.message.senderRole === 'customer'
										? 'bg-muted text-foreground'
										: 'bg-primary text-primary-foreground'}"
								>
									{#if item.message.senderRole !== 'customer'}
										<p class="text-xs font-semibold mb-0.5 opacity-80">{item.message.senderName}</p>
									{/if}
									<p>{item.message.text}</p>
									<p class="text-[10px] opacity-70 mt-1">{new Date(item.message.timestamp).toLocaleString()}</p>
								</div>
							</div>
						{:else}
							<div class="flex justify-end">
								<QuoteCard quote={item.quote} conversationId={selected.id} role="staff" onUpdated={handleUpdated} />
							</div>
						{/if}
					{/each}
				</div>

				<div class="mt-6 space-y-3 pt-4 border-t border-border/40">
					<textarea
						bind:value={reply}
						placeholder="Write your response..."
						class="w-full min-h-[100px] resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					/>
					{#if formError}
						<p class="text-sm text-destructive">{formError}</p>
					{/if}
					<div class="flex gap-2">
						<button
							on:click={send}
							disabled={!reply.trim() || sending}
							class="flex items-center gap-2 px-4 py-2.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity text-sm font-medium"
						>
							{#if sending}<LoaderCircle class="w-4 h-4 animate-spin" />{:else}<Send class="w-4 h-4" />{/if}
							Send reply
						</button>
						{#if selected.status !== 'resolved'}
							<button
								on:click={resolve}
								class="flex items-center gap-2 px-4 py-2.5 rounded-md glass border-border/60 hover:border-primary/50 transition-smooth text-sm font-medium"
							>
								<CircleCheckBig class="w-4 h-4" />
								Mark resolved
							</button>
						{/if}
						<button
							type="button"
							on:click={toggleQuoteForm}
							class="flex items-center gap-2 px-4 py-2.5 rounded-md glass border-border/60 hover:border-primary/50 transition-smooth text-sm font-medium"
						>
							<Receipt class="w-4 h-4" />
							Send a quote
						</button>
					</div>

					{#if showQuoteForm}
						<div class="mt-4 pt-4 border-t border-border/40 space-y-3">
							<div class="space-y-1.5">
								<label for="quote-description" class="text-sm font-medium text-foreground">What's this for?</label>
								<textarea
									id="quote-description"
									bind:value={quoteDescription}
									placeholder="e.g. 3 illuminated shop signs, installation included"
									class="w-full min-h-[70px] resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
								></textarea>
							</div>
							<div class="space-y-1.5 max-w-[200px]">
								<label for="quote-amount" class="text-sm font-medium text-foreground">Amount (NGN)</label>
								<input
									id="quote-amount"
									type="number"
									min="0.01"
									step="0.01"
									bind:value={quoteAmount}
									placeholder="450000"
									class="w-full h-11 px-3 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
								/>
							</div>
							{#if quoteError}
								<p class="text-sm text-destructive">{quoteError}</p>
							{/if}
							<button
								type="button"
								on:click={sendQuote}
								disabled={quoteSending}
								class="flex items-center gap-2 px-4 py-2.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity text-sm font-medium"
							>
								{#if quoteSending}<LoaderCircle class="w-4 h-4 animate-spin" />{:else}<Plus class="w-4 h-4" />{/if}
								Send quote
							</button>
						</div>
					{/if}
				</div>
			{:else}
				<p class="text-center text-muted-foreground py-12">Select a request to view it.</p>
			{/if}
		</div>
	</div>
</div>
