"""Playback state and transport controls for the DJ companion (DJ1).

Thin, stateless wrappers over Spotify's /me/player endpoints. DJ0.2 measured the
Web API path as fast enough (~140 ms for player state) that the iOS SDK isn't
needed for now-playing.

Command routes answer 200 with {'error': ...} for expected player failures, the
same convention as /spotify/queue/, so clients can show a message rather than
treating "no device" as a crash.
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from spotipy import SpotifyException

from config import SYNC_ENABLED
from services.spotify_auth import get_spotify_token
from services.spotify_client import user_client

log = logging.getLogger(__name__)

router = APIRouter()


def _track(item: dict | None) -> dict | None:
    """Same shape as /get-profile/ tracks, so iOS decodes both with one model —
    except the image is the LARGEST size, since now-playing shows it big."""
    if not item or item.get('type') != 'track':
        return None
    album = item.get('album') or {}
    images = album.get('images') or []
    return {
        'id': item.get('id') or '',
        'title': item.get('name', ''),
        'artists': [a.get('name', '') for a in item.get('artists', [])],
        'image': images[0].get('url', '') if images else '',
        'album': album.get('name', ''),
        'duration_ms': item.get('duration_ms', 0),
        'explicit': item.get('explicit', False),
        'track_url': (item.get('external_urls') or {}).get('spotify', ''),
        'release_date': album.get('release_date', ''),
    }


def normalize_playback(p: dict | None) -> dict:
    """Spotify answers 204 (spotipy: None) when nothing is playing anywhere."""
    if not p:
        return {'active': False}
    device = p.get('device') or {}
    disallows = (p.get('actions') or {}).get('disallows') or {}
    return {
        'active': True,
        'is_playing': p.get('is_playing', False),
        'progress_ms': p.get('progress_ms') or 0,
        # Spotify's server time for progress_ms — lets the client interpolate.
        'timestamp': p.get('timestamp', 0),
        'shuffle': p.get('shuffle_state', False),
        # Smart Shuffle inserts recommendations mid-queue, which would look like
        # guest requests to DJ5's insertion rule; the client turns that rule off.
        'smart_shuffle': p.get('smart_shuffle', False),
        'repeat': p.get('repeat_state', 'off'),
        'device': {'name': device.get('name', ''), 'type': device.get('type', '')},
        'context_uri': (p.get('context') or {}).get('uri'),
        # Podcasts/ads have no track item; the client shows a neutral state.
        'track': _track(p.get('item')),
        'disallows': sorted(k for k, v in disallows.items() if v),
    }


def player_error(e: SpotifyException) -> dict:
    """Map an expected player failure to a client-facing error code.

    Branch on status, not message text — see the note in queue_songs. A 403 is
    NOT always Premium: Spotify also uses it for restriction violations (e.g.
    previous on the first track), distinguished by `reason`.
    """
    if e.http_status == 401:
        # Expired token: the client should refresh and retry, not see a server fault.
        raise HTTPException(status_code=401, detail='Spotify session expired. Log in again.')
    if e.http_status == 404:
        return {'error': 'no_active_device'}
    if e.http_status == 403:
        if (e.reason or '').upper() == 'PREMIUM_REQUIRED':
            return {'error': 'premium_required'}
        return {'error': 'restricted', 'reason': e.reason}
    raise HTTPException(status_code=500, detail=str(e))


@router.get('/player/state/')
def player_state(
    token: str = Depends(get_spotify_token),
    x_dj_device: str | None = Header(default=None, max_length=64),
):
    try:
        playback = user_client(token).current_playback()
    except SpotifyException as e:
        return player_error(e)
    state = normalize_playback(playback)
    if x_dj_device and SYNC_ENABLED:
        state['dj'] = dj_status(token, x_dj_device)
    return state


def dj_status(token: str, device: str) -> dict | None:
    """Sync piggyback (SY1): clients already poll this every ~2s, so it carries
    the shared state's version and who's driving, and doubles as the primary's
    heartbeat. No extra calls per poll. Best effort: a sync failure must never
    break player state, so it degrades to None."""
    from routers.dj_state import get_store
    from services.dj_store import Unavailable, heartbeat_due, primary_info
    from services.spotify_identity import user_id
    try:
        user = user_id(token)
        store = get_store()
        row = store.read(user)
        if row is None:
            return {'version': 0, 'primary': None}
        if heartbeat_due(row, device):
            store.heartbeat(user, device)
        return {'version': row['version'], 'primary': primary_info(row)}
    except (Unavailable, HTTPException) as e:
        log.info('[player] dj status unavailable: %s', e)
        return None


@router.get('/player/queue/')
def player_queue(token: str = Depends(get_spotify_token)):
    try:
        q = user_client(token).queue() or {}
    except SpotifyException as e:
        return player_error(e)
    return {'queue': [t for t in map(_track, q.get('queue') or []) if t]}


def _command(token: str, action: str) -> dict:
    spotify = user_client(token)
    fn = {
        'play': spotify.start_playback,
        'pause': spotify.pause_playback,
        'next': spotify.next_track,
        'previous': spotify.previous_track,
    }[action]
    try:
        fn()
    except SpotifyException as e:
        log.info('[player] %s failed: %s', action, e)
        return player_error(e)
    return {'ok': True}


@router.post('/player/play/')
def play(token: str = Depends(get_spotify_token)):
    return _command(token, 'play')


@router.post('/player/pause/')
def pause(token: str = Depends(get_spotify_token)):
    return _command(token, 'pause')


@router.post('/player/next/')
def next_track(token: str = Depends(get_spotify_token)):
    return _command(token, 'next')


@router.post('/player/previous/')
def previous_track(token: str = Depends(get_spotify_token)):
    return _command(token, 'previous')
