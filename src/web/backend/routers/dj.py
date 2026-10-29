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
from typing import Annotated, Literal

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints
from spotipy import SpotifyException

from services import lastfm_client
from services.llm_auth import LLMCredentials, get_optional_llm_credentials
from services.llm_client import NeedsLLM
from services.claude_code import ClaudeCodeError
from services.llm_json import LLMParseError, extract_json
from services.spotify_auth import get_spotify_token
from services.spotify_client import user_client
from services import deezer

log = logging.getLogger(__name__)

router = APIRouter()

# Order is the display order. A goal (DJ6) adds one more move in front.
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
    isrc: Annotated[str, StringConstraints(max_length=15)] | None = None
    title: _Text
    artist: _Text


def _refs():
    return Field(default=[], max_length=_MAX_REFS)


class Goal(BaseModel):
    """Optional steering (DJ6). Deliberately not a precomputed path: each
    suggestion round asks for the next *step* from what actually played."""
    kind: Literal['destination', 'arc', 'drift']
    destination: Annotated[str, StringConstraints(max_length=200)] = ''
    shape: Literal['build', 'wind_down', 'peak_cool'] = 'build'
    minutes: int = Field(default=30, ge=5, le=240)
    elapsed_minutes: float = Field(default=0, ge=0)


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
    goal: Goal | None = None
    # F3c: re-ask only these moves (a per-move refresh), say what was off about
    # their last picks, and keep those picks out of this round.
    only_moves: list[Annotated[str, StringConstraints(max_length=20)]] = Field(default=[], max_length=8)
    feedback: dict[Annotated[str, StringConstraints(max_length=20)], list[Annotated[str, StringConstraints(max_length=60)]]] = Field(default={}, max_length=8)
    exclude: list[TrackRef] = _refs()
    # F3d: how much to draw on the listener's own library (their top tracks).
    # None = no preference (older clients); 0 = from their library, 1 = all new.
    familiar: float | None = Field(default=None, ge=0, le=1)
    library: list[TrackRef] = _refs()


# Concrete markers, because a bare "step energy UP" was followed weakly at
# reasoning_effort='low' (DJ6 live check: Otis Redding offered as a build step).
_UP = ('step the energy UP from now playing: each song must have a clearly faster tempo, harder drums '
       'or more intense production than now playing. Say in the reason what makes it higher energy.')
_DOWN = ('step the energy DOWN from now playing: each song must have a clearly slower tempo, softer or '
         'sparser production than now playing. Say in the reason what makes it calmer.')
_HOLD_PEAK = ('hold peak energy: match the intensity of the most energetic songs played so far. Say in the '
              'reason what keeps it at the peak.')
_HOLD_LOW = 'keep it calm and low: slow tempos, soft or sparse production.'


def _arc_step(goal: Goal) -> str:
    """Where an energy arc stands right now, as an instruction for this step."""
    p = min(goal.elapsed_minutes / goal.minutes, 1.0)
    pct, m = round(p * 100), goal.minutes
    if goal.shape == 'build':
        if p >= 1:
            return f'The {m}-minute build has reached its peak: {_HOLD_PEAK}'
        return f'{pct}% through a {m}-minute build to a peak: {_UP}'
    if goal.shape == 'wind_down':
        if p >= 1:
            return f'The {m}-minute wind-down is done: {_HOLD_LOW}'
        return f'{pct}% through a {m}-minute wind-down: {_DOWN}'
    # peak_cool: rise to a peak at the midpoint, then come back down.
    if p < 0.5:
        return f'{pct}% through a {m}-minute peak-then-cool, still climbing to the peak at the halfway mark: {_UP}'
    if p >= 1:
        return f'The {m}-minute peak-then-cool has finished cooling: {_HOLD_LOW}'
    return f'{pct}% through a {m}-minute peak-then-cool, past the peak: {_DOWN}'


def goal_move(goal: Goal | None) -> tuple[str, str] | None:
    """The extra move a goal adds: (key, description for the prompt)."""
    if goal is None:
        return None
    if goal.kind == 'drift':
        return ('drift', 'One step somewhere NEW, away from where the night has been (see the already played list), '
                         'without a jarring jump. There is no destination; keep travelling.')
    if goal.kind == 'destination' and goal.destination.strip():
        return ('toward', f'One step closer to where the host wants to end up: "{goal.destination.strip()}". '
                          'Move part of the way there from now playing, not all at once.')
    if goal.kind == 'arc':
        return ('toward', _arc_step(goal))
    return None


