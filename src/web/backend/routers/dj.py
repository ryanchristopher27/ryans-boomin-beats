"""Move suggestions for the DJ companion (DJ3).

A "move" is a decision about where the set goes next; songs fill it in. Stateless
like the rest of the backend: the client sends the whole context (now playing,
recent history, its upcoming queue) on every call.

Spotify's recommendations and audio-features endpoints are dead on this client
ID (DJ0 / V1 audits), so the vibe signal is Last.fm tags + the model's own ear.
"""
import asyncio
import json
import logging
import re
from typing import Annotated

import requests
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, StringConstraints
from spotipy import SpotifyException

from services import lastfm_client
from services.llm_auth import LLMCredentials, get_llm_credentials
from services.llm_client import LLMClient
from services.llm_json import LLMParseError, extract_json
from services.spotify_auth import get_spotify_token
from services.spotify_client import user_client
from services.spotify_validator import validate_songs

log = logging.getLogger(__name__)

router = APIRouter()

# Order is the display order. Bridge needs a destination, so it arrives with DJ6.
MOVES = {
    'hold': 'Same energy, tempo feel and era/scene as now playing. Keep the vibe going.',
    'lift': 'Noticeably MORE energy than now playing, but a coherent next step, not a jarring jump.',
    'drop': 'LOWER energy to give the room a breather, while keeping the mood.',
    'pivot': 'A DIFFERENT genre that keeps one clear thread (mood, groove, era or lyrical theme). Name the thread in the reason.',
    'curveball': 'Unexpected but it works: a deep cut, a cross-genre surprise, or an older/newer gem that still fits.',
}

SYSTEM_PROMPT = """You are a skilled party DJ helping a host pick what plays next. You suggest songs, the host decides.

Respond ONLY with a JSON object, no prose and no code fences. Keys are move names; each value is an array of objects with exactly three string fields: "title", "artist" (primary artist), "reason" (one short sentence a host would find useful).

Rules:
- Only real songs that are on Spotify.
- Never suggest a song from the "already played" or "already queued" lists, or the song now playing.
- Avoid the most obvious mainstream picks unless they are genuinely the best fit; a good DJ digs a little.
- Each song appears under one move only."""

# Ask for extras per move so validation drops don't leave a move short. Two,
# not one: at reasoning_effort=low only ~11-13 of 15 picks matched on Spotify
# and Curveball came back empty (DJ4 result).
_OVERASK = 2


# Bounds at the trust boundary: everything here lands in an LLM prompt billed to
# the user's own key, so a client can't be allowed to inflate it without limit.
_Text = Annotated[str, StringConstraints(max_length=300)]
_MAX_REFS = 50


class TrackRef(BaseModel):
    id: Annotated[str, StringConstraints(max_length=64)] = ''
    title: _Text
    artist: _Text


def _refs():
    return Field(default=[], max_length=_MAX_REFS)


class SuggestRequest(BaseModel):
    now_playing: TrackRef
    recent: list[TrackRef] = _refs()
    upcoming: list[TrackRef] = _refs()
    per_move: int = Field(default=2, ge=1, le=3)
    # DJ4 controls. All optional, so a DJ3 client keeps working.
    adventurousness: float = Field(default=0.5, ge=0, le=1)
    clean: bool = False
    liked: list[TrackRef] = _refs()
    disliked: list[TrackRef] = _refs()
    skipped: list[TrackRef] = _refs()
    avoid_tracks: list[TrackRef] = _refs()
    avoid_artists: list[_Text] = _refs()


def _adventure_line(a: float) -> str:
    if a < 0.34:
        return 'Play it SAFE: well-loved songs close to what is playing. Even Pivot and Curveball should be crowd-pleasers.'
    if a < 0.67:
        return 'Balance familiar picks with a few discoveries.'
    return ('Be BOLD: favour deep cuts, lesser-known artists and adventurous Pivots and Curveballs. '
            'Skip anything a casual listener would already expect.')


