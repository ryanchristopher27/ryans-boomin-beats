<script>
	// First run (F1): connect Spotify, pick an AI (or skip), choose where to start.
	import { goto } from '$app/navigation';
	import { access_token } from '../../../stores.js';
	import { onboarding } from '$lib/onboarding.js';
	import { beginLogin } from '$lib/spotifyAuth.js';
	import BoominBeatsLogo from '$lib/images/BoominBeatsLogo.jpg';
	import Blobs from '../ui/Blobs.svelte';
	import AiForm from './AiForm.svelte';
	import Icon from '../Icon.svelte';

	let connecting = false;

	// Spotify's sign-in leaves the page; the step is saved, so we come back on 2.
	async function connectSpotify() {
		connecting = true;
		$onboarding = 2;
		await beginLogin();
	}

	const STARTS = [
		{ href: '/', icon: 'compass', title: 'Explore a song', desc: 'Start from a song you love and find more that share what you like about it.' },
		{ href: '/playlist-builder/', icon: 'wand', title: 'Build a playlist', desc: 'Describe a mood or a moment. The AI picks the songs.' },
		{ href: '/dj/', icon: 'disc', title: 'Start a DJ set', desc: 'Run the music for a room. Guests can send requests.' }
	];

	function start(href) {
		$onboarding = 0;
		goto(href);
	}
</script>

<div class="ob" role="dialog" aria-modal="true" aria-label="Welcome to Boomin Beats">
	<Blobs hue={250} />
	<div class="inner">
		<div class="brand"><img src={BoominBeatsLogo} alt="" width="36" height="36" /> Boomin Beats</div>
		<div class="dots" aria-label="Step {$onboarding} of 3">
			{#each [1, 2, 3] as n}<span class:now={n === $onboarding} class:done={n <= ($onboarding ?? 0)} />{/each}
		</div>

		{#if $onboarding === 1}
			<section class="step">
				<h1>Your music, with a DJ that listens.</h1>
				<p class="lede">Boomin Beats reads your Spotify listening to find songs, build playlists and run the music at a party.</p>
				<button class="btn white cta" on:click={connectSpotify} disabled={connecting}>
					{#if connecting}<span class="spinner" aria-hidden="true" />{/if}
					{connecting ? 'Opening Spotify…' : 'Connect Spotify'}
				</button>
				<p class="fine">We read your top tracks and control playback on your devices. Nothing is posted to your account.</p>
			</section>
		{:else if $onboarding === 2}
			<section class="step narrow">
				<h1 class="smaller">Pick an AI for the smart parts.</h1>
				<p class="lede">It writes song analysis, builds playlists and suggests DJ moves. You can change it later in Settings.</p>
				{#if $access_token}
					<AiForm large canDisconnect={false} onConnected={() => ($onboarding = 3)}>
						<button slot="after" class="btn skip" on:click={() => ($onboarding = 3)}>Skip for now</button>
					</AiForm>
					<p class="fine">Without an AI, search, tags, your profile and the DJ's queue still work.</p>
				{:else}
					<!-- Back from Spotify: the Profile page is finishing the sign-in. -->
					<p class="fine" role="status"><span class="spinner light" aria-hidden="true" /> Finishing sign-in… <button class="link" on:click={() => ($onboarding = 1)}>Start over</button></p>
				{/if}
			</section>
		{:else}
			<section class="step wide">
				<h1 class="smaller">Where do you want to start?</h1>
				<div class="starts">
					{#each STARTS as s}
						<button class="start glass" on:click={() => start(s.href)}>
							<span class="start-icon"><Icon name={s.icon} size={20} /></span>
							<span class="start-title">{s.title}</span>
							<span class="start-desc">{s.desc}</span>
						</button>
					{/each}
				</div>
			</section>
		{/if}
	</div>
</div>

<style>
	.ob {
		position: fixed;
		inset: 0;
		z-index: 90;
		overflow-y: auto;
		overflow-x: hidden;
		background: var(--surface-0);
	}

	.inner {
		position: relative;
		z-index: 1;
		min-height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 28px;
		padding: 48px 20px;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: calc(17px * var(--text-scale, 1));
		font-weight: 600;
		letter-spacing: -0.01em;
	}

	.brand img {
		border-radius: 9px;
		object-fit: cover;
	}

	.dots {
		display: flex;
		gap: 6px;
	}

	.dots span {
		width: 6px;
		height: 6px;
		border-radius: 6px;
		background: rgba(255, 255, 255, 0.18);
		transition: background-color 0.3s var(--ease);
	}

	.dots .done {
		background: var(--accent);
	}

	.dots .now {
		width: 22px;
	}

	.step {
		width: min(560px, 100%);
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 18px;
		text-align: center;
		animation: bbin 0.4s var(--ease);
	}

	.narrow {
		width: min(500px, 100%);
		align-items: stretch;
	}

	.wide {
		width: min(820px, 100%);
		gap: 22px;
	}

	h1 {
		margin: 0;
		font-size: calc(clamp(40px, 8vw, 64px) * var(--text-scale, 1));
		font-weight: 700;
		line-height: 0.98;
		letter-spacing: -0.045em;
		text-wrap: balance;
	}

	h1.smaller {
		font-size: calc(clamp(34px, 6vw, 50px) * var(--text-scale, 1));
		line-height: 1;
		letter-spacing: -0.04em;
	}

	.lede {
		margin: 0 auto;
		max-width: 460px;
		font-size: calc(16px * var(--text-scale, 1));
		line-height: 1.55;
		color: rgba(243, 243, 245, 0.65);
		text-wrap: pretty;
	}

	.cta {
		height: 50px;
		padding: 0 24px;
		margin-top: 6px;
		border-radius: 999px;
		font-size: calc(15px * var(--text-scale, 1));
		gap: 10px;
	}

	.skip {
		border-color: rgba(255, 255, 255, 0.14);
	}

	.fine {
		margin: 0 auto;
		max-width: 380px;
		font-size: calc(12px * var(--text-scale, 1));
		line-height: 1.5;
		color: var(--text-subtle);
	}

	.starts {
		width: 100%;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 12px;
	}

	.start {
		display: flex;
		flex-direction: column;
		gap: 12px;
		padding: 20px;
		border-radius: 16px;
		color: var(--text-primary);
		font: inherit;
		text-align: left;
		white-space: normal;
		cursor: pointer;
		transition: border-color 0.15s, transform 0.2s var(--ease);
	}

	.start:hover {
		border-color: rgba(var(--accent-rgb), 0.45);
		transform: translateY(-3px);
	}

	.start-icon {
		width: 40px;
		height: 40px;
		display: grid;
		place-items: center;
		border-radius: 11px;
		background: rgba(var(--accent-rgb), 0.12);
		color: var(--accent);
	}

	.start-title {
		font-size: calc(17px * var(--text-scale, 1));
		font-weight: 600;
	}

	.start-desc {
		font-size: calc(13px * var(--text-scale, 1));
		line-height: 1.5;
		color: rgba(243, 243, 245, 0.6);
	}

	.link {
		padding: 0;
		border: none;
		background: none;
		color: var(--accent);
		font: inherit;
		cursor: pointer;
	}

	.fine .spinner {
		display: inline-block;
		vertical-align: -3px;
		margin-right: 6px;
	}

	.spinner.light {
		border-color: rgba(255, 255, 255, 0.2);
		border-top-color: var(--accent);
	}

	.spinner {
		width: 16px;
		height: 16px;
		border-radius: 50%;
		border: 2px solid rgba(0, 0, 0, 0.2);
		border-top-color: #0a0a0c;
		animation: bbspin 0.7s linear infinite;
	}
</style>