def moves_for(goal: Goal | None) -> dict[str, str]:
    extra = goal_move(goal)
    return {extra[0]: extra[1], **MOVES} if extra else dict(MOVES)


def _adventure_line(a: float) -> str:
    if a < 0.34:
        return 'Play it SAFE: well-loved songs close to what is playing. Even Pivot and Curveball should be crowd-pleasers.'
    if a < 0.67:
        return 'Balance familiar picks with a few discoveries.'
    return ('Be BOLD: favour deep cuts, lesser-known artists and adventurous Pivots and Curveballs. '
            'Skip anything a casual listener would already expect.')


def familiar_line(body: SuggestRequest) -> str:
    """Familiar ↔ New (F3d): lean on the listener's library, or away from it."""
    if body.familiar is None or not body.library:
        return ''
    songs = '\n'.join(f'- {r.title} — {r.artist}' for r in body.library[:20])
    head = f"The listener's own library (their top tracks):\n{songs}\n"
    if body.familiar < 0.34:
        return head + ('FAMILIAR: most picks should be songs from this library or other songs by these artists, '
                       'as long as they fit the move. Say so in the reason.\n\n')
    if body.familiar < 0.67:
        return head + 'MIX: about half the picks from this library or its artists, half new to the listener.\n\n'
    return head + ('NEW: pick songs the listener likely has NOT heard: avoid this library and its artists, '
                   'but match its taste.\n\n')


def asked_moves(body: SuggestRequest) -> dict[str, str]:
    """The moves this round asks for: all of them, or only the ones being refreshed."""
    allowed = moves_for(body.goal)
    picked = {m: allowed[m] for m in body.only_moves if m in allowed}
    return picked or allowed


def feedback_lines(body: SuggestRequest, moves: dict[str, str]) -> str:
    """What the host said was off about a move's last picks (F3c), per move asked."""
    out = []
    for move, notes in body.feedback.items():
        notes = [n.strip() for n in notes[:6] if n.strip()]
        if move in moves and notes:
            out.append(f'- "{move}": the last picks were {", ".join(notes).lower()}. Correct for that.')
    return ('The host refreshed these moves; fix what was off:\n' + '\n'.join(out) + '\n\n') if out else ''


def build_prompt(body: SuggestRequest, tags: list[str]) -> str:
    def lines(refs: list[TrackRef]) -> str:
        return '\n'.join(f'- {r.title} — {r.artist}' for r in refs) or '- (none)'

    asked = asked_moves(body)
    moves = '\n'.join(f'- "{name}": {desc}' for name, desc in asked.items())
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
        + (f'Just shown and being replaced (do not suggest these):\n{lines(body.exclude)}\n\n' if body.exclude else '')
        + feedback_lines(body, asked)
        + familiar_line(body)
        + ('Clean versions only: no explicit songs.\n\n' if body.clean else '')
        + f'{_adventure_line(body.adventurousness)}\n\n'
        + f'Give {n} songs for each of these moves:\n{moves}'
    )


def normalize_moves(data, allowed: dict[str, str] = MOVES) -> dict[str, list[dict]]:
    """Coerce the parsed model output into {move: [{title, artist, reason}]},
    keeping only known moves and well-formed entries."""
    if not isinstance(data, dict):
        return {}
    out = {}
    for move in allowed:
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
    """A catalogue match can be a different artist's song of the same name.
    For a DJ that's a wrong track, so require the suggested artist to appear
    among the matched artists."""
    s = _fold(suggested)
    return bool(s) and any(s in _fold(a) or _fold(a) in s for a in spotify_artists if _fold(a))


def _fold(name: str) -> str:
    """'Tyler, The Creator' and 'tyler the creator' compare equal."""
    return re.sub(r'[^0-9a-z]', '', name.casefold())


def song_key(title: str, artist: str) -> str:
    """Folded title|artist, for matching songs that have no ISRC."""
    lead = artist.split(',')[0]
    return f'{_fold(title)}|{_fold(lead)}'