def build_prompt(body: SuggestRequest, tags: list[str]) -> str:
    def lines(refs: list[TrackRef]) -> str:
        return '\n'.join(f'- {r.title} — {r.artist}' for r in refs) or '- (none)'

    moves = '\n'.join(f'- "{name}": {desc}' for name, desc in MOVES.items())
    tag_line = ', '.join(tags) if tags else '(no tags available)'
    # The clean filter drops explicit tracks after validation (DJ4: one extra left
    # whole moves empty), so ask for more when it's on.
    n = body.per_move + _OVERASK + (1 if body.clean else 0)
    return (
        f'Now playing: {body.now_playing.title} — {body.now_playing.artist}\n'
        f'Last.fm tags for it: {tag_line}\n\n'
        f'Already played, most recent first (this is the night so far; use it to read the room):\n{lines(body.recent)}\n\n'
        f'Already queued (do not suggest these):\n{lines(body.upcoming)}\n\n'
        + (f'The host wants MORE like:\n{lines(body.liked)}\n\n' if body.liked else '')
        + (f'The host wants LESS like (avoid this direction):\n{lines(body.disliked)}\n\n' if body.disliked else '')
        + (f'The host skipped these early (a sign they did not land):\n{lines(body.skipped)}\n\n' if body.skipped else '')
        + (f'Never suggest these artists: {", ".join(body.avoid_artists)}\n\n' if body.avoid_artists else '')
        + ('Clean versions only: no explicit songs.\n\n' if body.clean else '')
        + f'{_adventure_line(body.adventurousness)}\n\n'
        + f'Give {n} songs for each of these moves:\n{moves}'
    )


def normalize_moves(data) -> dict[str, list[dict]]:
    """Coerce the parsed model output into {move: [{title, artist, reason}]},
    keeping only known moves and well-formed entries."""
    if not isinstance(data, dict):
        return {}
    out = {}
    for move in MOVES:
        entries = data.get(move)
        if not isinstance(entries, list):
            continue
        cleaned = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            title = str(e.get('title', '')).strip()
            artist = str(e.get('artist', '')).strip()
            if title and artist:
                cleaned.append({'title': title, 'artist': artist, 'reason': str(e.get('reason', '')).strip()})
        if cleaned:
            out[move] = cleaned
    return out


# Groq's on-demand tier (8k tokens/min) was observed cutting replies off
# mid-string once the minute's budget was nearly spent (DJ4 result): 1,411 of
# ~2,400 chars, while the same prompt minutes later completed.
_CUT_OFF = "The AI's reply was cut off, usually the provider's per-minute limit. Try again in a minute."


def salvage_truncated(raw: str) -> dict | None:
    """Recover the complete entries from a {move: [entry, ...]} reply that was
    cut off mid-entry, by closing it after the last complete entry."""
    start = raw.find('{')
    if start < 0:
        return None
    depth, in_string, escaped, last_entry_end = 0, False, False, None
    for i in range(start, len(raw)):
        ch = raw[i]
        if escaped:
            escaped = False
        elif ch == '\\':
            escaped = in_string
        elif ch == '"':
            in_string = not in_string
        elif not in_string:
            if ch in '{[':
                depth += 1
            elif ch in '}]':
                depth -= 1
                # Depth 2 = back inside a move's array: an entry just closed.
                if ch == '}' and depth == 2:
                    last_entry_end = i
    if last_entry_end is None:
        return None
    try:
        return json.loads(raw[start:last_entry_end + 1] + ']}')
    except json.JSONDecodeError:
        return None


def _artist_matches(suggested: str, spotify_artists: list[str]) -> bool:
    """validate_songs falls back to a title-only search, which can land on a
    different artist's song of the same name. For a DJ that's a wrong track,
    so require the suggested artist to appear among the matched artists."""
    s = _fold(suggested)
    return bool(s) and any(s in _fold(a) or _fold(a) in s for a in spotify_artists if _fold(a))


def _fold(name: str) -> str:
    """'Tyler, The Creator' and 'tyler the creator' compare equal."""
    return re.sub(r'[^0-9a-z]', '', name.casefold())


