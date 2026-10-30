import asyncio
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, StringConstraints
from spotipy import Spotify, SpotifyException

from routers.player import _track, player_error
from services.spotify_auth import get_spotify_token
from services.spotify_client import user_client
from services import churn, history_store, library, spotify_identity, track_cache

log = logging.getLogger(__name__)

router = APIRouter()


class CreatePlaylistRequest(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    track_ids: list[str] = Field(default=[], max_length=500)
    # Spotify's limit is 300 characters (F3f: tonight's set's recap).
    description: Annotated[str, StringConstraints(max_length=300)] = ''


class QueueRequest(BaseModel):
    track_ids: list[str]


class AddToPlaylistRequest(BaseModel):
    playlist_id: str
    track_ids: list[str]


class SaveTrackRequest(BaseModel):
    track_ids: list[str]
    remove: bool = False


@router.post("/spotify/create-playlist/")
def create_playlist(body: CreatePlaylistRequest, token: str = Depends(get_spotify_token)):
    spotify = user_client(token)
    description = body.description.strip() or "Created by Boomin Beats"
    playlist = spotify._post("me/playlists", payload={"name": body.name, "public": False, "description": description})
    # Spotify takes at most 100 tracks per add.
    for i in range(0, len(body.track_ids), 100):
        spotify.playlist_add_items(playlist['id'], body.track_ids[i:i + 100])
    return {
        'playlist_url': playlist['external_urls']['spotify'],
        'playlist_id': playlist['id'],
    }


@router.get("/spotify/playlists/")
def list_playlists(token: str = Depends(get_spotify_token)):
    """List the user's editable playlists (owned or collaborative)."""
    spotify = user_client(token)
    me_id = spotify.me()['id']

    playlists = []
    offset = 0
    while True:
        page = spotify.current_user_playlists(limit=50, offset=offset)
        items = page.get('items', [])
        for p in items:
            if p is None:
                continue
            owned = p.get('owner', {}).get('id') == me_id
            if not (owned or p.get('collaborative')):
                continue
            images = p.get('images') or []
            # Spotify's /me/playlists returns the track ref under "items" (newer)
            # or "tracks" (older) — both are {href, total}.
            tracks_ref = p.get('items') or p.get('tracks') or {}
            track_count = tracks_ref.get('total', 0) if isinstance(tracks_ref, dict) else 0
            playlists.append({
                'id': p['id'],
                'name': p['name'],
                'image': images[0]['url'] if images else '',
                'track_count': track_count,
            })
        if page.get('next'):
            offset += 50
        else:
            break

    return {'playlists': playlists}


# A DJ set from a playlist doesn't need more than this (F3h).
PLAYLIST_TRACKS_MAX = 300


def playlist_tracks_from(spotify: Spotify, playlist_id: str, limit: int = PLAYLIST_TRACKS_MAX) -> list[dict]:
    """A playlist's songs, in order. The newer API answers /items with each
    entry's track under "item"; the older one used /tracks and "track"."""
    tracks, offset = [], 0
    while len(tracks) < limit:
        page = spotify._get(f"playlists/{playlist_id}/items", limit=50, offset=offset)
        for entry in page.get('items', []):
            t = _track((entry or {}).get('item') or (entry or {}).get('track'))
            # Local files have no Spotify id and can't be queued.
            if t and t['id']:
                tracks.append(t)
        if not page.get('next'):
            break
        offset += 50
    return tracks[:limit]


@router.get("/spotify/playlist-tracks/")
def playlist_tracks(
    playlist_id: Annotated[str, StringConstraints(pattern=r'^[A-Za-z0-9]{1,64}$')],
    token: str = Depends(get_spotify_token),
):
    return {'tracks': playlist_tracks_from(user_client(token), playlist_id)}


@router.post("/spotify/add-to-playlist/")
def add_to_playlist(body: AddToPlaylistRequest, token: str = Depends(get_spotify_token)):
    if not body.track_ids:
        return {'added': 0}
    spotify = user_client(token)
    spotify.playlist_add_items(body.playlist_id, body.track_ids)
    return {
        'added': len(body.track_ids),
        'playlist_url': f'https://open.spotify.com/playlist/{body.playlist_id}',
    }


@router.get("/spotify/top-tracks/")
def top_tracks(
    limit: int = Query(default=12),
    time_range: str = Query(default='medium_term'),
    token: str = Depends(get_spotify_token),
):
    spotify = user_client(token)
    result = spotify.current_user_top_tracks(limit=limit, time_range=time_range)
    tracks = []
    for t in result.get('items', []):
        images = t['album']['images']
        image = images[-1]['url'] if images else ''
        tracks.append({
            'title': t['name'],
            'artists': [a['name'] for a in t['artists']],
            'id': t['id'],
            'image': image,
        })
    return {'tracks': tracks}


_churn_cache: dict[str, tuple[float, dict]] = {}
_CHURN_TTL = 600


def _top(spotify: Spotify, kind: str, rng: str) -> list[dict]:
    if kind == 'artists':
        items = spotify.current_user_top_artists(limit=50, time_range=rng).get('items', [])
        return [{'id': a['id'], 'name': a.get('name', ''), 'image': ((a.get('images') or [{}])[-1]).get('url', '')} for a in items if a.get('id')]
    items = spotify.current_user_top_tracks(limit=50, time_range=rng).get('items', [])
    out = []
    for t in items:
        if not t.get('id'):
            continue
        images = (t.get('album') or {}).get('images') or []
        out.append({'id': t['id'], 'title': t.get('name', ''), 'artists': [a.get('name', '') for a in t.get('artists', [])],
                    'image': images[-1]['url'] if images else ''})
    return out


@router.get("/spotify/top-churn/")
async def top_churn(token: str = Depends(get_spotify_token)):
    """What's new vs what's a staple: top artists and tracks compared across the
    three time ranges (services/churn.py). Six top-item calls, no search; cached
    10 minutes per user since Profile loads it on every visit."""
    key = hashlib.sha256(token.encode()).hexdigest()
    hit = _churn_cache.get(key)
    if hit and time.monotonic() - hit[0] < _CHURN_TTL:
        return hit[1]
    spotify = user_client(token)
    ranges = ('short_term', 'medium_term', 'long_term')
    try:
        tops = await asyncio.gather(*(asyncio.to_thread(_top, spotify, kind, rng) for kind in ('artists', 'tracks') for rng in ranges))
    except SpotifyException as e:
        raise HTTPException(status_code=403 if e.http_status in (401, 403) else 502, detail='reconnect' if e.http_status in (401, 403) else "Couldn't reach Spotify.")
    result = {'artists': churn.compare(*tops[:3]), 'tracks': churn.compare(*tops[3:])}
    if len(_churn_cache) >= 256:
        _churn_cache.clear()
    _churn_cache[key] = (time.monotonic(), result)
    return result


@router.get("/spotify/library-stats/")
async def library_stats(token: str = Depends(get_spotify_token)):
    """Liked Songs and playlist stats for Profile (services/library.py). One request
    checks Liked Songs for changes; a full scan runs only when it changed."""
    spotify = user_client(token)
    try:
        me, first = await asyncio.gather(
            asyncio.to_thread(spotify_identity.user_id, token),
            asyncio.to_thread(spotify.current_user_saved_tracks, limit=50, offset=0),
        )
        total = first.get('total', 0)
        newest = (first.get('items') or [{}])[0].get('added_at')
        key = track_cache.key('library', me)
        cached = (await asyncio.to_thread(track_cache.get_many, [key])).get(key)
        if cached and cached.get('total') == total and cached.get('newest') == newest:
            liked = cached
        else:
            gate = asyncio.Semaphore(6)

            async def page(offset):
                async with gate:
                    return (await asyncio.to_thread(spotify.current_user_saved_tracks, limit=50, offset=offset)).get('items', [])

            rest = await asyncio.gather(*(page(o) for o in range(50, min(total, library.MAX_SONGS), 50)))
            items = [*first.get('items', []), *(it for p in rest for it in p)]
            liked = library.summarize(items, total)
            await asyncio.to_thread(track_cache.put_many, {key: liked})
        playlists, offset = [], 0
        while True:
            pl = await asyncio.to_thread(spotify.current_user_playlists, limit=50, offset=offset)
            playlists += pl.get('items', [])
            if not pl.get('next') or offset > 1000:
                break
            offset += 50
    except SpotifyException as e:
        if e.http_status in (401, 403):
            raise HTTPException(status_code=403, detail='reconnect')
        raise HTTPException(status_code=502, detail="Couldn't reach Spotify.")
    return {'liked': liked, 'playlists': library.playlist_stats(playlists, me)}


@router.get("/spotify/taste-over-time/")
def taste_over_time(token: str = Depends(get_spotify_token)):
    """Aggregate listening metrics across the three timeframes. Uses cheap
    Spotify-native data (popularity, release year) and tries audio-features
    (deprecated for new apps) — degrading to audio_features=None if unavailable."""
    spotify = user_client(token)

    ranges = [('short_term', '1 Month'), ('medium_term', '6 Months'), ('long_term', 'All Time')]
    af_dims = {'Energy': 'energy', 'Danceability': 'danceability', 'Positivity': 'valence', 'Acousticness': 'acousticness'}

    timeframes, release_year, avg_duration_ms, explicit_pct = [], [], [], []
    audio = {k: [] for k in af_dims}
    audio_available = True

    for rng, label in ranges:
        timeframes.append(label)
        tracks = spotify.current_user_top_tracks(limit=20, time_range=rng).get('items', [])

        years, durations, expl = [], [], 0
        for t in tracks:
            rd = t.get('album', {}).get('release_date', '') or ''
            if rd[:4].isdigit():
                years.append(int(rd[:4]))
            if t.get('duration_ms'):
                durations.append(t['duration_ms'])
            if t.get('explicit'):
                expl += 1
        release_year.append(round(sum(years) / len(years)) if years else 0)
        avg_duration_ms.append(round(sum(durations) / len(durations)) if durations else 0)
        explicit_pct.append(round(100 * expl / len(tracks)) if tracks else 0)

        # Audio features are deprecated for apps created after 2024-11-27; this
        # degrades to audio_features=None when unavailable.
        if audio_available:
            try:
                ids = [t['id'] for t in tracks if t.get('id')]
                feats = [f for f in (spotify.audio_features(ids) if ids else []) if f]
                if feats:
                    for k, sk in af_dims.items():
                        vals = [f[sk] for f in feats if sk in f]
                        audio[k].append(round(100 * sum(vals) / len(vals)) if vals else 0)
                else:
                    audio_available = False
            except Exception:
                audio_available = False

    return {
        'timeframes': timeframes,
        'release_year': release_year,
        'avg_duration_ms': avg_duration_ms,
        'explicit_pct': explicit_pct,
        'audio_features': audio if audio_available else None,
    }


def _recent_items(token: str) -> list[dict]:
    try:
        return user_client(token).current_user_recently_played(limit=50).get('items', [])
    except SpotifyException as e:
        if e.http_status in (401, 403):
            raise HTTPException(status_code=403, detail="reconnect")
        raise HTTPException(status_code=500, detail=str(e))


def _store_recent(token: str, items: list[dict]) -> str | None:
    """Keep these plays in the listening history; returns the user id, or None if storage is off."""
    try:
        user = spotify_identity.user_id(token)
        history_store.save(history_store.rows_from_recent(user, items))
        return user
    except (history_store.Unavailable, HTTPException) as e:
        log.info('[history] not stored: %s', e)
        return None


@router.get("/spotify/recently-played/")
def recently_played(tz: int = Query(default=0, ge=-840, le=840), token: str = Depends(get_spotify_token)):
    """Play timestamps for the listening clock. Spotify only keeps the 50 most
    recent, so they're also saved to the listening history, and `history` holds
    stats over the last 90 days of saved plays (in the caller's time zone: `tz`
    is JavaScript's getTimezoneOffset()). Needs user-read-recently-played."""
    items = _recent_items(token)
    played_at = [it['played_at'] for it in items if it.get('played_at')]
    history = None
    user = _store_recent(token, items)
    if user:
        try:
            since = datetime.now(timezone.utc) - timedelta(days=history_store.WINDOW_DAYS)
            history = history_store.stats(history_store.plays_since(user, since), tz)
        except history_store.Unavailable as e:
            log.info('[history] not read: %s', e)
    return {'played_at': played_at, 'count': len(played_at), 'history': history}


@router.post("/history/sync/")
def sync_history(token: str = Depends(get_spotify_token)):
    """Save the latest plays (the DJ page calls this while open), so history has no gaps."""
    items = _recent_items(token)
    return {'stored': _store_recent(token, items) is not None, 'seen': len(items)}


# Spotify's February 2026 migration consolidated the per-type save/remove/contains
# endpoints into PUT/DELETE /me/library and GET /me/library/contains, all keyed by
# Spotify URIs rather than bare ids. spotipy >= 2.26 already targets the new
# endpoints, so use its helpers — do NOT "fix" them back to /me/tracks/*, which
# the migration removed (those now return 403).
# The /me/library endpoints cap how many URIs one request may carry, and the cap
# is lower than the 50 the pre-migration /me/tracks endpoints allowed — 50 comes
# back as "400 Too many uris requested". The exact ceiling isn't documented, so
# start conservatively and halve on rejection rather than hard-coding a guess.
_SAVED_TRACKS_LIMIT = 20


def _id_chunks(ids: list[str], size: int):
    for i in range(0, len(ids), size):
        yield ids[i:i + size]


def _too_many_uris(e: SpotifyException) -> bool:
    return e.http_status == 400 and 'too many' in str(e).lower()


def _batched(ids: list[str], fn, size: int = _SAVED_TRACKS_LIMIT) -> list:
    """Apply fn to ids in chunks, halving on "too many uris" and remembering the
    smaller size for the remaining chunks so the cap is discovered once, not
    per chunk. Returns concatenated results (empty for writes, which return None).
    """
    out: list = []
    i = 0
    while i < len(ids):
        chunk = ids[i:i + size]
        try:
            result = fn(chunk)
        except SpotifyException as e:
            if not _too_many_uris(e) or len(chunk) == 1:
                raise
            size = max(1, len(chunk) // 2)
            log.warning('[spotify] batch rejected as too many uris; retrying at %d', size)
            continue  # same offset, smaller chunk
        if result:
            out.extend(result)
        i += len(chunk)
    return out


def _saved_tracks_contains(spotify: Spotify, ids: list[str]) -> list[bool]:
    return _batched(ids, lambda c: spotify.current_user_saved_tracks_contains(tracks=c))


def _saved_tracks_modify(spotify: Spotify, ids: list[str], remove: bool) -> None:
    call = (spotify.current_user_saved_tracks_delete if remove
            else spotify.current_user_saved_tracks_add)
    _batched(ids, lambda c: call(tracks=c))


@router.post("/spotify/save-track/")
def save_track(body: SaveTrackRequest, token: str = Depends(get_spotify_token)):
    if not body.track_ids:
        return {'ok': True, 'saved': not body.remove}
    spotify = user_client(token)
    try:
        _saved_tracks_modify(spotify, body.track_ids, body.remove)
    except SpotifyException as e:
        if e.http_status in (401, 403):
            raise HTTPException(status_code=403, detail="reconnect")
        raise HTTPException(status_code=500, detail=str(e))
    return {'ok': True, 'saved': not body.remove}


@router.get("/spotify/saved-contains/")
def saved_contains(ids: str = Query(default=""), token: str = Depends(get_spotify_token)):
    id_list = [i for i in ids.split(',') if i]
    if not id_list:
        return {'saved': {}}
    spotify = user_client(token)
    try:
        flags = _saved_tracks_contains(spotify, id_list)
    except SpotifyException as e:
        if e.http_status in (401, 403):
            raise HTTPException(status_code=403, detail="reconnect")
        raise HTTPException(status_code=500, detail=str(e))
    return {'saved': dict(zip(id_list, flags))}


@router.post("/spotify/queue/")
def queue_songs(body: QueueRequest, token: str = Depends(get_spotify_token)):
    spotify = user_client(token)
    queued = 0
    for track_id in body.track_ids:
        try:
            spotify.add_to_queue(f'spotify:track:{track_id}')
        except SpotifyException as e:
            # The player endpoints report device problems as 404 with an
            # inconsistent message — "Player command failed: No active device
            # found" on one call, a bare "Not found." on the next. Branch on the
            # status, not the text; string matching missed the second phrasing
            # and surfaced it as a 500.
            # A 403 is not always Premium — player_error tells them apart by reason.
            log.info('[spotify] queue stopped after %d: %s', queued, e)
            return {**player_error(e), 'queued': queued}
        queued += 1
    return {'queued': queued}