def select_tracks(
    moves: dict[str, list[dict]],
    matched: list[dict],
    exclude_ids: set[str],
    per_move: int,
    avoid_artists: list[str] = (),
    clean: bool = False,
    exclude_keys: set[str] = frozenset(),
) -> list[dict]:
    """Attach checked catalogue tracks to their moves, dropping wrong-artist
    matches, excluded tracks, do-not-play artists, explicit tracks when clean,
    and duplicates across moves. The prompt asks for all of this too; these
    filters are the guarantee.

    `matched[i]['spotify']` is the catalogue match. Since Q2 the DJ's comes
    from Deezer: its `id` is the ISRC (or `dz:<id>` without one), so
    `exclude_ids` holds ISRCs, and `exclude_keys` (folded title|artist) covers
    songs without one. Picks carry no Spotify id; clients resolve on tap."""
    by_key = {(m['title'], m['artist']): m for m in matched}
    seen = set(exclude_ids)
    seen_keys = set(exclude_keys)
    avoid = {_fold(a) for a in avoid_artists if _fold(a)}
    result = []
    for move, entries in moves.items():
        tracks = []
        for e in entries:
            m = by_key.get((e['title'], e['artist']))
            if not m:
                continue
            sp = m['spotify']
            key = song_key(sp['title'], sp['artists'][0] if sp['artists'] else e['artist'])
            if sp['id'] in seen or key in seen_keys or not _artist_matches(e['artist'], sp['artists']):
                continue
            if clean and sp.get('explicit'):
                continue
            if any(_fold(a) in avoid for a in sp['artists']):
                continue
            seen.add(sp['id'])
            seen_keys.add(key)
            tracks.append({
                'id': sp['id'],
                'title': sp['title'],
                'artists': sp['artists'],
                'image': sp['image'],
                'reason': e['reason'],
                **({'isrc': sp.get('isrc'), 'explicit': bool(sp.get('explicit'))} if 'isrc' in sp else {}),
            })
            if len(tracks) == per_move:
                break
        if tracks:
            result.append({'move': move, 'tracks': tracks})
    return result


async def deezer_validate(batch: list[dict], fallback: bool = False) -> tuple[list[dict], list[dict]]:
    """fill_moves' validator since Q2: check picks against Deezer, not Spotify,
    so a suggestion round spends no Spotify search quota (plan Q2)."""
    found = await deezer.find_many(batch)
    matched, failed = [], []
    for e in batch:
        song = found.get((e['title'], e['artist']))
        if song:
            matched.append({**e, 'spotify': {
                'id': song['isrc'] or f"dz:{song['deezer_id']}",
                'isrc': song['isrc'],
                'title': song['title'],
                'artists': song['artists'],
                'image': song['image'],
                'explicit': song['explicit'],
            }})
        else:
            failed.append(e)
    return matched, failed


async def fill_moves(moves, exclude, per_move, avoid_artists=(), clean=False, validate=None, exclude_keys=frozenset()):
    """Validate only as many picks as each move needs. The prompt over-asks
    (_OVERASK spares per move), but most picks match, so check the first
    `per_move` of each move and go further down a move's list only to replace
    a pick that failed a check. Since Q2 the checks are Deezer's, so a round
    spends no Spotify search quota at all (tracker e2df2d)."""
    validate = validate or deezer_validate
    matched, tried = [], set()
    while True:
        result = select_tracks(moves, matched, exclude, per_move, avoid_artists, clean, exclude_keys)
        have = {r['move']: len(r['tracks']) for r in result}
        batch = []
        for move, entries in moves.items():
            short = per_move - have.get(move, 0)
            if short > 0:
                batch += [e for e in entries if (e['title'], e['artist']) not in tried][:short]
        if not batch:
            return result
        tried.update((e['title'], e['artist']) for e in batch)
        found, _ = await validate(batch, fallback=False)
        matched += found


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
            refs.append(TrackRef(id=t['id'], isrc=(t.get('external_ids') or {}).get('isrc'),
                                 title=t.get('name', ''), artist=t['artists'][0].get('name', '')))
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


class RecapRequest(BaseModel):
    songs: list[TrackRef] = Field(min_length=1, max_length=100)


_RECAP_SYSTEM = (
    'You write Spotify playlist descriptions for a DJ set that just happened. Reply with the description only: '
    'one or two sentences, at most 250 characters, describing the arc of the night and its standout sounds. '
    'No emojis, no hashtags, no quotation marks.'
)


def recap_prompt(songs: list[TrackRef]) -> str:
    lines = '\n'.join(f'{i + 1}. {r.title} — {r.artist}' for i, r in enumerate(songs))
    return f'The set, in the order it played:\n{lines}'


