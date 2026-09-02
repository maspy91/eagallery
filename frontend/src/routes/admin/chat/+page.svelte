<script lang="ts">
	import { onMount } from 'svelte';
	import { MessageCircle, Send, LoaderCircle, Bot, UserRound, Mail } from '@lucide/svelte';
	import { adminChatApi, ApiError, type ApiAdminChatThread, type ApiAdminChatThreadDetail } from '$lib/api';

	// Mirrors admin/requests/+page.svelte's list+detail layout -- see that
	// file for the base pattern. Genuinely different here: threads have a
	// mode (pending_admin/human, never shown here in 'ai' mode -- the
	// backend's list endpoint only ever returns forwarded/picked-up
	// threads, see chat.py's list_threads) and a pickup/hand-back toggle
	// instead of a resolve button, since chat threads don't have a
	// separate "resolved" state the way Business Requests do.
	let threads: ApiAdminChatThread[] = [];
	let loading = true;
	let loadError = '';

	let selectedId: string | null = null;
	let selected: ApiAdminChatThreadDetail | null = null;
	let loadingDetail = false;

	let reply = '';
	let sending = false;
	let formError = '';
	let togglingMode = false;

	async function load() {
		loading = true;
		loadError = '';
		try {
			threads = await adminChatApi.listThreads();
			if (!selectedId && threads.length > 0) select(threads[0].id);
		} catch (err) {
			loadError = err instanceof ApiError ? err.message : 'Could not load chat threads.';
		} finally {
			loading = false;
		}
	}

	onMount(load);

	async function select(id: string) {
		selectedId = id;
		reply = '';
		formError = '';
		loadingDetail = true;
		try {
			selected = await adminChatApi.getThread(id);
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'Could not load this conversation.';
		} finally {
			loadingDetail = false;
		}
	}

	async function refreshListEntry() {
		try {
			threads = await adminChatApi.listThreads();
		} catch {
			// the detail pane is already showing the current state; a
			// failed list refresh just means the sidebar preview/order
			// might lag slightly, not worth surfacing an error for
		}
	}

	async function send() {
		if (!selectedId || !reply.trim() || sending) return;
		sending = true;
		formError = '';
		try {
			selected = await adminChatApi.reply(selectedId, reply.trim());
			reply = '';
			await refreshListEntry();
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'Could not send your reply.';
		} finally {
			sending = false;
		}
	}

	async function toggleMode() {
		if (!selectedId || !selected || togglingMode) return;
		togglingMode = true;
		formError = '';
		try {
			const nextMode = selected.mode === 'human' ? 'ai' : 'human';
			selected = await adminChatApi.setMode(selectedId, nextMode);
			await refreshListEntry();
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'Could not update this conversation.';
		} finally {
			togglingMode = false;
		}
	}
</script>

<svelte:head><title>Live Chat — EddyArt Gallery Admin</title></svelte:head>

<div class="space-y-6">
	<div>
		<h1 class="text-3xl font-bold text-foreground">Live Chat</h1>
		<p class="text-muted-foreground mt-1">
			Conversations our AI assistant has flagged, plus anything you've picked up yourself. Replying takes over the
			thread automatically; hand it back to the assistant any time.
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
				{#each threads as t (t.id)}
					<button
						on:click={() => select(t.id)}
						class="w-full text-left p-4 transition-colors {selectedId === t.id ? 'bg-primary/5' : 'hover:bg-muted/40'}"
					>
						<div class="flex items-center justify-between gap-2">
							<span class="font-medium text-foreground text-sm truncate">
								{t.displayName}{t.isGuest ? ' (guest)' : ''}
							</span>
							<span
								class="shrink-0 px-2 py-0.5 rounded-full text-xs font-medium {t.mode === 'human'
									? 'bg-success/10 text-success'
									: 'bg-primary/10 text-primary'}"
							>
								{t.mode === 'human' ? (t.assignedAdminName ?? 'Assigned') : 'Needs pickup'}
							</span>
						</div>
						<p class="text-sm text-muted-foreground truncate mt-0.5">{t.lastMessagePreview}</p>
					</button>
				{:else}
					<p class="text-center text-muted-foreground py-12 px-4">
						No conversations need attention right now.
					</p>
				{/each}
			{/if}
		</div>

		<div class="glass elevated rounded-xl p-6">
			{#if loadingDetail}
				<p class="text-center text-muted-foreground py-12"><LoaderCircle class="w-4 h-4 animate-spin inline-block" /></p>
			{:else if selected}
				<div class="flex items-start justify-between gap-4 mb-1">
					<div>
						<h2 class="text-xl font-bold text-foreground flex items-center gap-2">
							<MessageCircle class="w-5 h-5 text-primary" />
							{selected.displayName}{selected.isGuest ? ' (guest)' : ''}
						</h2>
						{#if selected.contactEmail}
							<p class="text-sm text-muted-foreground mt-1 flex items-center gap-1.5">
								<Mail class="w-3.5 h-3.5" />
								{selected.contactEmail}
							</p>
						{/if}
					</div>
					<button
						on:click={toggleMode}
						disabled={togglingMode}
						class="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border hover:border-primary/50 transition-smooth text-xs font-medium disabled:opacity-50"
					>
						{#if togglingMode}
							<LoaderCircle class="w-3.5 h-3.5 animate-spin" />
						{:else if selected.mode === 'human'}
							<Bot class="w-3.5 h-3.5" />
							Hand back to AI
						{:else}
							<UserRound class="w-3.5 h-3.5" />
							Take over
						{/if}
					</button>
				</div>

				<div class="space-y-4 max-h-[380px] overflow-y-auto pr-1 mt-4">
					{#each selected.messages as m (m.id)}
						{#if m.isSystem}
							<p class="text-xs text-muted-foreground text-center py-1">{m.text}</p>
						{:else}
							<div class="flex {m.senderRole === 'customer' ? 'justify-start' : 'justify-end'}">
								<div
									class="max-w-[80%] rounded-xl px-4 py-2.5 text-sm {m.senderRole === 'customer'
										? 'bg-muted text-foreground'
										: m.senderRole === 'ai'
											? 'bg-secondary/10 text-foreground'
											: 'bg-primary text-primary-foreground'}"
								>
									{#if m.senderRole !== 'customer'}
										<p class="text-xs font-semibold mb-0.5 opacity-80 flex items-center gap-1">
											{#if m.senderRole === 'ai'}<Bot class="w-3 h-3" />{/if}
											{m.senderName}
										</p>
									{/if}
									<p class="whitespace-pre-wrap">{m.text}</p>
									<p class="text-[10px] opacity-70 mt-1">{new Date(m.timestamp).toLocaleString()}</p>
								</div>
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
					<button
						on:click={send}
						disabled={!reply.trim() || sending}
						class="flex items-center gap-2 px-4 py-2.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity text-sm font-medium"
					>
						{#if sending}<LoaderCircle class="w-4 h-4 animate-spin" />{:else}<Send class="w-4 h-4" />{/if}
						Send reply
					</button>
				</div>
			{:else}
				<p class="text-center text-muted-foreground py-12">Select a conversation to view it.</p>
			{/if}
		</div>
	</div>
</div>
