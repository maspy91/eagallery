<script lang="ts">
	// frontend/src/routes/admin/requests/+page.svelte
	// EDITED FILE — replaces: src/routes/admin/requests/+page.svelte (whole-file replacement)
	// Replaced the in-memory `[...mockConversations]` copy with GET
	// /api/conversations (requests:respond). send()/resolve() now call the
	// real reply/status endpoints instead of mutating local state directly.

	import { onMount } from 'svelte';
	import { Mail, Send, CircleCheckBig, LoaderCircle } from '@lucide/svelte';
	import { conversationsApi, ApiError, type ApiConversation } from '$lib/api';

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
			conversations = await conversationsApi.listAll();
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
	}

	async function send() {
		if (!selected || !reply.trim()) return;
		sending = true;
		formError = '';
		try {
			const updated = await conversationsApi.reply(selected.id, reply.trim());
			conversations = conversations.map((c) => (c.id === updated.id ? updated : c));
			selected = updated;
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
			conversations = conversations.map((c) => (c.id === updated.id ? updated : c));
			selected = updated;
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'Could not update status.';
		}
	}
</script>

<svelte:head><title>Requests — EddyArt Gallery Admin</title></svelte:head>

<div class="space-y-6">
	<div>
		<h1 class="text-3xl font-bold text-foreground">Business Requests</h1>
		<p class="text-muted-foreground mt-1">
			Every conversation a customer starts from their dashboard Inbox shows up here. Replies here appear back in
			their Inbox — it's the same thread.
		</p>
	</div>

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
					{#each selected.messages as m (m.id)}
						<div class="flex {m.senderRole === 'customer' ? 'justify-start' : 'justify-end'}">
							<div
								class="max-w-[80%] rounded-xl px-4 py-2.5 text-sm {m.senderRole === 'customer'
									? 'bg-muted text-foreground'
									: 'bg-primary text-primary-foreground'}"
							>
								{#if m.senderRole !== 'customer'}
									<p class="text-xs font-semibold mb-0.5 opacity-80">{m.senderName}</p>
								{/if}
								<p>{m.text}</p>
								<p class="text-[10px] opacity-70 mt-1">{new Date(m.timestamp).toLocaleString()}</p>
							</div>
						</div>
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
					</div>
				</div>
			{:else}
				<p class="text-center text-muted-foreground py-12">Select a request to view it.</p>
			{/if}
		</div>
	</div>
</div>
