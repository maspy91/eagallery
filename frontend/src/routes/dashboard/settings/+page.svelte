<script lang="ts">
	import AccountSettings from '$lib/components/AccountSettings.svelte';
</script>

<svelte:head><title>Account Settings — EddyArt</title></svelte:head>

<div class="space-y-6">
	<div>
		<h1 class="text-3xl font-bold text-foreground">Account settings</h1>
		<p class="text-muted-foreground mt-1">Update your name, email, or password.</p>
	</div>

	<AccountSettings />
</div>