def select_tracks(
    moves: dict[str, list[dict]],
    matched: list[dict],
    exclude_ids: set[str],
    per_move: int,
    avoid_artists: list[str] = (),
    clean: bool = False,
) -> list[dict]:
    """Attach validated Spotify tracks to their moves, dropping wrong-artist
    matches, excluded tracks, do-not-play artists, explicit tracks when clean,
    and duplicates across moves. The prompt asks for all of this too; these
    filters are the guarantee."""
    by_key = {(m['title'], m['artist']): m for m in matched}
    seen = set(exclude_ids)
    avoid = {_fold(a) for a in avoid_artists if _fold(a)}
    result = []
    for move, entries in moves.items():
        tracks = []
        for e in entries:
            m = by_key.get((e['title'], e['artist']))
            if not m:
                continue
            sp = m['spotify']
            if sp['id'] in seen or not _artist_matches(e['artist'], sp['artists']):
                continue
            if clean and sp.get('explicit'):
                continue
            if any(_fold(a) in avoid for a in sp['artists']):
                continue
            seen.add(sp['id'])
            tracks.append({
                'id': sp['id'],
                'title': sp['title'],
                'artists': sp['artists'],
                'image': sp['image'],
                'reason': e['reason'],
            })
            if len(tracks) == per_move:
                break
        if tracks:
            result.append({'move': move, 'tracks': tracks})
    return result


def _spotify_recent(token: str, limit: int = 20) -> list[TrackRef]:
    """The user's last plays from Spotify, so history survives an app relaunch
    (the client only remembers what it saw this session). Best effort."""
    try:
        items = user_client(token).current_user_recently_played(limit=limit).get('items', [])
    # requests' Timeout/ConnectionError don't subclass the builtins (review W1).
    except (SpotifyException, requests.exceptions.RequestException, TimeoutError, ConnectionError) as e:
        log.info('[dj] recently-played unavailable: %s', e)
        return []
    refs = []
    for it in items:
        t = it.get('track') or {}
        if t.get('id') and t.get('artists'):
            refs.append(TrackRef(id=t['id'], title=t.get('name', ''), artist=t['artists'][0].get('name', '')))
    return refs


def merge_recent(session: list[TrackRef], spotify: list[TrackRef], cap: int = 15) -> list[TrackRef]:
    """Session history first (it's fresher), then Spotify's, deduped by id."""
    seen, out = set(), []
    for r in [*session, *spotify]:
        key = r.id or (r.title, r.artist)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out[:cap]


@router.post('/dj/suggest/')
async def suggest(
    body: SuggestRequest,
    creds: LLMCredentials = Depends(get_llm_credentials),
    token: str = Depends(get_spotify_token),
):
    info, spotify_recent = await asyncio.gather(
        lastfm_client.track_info(body.now_playing.title, body.now_playing.artist),
        asyncio.to_thread(_spotify_recent, token),
    )
    tags = [t['name'] for t in info['tags'][:8]]
    # Everything played recently is excluded below, but only the head goes in the prompt.
    all_recent = merge_recent(body.recent, spotify_recent, cap=50)
    body.recent = all_recent[:15]

    client = LLMClient(provider=creds.provider, api_key=creds.api_key)
    try:
        raw = await client.generate([{'role': 'user', 'content': build_prompt(body, tags)}], SYSTEM_PROMPT)
    except Exception as e:
        log.warning('[dj] %s request failed: %s', creds.provider, e)
        return {'moves': [], 'tags': tags, 'error': f'{creds.provider} request failed: {e}'}

    try:
        moves = normalize_moves(extract_json(raw, context='dj'))
    except LLMParseError as e:
        moves = normalize_moves(salvage_truncated(e.raw))
        log.warning('[dj] parse failed (%d chars); salvaged %d moves', len(e.raw), len(moves))
        if not moves:
            return {'moves': [], 'tags': tags, 'error': _CUT_OFF}

    flat = [e for entries in moves.values() for e in entries]
    # No title-only fallback: select_tracks drops other artists' songs anyway.
    matched, _ = await validate_songs(flat, fallback=False)

    exclude = {r.id for r in [body.now_playing, *all_recent, *body.upcoming, *body.avoid_tracks] if r.id}
    result = select_tracks(moves, matched, exclude, body.per_move, body.avoid_artists, body.clean)
    return {
        'moves': result,
        'tags': tags,
        'error': None if result else 'No suggestions could be matched on Spotify.',
    }
