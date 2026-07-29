<script lang="ts">
	import { page } from '$app/stores';
	import { Send, Plus, MessagesSquare } from '@lucide/svelte';
	import { currentUser } from '$lib/stores/auth';
	import { mockConversations } from '$lib/data/mock';
	import type { BusinessConversation } from '$lib/types';

	$: myId = $currentUser?.id;
	let conversations: BusinessConversation[] = [];
	$: conversations = mockConversations.filter((c) => c.customerId === myId);

	let selected: BusinessConversation | null = null;
	$: if (!selected && conversations.length > 0) selected = conversations[0];

	let composing = $page.url.searchParams.get('new') === '1';
	let newSubject = '';
	let newMessage = '';
	let reply = '';

	const statusStyle: Record<BusinessConversation['status'], string> = {
		new: 'bg-primary/10 text-primary',
		in_progress: 'bg-secondary/10 text-secondary',
		resolved: 'bg-success/10 text-success'
	};

	function select(c: BusinessConversation) {
		selected = c;
		composing = false;
		reply = '';
	}

	function startNew() {
		composing = true;
		selected = null;
	}

	function sendNew() {
		if (!newSubject.trim() || !newMessage.trim() || !$currentUser) return;
		const conversation: BusinessConversation = {
			id: Math.max(0, ...mockConversations.map((c) => c.id)) + 1,
			customerId: $currentUser.id,
			customerName: $currentUser.name,
			customerEmail: $currentUser.email,
			subject: newSubject.trim(),
			status: 'new',
			updatedAt: new Date().toISOString(),
			messages: [
				{
					id: 1,
					senderRole: 'customer',
					senderName: $currentUser.name,
					text: newMessage.trim(),
					timestamp: new Date().toISOString()
				}
			]
		};
		mockConversations.unshift(conversation);
		conversations = mockConversations.filter((c) => c.customerId === myId);
		newSubject = '';
		newMessage = '';
		select(conversation);
	}

	function sendReply() {
		if (!selected || !reply.trim() || !$currentUser) return;
		selected.messages.push({
			id: selected.messages.length + 1,
			senderRole: 'customer',
			senderName: $currentUser.name,
			text: reply.trim(),
			timestamp: new Date().toISOString()
		});
		selected = { ...selected };
		reply = '';
	}
</script>

<svelte:head><title>Inbox — EddyArt Gallery</title></svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between flex-wrap gap-4">
		<div>
			<h1 class="text-3xl font-bold text-foreground">Inbox</h1>
			<p class="text-muted-foreground mt-1">Your direct conversations with the platform team.</p>
		</div>
		<button
			on:click={startNew}
			class="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm font-medium"
		>
			<Plus class="w-4 h-4" />
			New conversation
		</button>
	</div>

	<div class="grid lg:grid-cols-[320px_1fr] gap-6">
		<div class="glass elevated rounded-xl divide-y divide-border/60 overflow-hidden">
			{#each conversations as c (c.id)}
				<button
					on:click={() => select(c)}
					class="w-full text-left p-4 transition-colors {selected?.id === c.id && !composing ? 'bg-primary/5' : 'hover:bg-muted/40'}"
				>
					<div class="flex items-center justify-between gap-2">
						<span class="font-medium text-foreground text-sm truncate">{c.subject}</span>
						<span class="shrink-0 px-2 py-0.5 rounded-full text-xs font-medium capitalize {statusStyle[c.status]}">
							{c.status.replace('_', ' ')}
						</span>
					</div>
					<p class="text-sm text-muted-foreground truncate mt-0.5">
						{c.messages[c.messages.length - 1]?.text}
					</p>
				</button>
			{/each}
			{#if conversations.length === 0}
				<p class="text-center text-muted-foreground py-12 px-4">No conversations yet.</p>
			{/if}
		</div>

		<div class="glass elevated rounded-xl p-6">
			{#if composing}
				<h2 class="text-xl font-bold text-foreground mb-4">Start a new conversation</h2>
				<div class="space-y-4">
					<div class="space-y-2">
						<label for="subject" class="text-sm font-medium text-foreground">Subject</label>
						<input
							id="subject"
							bind:value={newSubject}
							placeholder="What's this about?"
							class="w-full h-11 px-3 rounded-lg border border-input bg-background/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						/>
					</div>
					<div class="space-y-2">
						<label for="message" class="text-sm font-medium text-foreground">Message</label>
						<textarea
							id="message"
							bind:value={newMessage}
							placeholder="Tell us what you need..."
							class="w-full min-h-[140px] resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						/>
					</div>
					<button
						on:click={sendNew}
						disabled={!newSubject.trim() || !newMessage.trim()}
						class="flex items-center gap-2 px-4 py-2.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity text-sm font-medium"
					>
						<Send class="w-4 h-4" />
						Send message
					</button>
				</div>
			{:else if selected}
				<div class="flex items-start justify-between gap-4 mb-4">
					<h2 class="text-xl font-bold text-foreground">{selected.subject}</h2>
					<span class="shrink-0 px-2.5 py-1 rounded-full text-xs font-medium capitalize {statusStyle[selected.status]}">
						{selected.status.replace('_', ' ')}
					</span>
				</div>

				<div class="space-y-4 max-h-[420px] overflow-y-auto pr-1">
					{#each selected.messages as m (m.id)}
						<div class="flex {m.senderRole === 'customer' ? 'justify-end' : 'justify-start'}">
							<div
								class="max-w-[80%] rounded-xl px-4 py-2.5 text-sm {m.senderRole === 'customer'
									? 'bg-primary text-primary-foreground'
									: 'bg-muted text-foreground'}"
							>
								{#if m.senderRole !== 'customer'}
									<p class="text-xs font-semibold mb-0.5 opacity-80">{m.senderName} · Team</p>
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
						placeholder="Write a message..."
						class="w-full min-h-[90px] resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					/>
					<button
						on:click={sendReply}
						disabled={!reply.trim()}
						class="flex items-center gap-2 px-4 py-2.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity text-sm font-medium"
					>
						<Send class="w-4 h-4" />
						Send
					</button>
				</div>
			{:else}
				<div class="text-center py-16 text-muted-foreground">
					<MessagesSquare class="w-10 h-10 mx-auto mb-3 opacity-50" />
					<p>Select a conversation, or start a new one.</p>
				</div>
			{/if}
		</div>
	</div>
</div>
