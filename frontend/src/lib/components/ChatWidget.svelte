<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { MessageCircle, X, Send, LoaderCircle } from '@lucide/svelte';
	import { chatApi, ApiError, type ApiChatMessage, type ChatMode } from '$lib/api';
	import { currentUser } from '$lib/stores/auth';

	// Persisted in sessionStorage (not a cookie -- the backend already
	// tracks identity via its own cookies, guest or logged-in; this is
	// purely "which thread was open in this browser TAB", so a reload
	// reopens the same conversation instead of always starting fresh).
	const THREAD_STORAGE_KEY = 'eddyart_chat_thread_id';

	let open = false;
	let threadId: string | null = null;
	let messages: ApiChatMessage[] = [];
	let mode: ChatMode = 'ai';
	let contactEmail: string | null = null;

	let input = '';
	let sending = false;
	let loadError = '';

	let emailInput = '';
	let submittingEmail = false;
	let emailError = '';

	let scrollContainer: HTMLDivElement;

	async function scrollToBottom() {
		await tick();
		scrollContainer?.scrollTo({ top: scrollContainer.scrollHeight, behavior: 'smooth' });
	}

	onMount(() => {
		const saved = sessionStorage.getItem(THREAD_STORAGE_KEY);
		if (saved) {
			threadId = saved;
			loadExisting(saved);
		}
	});

	async function loadExisting(id: string) {
		try {
			const thread = await chatApi.getThread(id);
			messages = thread.messages;
			mode = thread.mode;
			contactEmail = thread.contactEmail;
		} catch {
			// The saved thread id is stale/invalid (e.g. a different
			// browser, or the cookie identifying it is gone) -- just drop
			// it silently and let the widget start fresh on next send.
			sessionStorage.removeItem(THREAD_STORAGE_KEY);
			threadId = null;
		}
	}

	function toggleOpen() {
		open = !open;
		if (open) scrollToBottom();
	}

	async function send() {
		const text = input.trim();
		if (!text || sending) return;
		input = '';
		sending = true;
		loadError = '';
		try {
			const result = await chatApi.sendMessage(text, threadId ?? undefined);
			threadId = result.threadId;
			sessionStorage.setItem(THREAD_STORAGE_KEY, threadId);
			mode = result.mode;
			messages = result.messages;
			scrollToBottom();
		} catch (err) {
			loadError = err instanceof ApiError ? err.message : 'Could not send your message. Please try again.';
			input = text; // give it back so they don't lose what they typed
		} finally {
			sending = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	}

	async function submitEmail() {
		if (!threadId || submittingEmail) return;
		submittingEmail = true;
		emailError = '';
		try {
			const thread = await chatApi.setContactEmail(threadId, emailInput.trim());
			contactEmail = thread.contactEmail;
			emailInput = '';
		} catch (err) {
			emailError = err instanceof ApiError ? err.message : 'Please enter a valid email address.';
		} finally {
			submittingEmail = false;
		}
	}
</script>

<!-- Floating launcher + panel, fixed to the viewport corner regardless of
     scroll position -- standard chat-widget placement, kept out of the
     document flow entirely so it never affects page layout. -->
<div class="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
	{#if open}
		<div class="w-[22rem] max-w-[calc(100vw-3rem)] h-[32rem] max-h-[calc(100vh-8rem)] glass elevated rounded-2xl shadow-xl flex flex-col overflow-hidden animate-fade-in">
			<div class="px-4 py-3 border-b border-border flex items-center justify-between shrink-0">
				<div>
					<p class="font-semibold text-foreground text-sm">Chat with Lucy</p>
					<p class="text-xs text-muted-foreground">
						{#if mode === 'human'}
							A team member is here
						{:else if mode === 'pending_admin'}
							Connecting you with our team
						{:else}
							Ask about the gallery
						{/if}
					</p>
				</div>
				<button on:click={toggleOpen} class="p-1.5 rounded-md hover:bg-muted transition-colors" aria-label="Close chat">
					<X class="w-4 h-4" />
				</button>
			</div>

			<div bind:this={scrollContainer} class="flex-1 overflow-y-auto px-4 py-3 space-y-3">
				{#if messages.length === 0}
					<p class="text-sm text-muted-foreground text-center py-8">
						Hi{$currentUser ? ` ${$currentUser.name.split(' ')[0]}` : ''}! Ask me anything about the gallery, or tell
						me about a custom project you have in mind.
					</p>
				{/if}
				{#each messages as m (m.id)}
					{#if m.isSystem}
						<p class="text-xs text-muted-foreground text-center py-1">{m.text}</p>
					{:else}
						<div class="flex {m.senderRole === 'customer' ? 'justify-end' : 'justify-start'}">
							<div
								class="max-w-[85%] rounded-xl px-3 py-2 text-sm {m.senderRole === 'customer'
									? 'bg-primary text-primary-foreground'
									: 'bg-muted text-foreground'}"
							>
								{#if m.senderRole !== 'customer'}
									<p class="text-xs font-medium mb-0.5 opacity-70">{m.senderName}</p>
								{/if}
								<p class="whitespace-pre-wrap">{m.text}</p>
							</div>
						</div>
					{/if}
				{/each}

				{#if mode === 'pending_admin' && !contactEmail}
					<div class="glass rounded-lg p-3 space-y-2">
						<p class="text-xs text-muted-foreground">
							Leave your email so our team can follow up if you step away.
						</p>
						<div class="flex gap-2">
							<input
								bind:value={emailInput}
								type="email"
								placeholder="you@example.com"
								class="flex-1 h-8 px-2 rounded-md border border-input bg-background/50 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
							/>
							<button
								on:click={submitEmail}
								disabled={submittingEmail || !emailInput.trim()}
								class="px-3 h-8 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
							>
								{#if submittingEmail}<LoaderCircle class="w-3 h-3 animate-spin" />{:else}Save{/if}
							</button>
						</div>
						{#if emailError}<p class="text-xs text-destructive">{emailError}</p>{/if}
					</div>
				{/if}
			</div>

			{#if loadError}
				<p class="px-4 text-xs text-destructive">{loadError}</p>
			{/if}

			<div class="p-3 border-t border-border shrink-0">
				<div class="flex items-end gap-2">
					<textarea
						bind:value={input}
						on:keydown={handleKeydown}
						rows="1"
						placeholder="Type a message…"
						class="flex-1 resize-none px-3 py-2 rounded-lg border border-input bg-background/50 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-h-24"
					/>
					<button
						on:click={send}
						disabled={sending || !input.trim()}
						class="p-2.5 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50 shrink-0"
						aria-label="Send message"
					>
						{#if sending}
							<LoaderCircle class="w-4 h-4 animate-spin" />
						{:else}
							<Send class="w-4 h-4" />
						{/if}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<button
		on:click={toggleOpen}
		class="w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-lg flex items-center justify-center hover:opacity-90 transition-opacity"
		aria-label={open ? 'Close chat' : 'Open chat'}
	>
		{#if open}
			<X class="w-6 h-6" />
		{:else}
			<MessageCircle class="w-6 h-6" />
		{/if}
	</button>
</div>
