<script>
	// The floating preview pill (F2): cover, title, time, progress, where the
	// sound goes, Queue it and Stop. Mounted once in the layout.
	import { page } from '$app/stores';
	import Icon from './Icon.svelte';
	import { preview, PREVIEW_SECONDS } from '$lib/preview.js';
	import { getDJ } from '$lib/dj/instance.js';
	import { queueTracks, rememberSongs } from '$lib/playlistActions.js';
	import { say } from '$lib/toast.js';

	const SPOTIFY_ID = /^[0-9A-Za-z]{22}$/;
	const MISS = { not_on_spotify: "That song isn't on Spotify.", explicit: 'Only an explicit version is on Spotify.', unavailable: "Couldn't add that right now." };

	let queueing = false;

	$: song = $preview?.song;
	$: pos = $preview?.pos ?? 0;

	// On the DJ page "Queue it" adds to Up next through the DJ engine; elsewhere it queues on Spotify.
	async function queue() {
		const song = $preview?.song;
		if (!song || queueing) return;
		queueing = true;
		try {
			const dj = getDJ();
			if ($page.url.pathname.startsWith('/dj') && dj) {
				if (SPOTIFY_ID.test(song.id)) {
					await dj.add({ id: song.id, title: song.title, artists: song.artists, image: song.image, isrc: song.isrc });
					say('Added to Up next.');
				} else {
					const r = await dj.addPick({ id: song.id, title: song.title, artists: song.artists, image: song.image, isrc: song.isrc });
					say(r.ok ? 'Added to Up next.' : MISS[r.reason]);
				}
			} else {
				// queueTracks resolves Deezer-keyed songs on Spotify first.
				rememberSongs([song]);
				say((await queueTracks([song.id])).message);
			}
		} catch {
			say("Couldn't add that right now.");
		} finally {
			queueing = false;
		}
	}
</script>

{#if song}
	<div class="pill" role="group" aria-label="Song preview">
		{#if song.image}<img class="cover" src={song.image} alt="" />{:else}<span class="cover" />{/if}
		<div class="info">
			<span class="title">{song.title}</span>
			<span class="meta mono">
				Preview · 0:{String(Math.floor(pos)).padStart(2, '0')} / 0:{PREVIEW_SECONDS}{#if $preview?.ducked}{' · Spotify lowered'}{/if}
			</span>
			<span class="bar" role="progressbar" aria-label="Preview progress" aria-valuemin={0} aria-valuemax={PREVIEW_SECONDS} aria-valuenow={Math.floor(pos)}>
				<span class="fill" style:transform="scaleX({pos / PREVIEW_SECONDS})" />
			</span>
		</div>
		<button class="btn primary small" on:click={queue} disabled={queueing}>Queue it</button>
		<button class="stop" on:click={() => preview.stop()} aria-label="Stop preview" title="Stop"><Icon name="stop" size={14} filled /></button>
	</div>
{/if}

<style>
	.pill {
		position: fixed;
		left: 0;
		right: 0;
		margin: 0 auto;
		bottom: calc(var(--mini-h, 0px) + var(--tab-h, 0px) + 72px);
		z-index: 60;
		display: flex;
		align-items: center;
		gap: 12px;
		box-sizing: border-box;
		width: min(480px, calc(100vw - 24px));
		padding: 8px 10px;
		border-radius: 16px;
		background: var(--glass);
		-webkit-backdrop-filter: var(--glass-blur);
		backdrop-filter: var(--glass-blur);
		border: 1px solid var(--accent-tint-border);
		box-shadow: var(--shadow-pop);
		animation: bbin 0.2s var(--ease);
	}

	.cover {
		flex: none;
		width: 40px;
		height: 40px;
		border-radius: 8px;
		object-fit: cover;
		background: var(--surface-2);
	}

	.info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: calc(14px * var(--text-scale, 1));
		font-weight: 500;
	}

	.meta {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: calc(11px * var(--text-scale, 1));
		color: var(--text-subtle);
	}

	.bar {
		height: 3px;
		margin-top: 3px;
		border-radius: 2px;
		background: rgba(255, 255, 255, 0.1);
		overflow: hidden;
	}

	.fill {
		display: block;
		height: 100%;
		width: 100%;
		background: var(--accent);
		transform-origin: left;
	}

	.stop {
		flex: none;
		width: 32px;
		height: 32px;
		display: grid;
		place-items: center;
		padding: 0;
		border: none;
		border-radius: 8px;
		background: none;
		color: var(--text-muted);
		cursor: pointer;
		transition: background-color var(--transition), color var(--transition);
	}

	.stop:hover {
		background: var(--hover);
		color: var(--text-primary);
	}
</style>
