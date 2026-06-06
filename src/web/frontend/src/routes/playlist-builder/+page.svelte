<script>
	import { onMount } from 'svelte';
	import { page, generatedPlaylist, chatMessages } from '../../stores.js';
	import ChatInterface from '$lib/components/ChatInterface.svelte';
	import PlaylistResult from '$lib/components/PlaylistResult.svelte';

	let requested = 0;

	onMount(() => {
		$page = 'Playlist Builder';
	});

	function onResult(data) {
		requested = data.requested;
		$generatedPlaylist = data.playlist;
	}

	function clearPlaylist() {
		$generatedPlaylist = [];
		$chatMessages = [];
		requested = 0;
	}
</script>

<svelte:head>
	<title>Playlist Builder</title>
	<meta name="description" content="AI-powered playlist builder" />
</svelte:head>

<div class="body-div">
	<ChatInterface {onResult} />
	<PlaylistResult playlist={$generatedPlaylist} {requested} onClear={clearPlaylist} />
</div>

<style>
	.body-div {
		min-height: 100vh;
		width: 100%;
		min-width: 800px;
		margin-top: 65px;
	}
</style>