def clean_recap(text: str) -> str:
    """One tidy line within Spotify's 300-character description limit."""
    t = ' '.join(text.split()).strip().strip('"').strip()
    return t if len(t) <= 300 else t[:297].rsplit(' ', 1)[0] + '…'


@router.post('/dj/recap/')
async def recap(body: RecapRequest, creds: LLMCredentials | None = Depends(get_optional_llm_credentials)):
    """Save tonight's set (F3f): an AI-written description. Optional in the UI."""
    if creds is None:
        raise HTTPException(status_code=401, detail='Connect an AI in Settings to write a recap.')
    client = creds.client()
    try:
        text = await client.generate([{'role': 'user', 'content': recap_prompt(body.songs)}], _RECAP_SYSTEM)
    except NeedsLLM:
        raise
    except Exception as e:
        log.warning('[dj] recap via %s failed: %s', creds.provider, e)
        raise HTTPException(status_code=502, detail="Couldn't write a recap right now.")
    return {'recap': clean_recap(text)}


def similar_moves(similar: list[dict], now_playing: TrackRef, limit: int) -> dict[str, list[dict]]:
    """Last.fm's similar tracks as the no-AI-key DJ's one move (F3e)."""
    entries = [{'title': t['title'], 'artist': t['artist'],
                'reason': f'Last.fm listeners who play {now_playing.title} also play this.'}
               for t in similar if t.get('title') and t.get('artist')]
    return {'similar': entries[:limit]} if entries else {}


async def suggest_without_llm(body: SuggestRequest, tags: list[str], all_recent: list[TrackRef]):
    """No AI key: songs Last.fm listeners play alongside now playing, checked on Deezer."""
    similar = await lastfm_client.track_similar(body.now_playing.title, body.now_playing.artist)
    refs = [body.now_playing, *all_recent, *body.upcoming, *body.avoid_tracks, *body.exclude]
    exclude = {r.isrc for r in refs if r.isrc}
    exclude_keys = {song_key(r.title, r.artist) for r in refs if r.title}
    per_move = max(body.per_move, 3) * 2  # one move instead of five: show more of it
    moves = similar_moves(similar, body.now_playing, per_move * 3)
    result = await fill_moves(moves, exclude, per_move, body.avoid_artists, body.clean, exclude_keys=exclude_keys) if moves else []
    return {
        'moves': result,
        'tags': tags,
        'source': 'lastfm',
        'error': None if result else "Last.fm has no similar songs for this one. Add an AI key for more picks.",
    }


@router.post('/dj/suggest/')
async def suggest(
    body: SuggestRequest,
    creds: LLMCredentials | None = Depends(get_optional_llm_credentials),
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

    if creds is None:
        return await suggest_without_llm(body, tags, all_recent)

    client = creds.client()
    try:
        raw = await client.generate([{'role': 'user', 'content': build_prompt(body, tags)}], SYSTEM_PROMPT)
    except NeedsLLM:
        raise
    except Exception as e:
        log.warning('[dj] %s request failed: %s', creds.provider, e)
        # Claude Code's messages are written for the user (e.g. "sign in again").
        message = str(e) if isinstance(e, ClaudeCodeError) else f'{creds.provider} request failed: {e}'
        return {'moves': [], 'tags': tags, 'error': message}

    try:
        moves = normalize_moves(extract_json(raw, context='dj'), asked_moves(body))
    except LLMParseError as e:
        moves = normalize_moves(salvage_truncated(e.raw), asked_moves(body))
        log.warning('[dj] parse failed (%d chars); salvaged %d moves', len(e.raw), len(moves))
        if not moves:
            return {'moves': [], 'tags': tags, 'error': _CUT_OFF}

    # Played, queued and avoided songs are excluded by ISRC, or by title+artist
    # for refs without one (picks no longer have Spotify ids to compare).
    refs = [body.now_playing, *all_recent, *body.upcoming, *body.avoid_tracks, *body.exclude]
    exclude = {r.isrc for r in refs if r.isrc}
    exclude_keys = {song_key(r.title, r.artist) for r in refs if r.title}
    result = await fill_moves(moves, exclude, body.per_move, body.avoid_artists, body.clean, exclude_keys=exclude_keys)
    return {
        'moves': result,
        'tags': tags,
        'source': 'ai',
        'error': None if result else 'None of the suggestions could be found this time. Try again.',
    }
