import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from spotipy import Spotify, SpotifyException

from routers.player import player_error
from services.spotify_auth import get_spotify_token
from services.spotify_client import user_client

log = logging.getLogger(__name__)

router = APIRouter()


class CreatePlaylistRequest(BaseModel):
    name: str
    track_ids: list[str]


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
    playlist = spotify._post("me/playlists", payload={"name": body.name, "public": False, "description": "Created by Boomin Beats"})
    if body.track_ids:
        spotify.playlist_add_items(playlist['id'], body.track_ids)
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


@router.get("/spotify/recently-played/")
def recently_played(token: str = Depends(get_spotify_token)):
    """Return play timestamps for the listening clock. Spotify caps this at the
    50 most-recent plays. Needs the user-read-recently-played scope."""
    spotify = user_client(token)
    try:
        res = spotify.current_user_recently_played(limit=50)
    except SpotifyException as e:
        if e.http_status in (401, 403):
            raise HTTPException(status_code=403, detail="reconnect")
        raise HTTPException(status_code=500, detail=str(e))
    played_at = [it['played_at'] for it in res.get('items', []) if it.get('played_at')]
    return {'played_at': played_at, 'count': len(played_at)}


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
