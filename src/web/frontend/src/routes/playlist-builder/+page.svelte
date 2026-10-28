<script>
	import { onDestroy, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { PUBLIC_API_URL } from '$env/static/public';
	import {
		page,
		generatedPlaylist,
		chatMessages,
		playlistRequested,
		builderRequest,
		llmConfig,
		llmSettingsOpen,
		selectedSong,
		exploreTrail,
		discoveryPlaylist
	} from '../../stores.js';
	import { llmHeaders } from '$lib/llmHeaders.js';
	import { playlistName } from '$lib/builder.js';
	import Composer from '$lib/components/builder/Composer.svelte';
	import Conversation from '$lib/components/builder/Conversation.svelte';
	import PlaylistView from '$lib/components/builder/PlaylistView.svelte';

	const AI_NAMES = { claude: 'Claude', openai: 'OpenAI', groq: 'Groq', 'claude-code': 'Your Claude Code' };
	$: aiLabel = $llmConfig.connected ? AI_NAMES[$llmConfig.provider] ?? $llmConfig.provider : 'no AI connected';

	let draft = '';
	let count = 10;
	let loading = false;
	let error = '';
	let needsKey = false;
	let step = 0;
	let stepTimer;

	$: firstPrompt = $chatMessages.find((m) => m.role === 'user')?.content ?? '';
	$: active = $chatMessages.length > 0 || loading;

	onMount(() => {
		$page = 'Playlist Builder';
		// A prompt handed over from Explore or Profile starts a fresh playlist.
		if ($builderRequest) {
			const p = $builderRequest;
			$builderRequest = null;
			reset();
			send(p);
		}
	});
	onDestroy(() => clearTimeout(stepTimer));

	async function send(prompt) {
		if (!prompt.trim() || loading) return;
		const history = $chatMessages;
		$chatMessages = [...history, { role: 'user', content: prompt }];
		loading = true;
		error = '';
		needsKey = false;
		// One request does both steps; the second lights up once picking has had time.
		step = 0;
		clearTimeout(stepTimer);
		stepTimer = setTimeout(() => (step = 1), 4000);
		try {
			const res = await fetch(`${PUBLIC_API_URL}/llm/generate-playlist/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', ...llmHeaders() },
				body: JSON.stringify({ prompt, messages: history, count })
			});
			if (res.status === 401) {
				needsKey = true;
				error = 'Connect an AI in Settings to build playlists.';
				$chatMessages = history.length ? history : [];
				return;
			}
			const data = await res.json();
			$chatMessages = data.messages ?? $chatMessages;
			if (data.playlist?.length) {
				$generatedPlaylist = data.playlist;
				$playlistRequested = data.requested ?? count;
			} else {
				error = data.error ?? "Couldn't build that one. Try describing it another way.";
			}
		} catch {
			error = 'Something went wrong. Make sure the backend is running.';
		} finally {
			loading = false;
			clearTimeout(stepTimer);
		}
	}

	function reset() {
		$chatMessages = [];
		$generatedPlaylist = [];
		$playlistRequested = 0;
		error = '';
		needsKey = false;
	}

	function explore(song) {
		$selectedSong = { title: song.title, artists: song.artists, id: song.id, image: song.image, isrc: song.isrc };
		$exploreTrail = [$selectedSong];
		$discoveryPlaylist = [];
		goto('/');
	}
</script>

<svelte:head>
	<title>Playlist builder · Boomin Beats</title>
	<meta name="description" content="AI-powered playlist builder" />
</svelte:head>

<div class="bleed">
	{#if !active}
		<Composer bind:draft bind:count {aiLabel} busy={loading} onSubmit={send} />
		{#if error}
			<div class="empty-error" role="alert">
				<p>{error}</p>
				{#if needsKey}<button class="btn small primary" on:click={() => ($llmSettingsOpen = true)}>Open AI settings</button>{/if}
			</div>
		{/if}
	{:else}
		<div class="active">
			<div class="playlist">
				<PlaylistView
					tracks={$generatedPlaylist}
					requested={$playlistRequested}
					name={playlistName(firstPrompt)}
					prompt={firstPrompt}
					{aiLabel}
					building={loading && !$generatedPlaylist.length}
					refining={loading && $generatedPlaylist.length > 0}
					onOpen={explore}
				/>
			</div>
			<div class="chat">
				<Conversation
					messages={$chatMessages}
					{loading}
					{step}
					{error}
					onSend={send}
					onReset={reset}
					onOpenSettings={needsKey ? () => ($llmSettingsOpen = true) : null}
				/>
			</div>
		</div>
	{/if}
</div>

<style>
	.bleed {
		margin: calc(var(--primary-spacing) * -1);
		min-width: 0;
	}

	.empty-error {
		position: fixed;
		left: 50%;
		bottom: calc(var(--mini-h, 0px) + 24px);
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 10px 10px 16px;
		border-radius: 12px;
		background: var(--popover);
		border: 1px solid rgba(255, 122, 122, 0.25);
		color: #ffb0b0;
		font-size: 14px;
	}

	.empty-error p {
		margin: 0;
	}

	/* Desktop: chat | playlist, filling the window; each column scrolls. */
	.active {
		display: grid;
		grid-template-columns: minmax(340px, 420px) minmax(0, 1fr);
		height: calc(100vh - var(--header-height) - var(--mini-h, 0px));
	}

	.chat {
		order: -1;
		min-height: 0;
	}

	.playlist {
		min-height: 0;
	}

	@media (max-width: 1179px) {
		.active {
			grid-template-columns: minmax(0, 1fr);
			height: auto;
		}
		.chat {
			order: 1;
			height: 520px;
			border-top: 1px solid var(--border-subtle);
		}
		.chat :global(.conv) {
			border-right: none;
		}
	}
</style>
