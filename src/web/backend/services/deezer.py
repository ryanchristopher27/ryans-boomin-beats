"""Deezer as the source for *showing* songs (plan Q1): existence, the right
artist, art, explicit flag and ISRC, without spending Spotify's search quota.

Deezer's public API needs no key (about 50 requests / 5 s per IP). Its terms
limit use to non-commercial, private scope: fine for the owner's small circle,
to be revisited before any public launch (brainstorm 2026-10-25, direction F).

Matching (Q0 spike, 60 real DJ picks): the strict `artist:"…" track:"…"`
syntax returns nothing, so search loosely and check title and artist here.
Search ranking sometimes hides a real song (Kendrick Lamar's "Money Trees"
lost to a sped-up re-upload), so a miss falls back to the artist's top tracks.
That found all 58 real songs and still rejected both invented ones.
"""
import asyncio
import collections
import logging
import re
import time

import httpx

from services import track_cache

log = logging.getLogger(__name__)

BASE = 'https://api.deezer.com'
# Deezer allows ~50 requests / 5 s per IP. Stay under it; a 60-pick burst at
# 4-in-flight (no pacing) drew 11 "Quota limit exceeded" errors in the Q1 check.
WINDOW_S = 5.0
MAX_PER_WINDOW = 40
_RETRIES = 3
# Re-uploads that outrank originals unless the pick asked for them.
# Re-upload markers, matched in a title's *label* (its bracketed or dashed
# suffix) so "Money Trees (Speed)" is caught but "Need for Speed" and
# "Undercover Lover" aren't. Each word maps to one kind, so "sped up" in the
# query allows a "(Speed Up)" result.
_VARIANT = re.compile(
    r'\b(sped[ -]?up|speed(?:[ -]?up)?|slowed|reverb|nightcore|8d|karaoke|instrumental|'
    r'cover|tribute|bass[ -]?boosted|official(?: music)? (?:audio|video)|lyrics?(?: video)?)\b', re.I)
_KIND = {'sped': 'speed', 'speed': 'speed', 'slowed': 'slowed', 'reverb': 'slowed', 'nightcore': 'speed',
         '8d': '8d', 'karaoke': 'karaoke', 'instrumental': 'instrumental', 'cover': 'cover',
         'tribute': 'cover', 'bass': 'bass', 'official': 'upload', 'lyric': 'upload', 'lyrics': 'upload'}
_LABELS = re.compile(r'[\(\[]([^\)\]]*)[\)\]]|\s-\s(.+)$')
# Accounts that only post re-uploads, named for it ("sped up viral").
_REUPLOAD_ARTIST = re.compile(r'\b(sped[ -]?up|slowed|nightcore|8d audio|bass[ -]?boosted)\b', re.I)


def _kinds(text: str) -> set[str]:
    return {_KIND[m.group(1).casefold().split()[0].split('-')[0]] for m in _VARIANT.finditer(text)}


def is_reupload(title: str, artist: str = '', wanted: str = '', *extra_labels: str) -> bool:
    """A sped-up / slowed / cover / karaoke… version the wanted text didn't ask for.
    `extra_labels` are checked whole (e.g. an album named "September (sped up + slowed)")."""
    labels = ' '.join(a or b for a, b in _LABELS.findall(title))
    found = _kinds(labels) | _kinds(' '.join(extra_labels))
    if _REUPLOAD_ARTIST.search(artist or ''):
        found |= _kinds(artist)
    return bool(found - _kinds(wanted))
_ARTIST_SPLIT = re.compile(r'\s*(?:,|&|\bfeat\.?|\bft\.?|\bfeaturing\b|\bwith\b|\bx\b|\band\b)\s*', re.I)


class DeezerUnavailable(Exception):
    """Deezer errored or throttled us; callers treat the songs as unchecked."""


def _fold(s: str) -> str:
    return re.sub(r'[^0-9a-z]', '', s.casefold())


def _base_title(t: str) -> str:
    """'Money Trees (feat. Jay Rock) - Remastered' -> 'Money Trees'."""
    return re.split(r'\s[\(\[]|\s-\s', t)[0]


def artists_of(artist: str) -> list[str]:
    return [a for a in _ARTIST_SPLIT.split(artist) if a]


def artist_matches(wanted: str, found: str) -> bool:
    got = _fold(found)
    return any(w and (w in got or got in w) for w in map(_fold, artists_of(wanted)))


def title_matches(wanted: str, found: str) -> bool:
    # Exact after stripping suffixes: a prefix rule let "Electric" match "Electricity".
    w, f = _fold(_base_title(wanted)), _fold(_base_title(found))
    if not w or w != f:
        return False
    return not is_reupload(found, wanted=wanted)


def _song(t: dict) -> dict:
    album = t.get('album') or {}
    return {
        'deezer_id': t['id'],
        'title': t.get('title', ''),
        'artists': [t.get('artist', {}).get('name', '')],
        'album': album.get('title', ''),
        'image': album.get('cover_medium') or album.get('cover') or '',
        'explicit': bool(t.get('explicit_lyrics')),
        'isrc': t.get('isrc') or None,
        'duration_ms': int(t.get('duration') or 0) * 1000,
    }


class Deezer:
    def __init__(self, http: httpx.AsyncClient | None = None, max_per_window: int = MAX_PER_WINDOW, window_s: float = WINDOW_S):
        self._http = http or httpx.AsyncClient(base_url=BASE, timeout=6.0)
        self._gate = asyncio.Semaphore(4)
        self._sent: collections.deque[float] = collections.deque()
        self._max, self._window = max_per_window, window_s
        self._pace = asyncio.Lock()

    async def _wait_turn(self):
        """Sliding-window pacing: at most `_max` requests per `_window` seconds."""
        async with self._pace:
            while True:
                now = time.monotonic()
                while self._sent and now - self._sent[0] >= self._window:
                    self._sent.popleft()
                if len(self._sent) < self._max:
                    self._sent.append(now)
                    return
                await asyncio.sleep(self._window - (now - self._sent[0]) + 0.01)

    async def _get(self, path: str, **params) -> dict:
        for attempt in range(_RETRIES + 1):
            async with self._gate:
                await self._wait_turn()
                try:
                    res = await self._http.get(path, params=params)
                    data = res.json()
                except (httpx.HTTPError, ValueError) as e:
                    raise DeezerUnavailable(str(e)) from e
            error = data.get('error') if isinstance(data, dict) else None
            if not error:
                return data
            # Code 4 is Deezer's rate limit (shared per IP, so other tenants of a
            # serverless IP count too): its window is seconds, so wait and retry.
            if isinstance(error, dict) and error.get('code') == 4 and attempt < _RETRIES:
                await asyncio.sleep(1.0 + attempt)
                continue
            raise DeezerUnavailable(str(error)[:200])
        raise DeezerUnavailable('rate limited')

    async def search(self, q: str, limit: int = 10) -> list[dict]:
        """Free-text track search (type-ahead), formatted, no matching."""
        data = await self._get('/search', q=q, limit=limit)
        return [_song(t) for t in data.get('data', []) if t.get('readable', True)]

    async def find(self, title: str, artist: str) -> dict | None:
        """The pick as Deezer has it, or None when it isn't there (right title AND artist)."""
        lead = artists_of(artist)[0] if artists_of(artist) else artist
        data = await self._get('/search', q=f'{_base_title(title)} {lead}', limit=10)
        for t in data.get('data', []):
            if t.get('readable', True) and title_matches(title, t.get('title', '')) \
                    and artist_matches(artist, t.get('artist', {}).get('name', '')):
                return _song(t)
        return await self._from_top_tracks(title, artist)

    async def preview(self, deezer_id: int | None = None, isrc: str | None = None, title: str = '', artist: str = '') -> str | None:
        """A fresh 30 s preview URL, or None. Deezer signs these and they expire
        within hours, so they are fetched per play and never cached."""
        data = None
        if deezer_id is None and isrc:
            try:
                data = await self._get(f'/track/isrc:{isrc}')
            except DeezerUnavailable:
                pass  # unknown ISRC answers with an error body; title + artist still can match
        if data is None:
            if deezer_id is None:
                song = await self.find(title, artist) if title and artist else None
                if not song:
                    return None
                deezer_id = song['deezer_id']
            data = await self._get(f'/track/{deezer_id}')
        return data.get('preview') or None

    async def _from_top_tracks(self, title: str, artist: str) -> dict | None:
        lead = artists_of(artist)[0] if artists_of(artist) else artist
        found = (await self._get('/search/artist', q=lead, limit=1)).get('data', [])
        if not found or _fold(found[0].get('name', '')) != _fold(lead):
            return None
        top = await self._get(f"/artist/{found[0]['id']}/top", limit=100)
        hit = next((t for t in top.get('data', []) if title_matches(title, t.get('title', ''))), None)
        if not hit:
            return None
        song = _song(hit)
        if not song['isrc']:  # top-track results omit it; one more (cached) call
            song['isrc'] = (await self._get(f"/track/{hit['id']}")).get('isrc') or None
        return song


_deezer: Deezer | None = None
# Process cache in front of the shared one; misses included.
_CACHE: dict[tuple[str, str], dict | None] = {}
_CACHE_MAX = 5000


def client() -> Deezer:
    global _deezer
    if _deezer is None:
        _deezer = Deezer()
    return _deezer


def as_track(song: dict) -> dict:
    """A Deezer song in the shape clients already render as a track (Q3). `id`
    is a key, not a Spotify id: the ISRC, or `dz:<id>` without one. Clients
    resolve it at choose time via POST /tracks/resolve/."""
    return {
        'id': song['isrc'] or f"dz:{song['deezer_id']}",
        'isrc': song['isrc'],
        'title': song['title'],
        'artists': song['artists'],
        'album': song.get('album', ''),
        'image': song['image'],
        'track_url': '',
        'duration_ms': song['duration_ms'],
        'explicit': song['explicit'],
    }


async def validate(suggestions: list[dict]) -> tuple[list[dict], list[dict]]:
    """Check playlist suggestions on Deezer: (matched, failed), with `spotify` holding
    the as_track() match, so the playlist builder spends no Spotify search (Q3)."""
    found = await find_many(suggestions)
    matched, failed = [], []
    for s in suggestions:
        song = found.get((s['title'], s['artist']))
        if song:
            matched.append({'title': s['title'], 'artist': s['artist'], 'reason': s.get('reason', ''), 'spotify': as_track(song)})
        else:
            failed.append(s)
    return matched, failed


async def find_many(songs: list[dict], dz: Deezer | None = None) -> dict[tuple[str, str], dict | None]:
    """{(title, artist): Deezer song or None} for each {title, artist}, cheapest
    source first: this process, the shared cache, then Deezer. A Deezer outage
    leaves those songs out of the result (unchecked), never cached as misses."""
    dz = dz or client()
    out: dict[tuple[str, str], dict | None] = {}
    pending = {}
    for s in songs:
        k = (s['title'].casefold(), s['artist'].casefold())
        if k in _CACHE:
            out[(s['title'], s['artist'])] = _CACHE[k]
        else:
            pending[k] = s
    if not pending:
        return out
    digests = {k: track_cache.key('deezer', s['title'], s['artist']) for k, s in pending.items()}
    shared = await asyncio.to_thread(track_cache.get_many, list(set(digests.values())))
    to_fetch = {}
    for k, s in pending.items():
        if digests[k] in shared:
            out[(s['title'], s['artist'])] = _CACHE[k] = shared[digests[k]]
        else:
            to_fetch[k] = s
    if to_fetch:
        found = await asyncio.gather(*[dz.find(s['title'], s['artist']) for s in to_fetch.values()], return_exceptions=True)
        fresh = {}
        for (k, s), r in zip(to_fetch.items(), found):
            if isinstance(r, BaseException):
                log.info('[deezer] lookup skipped for %r: %s', s['title'], r)
                continue
            if len(_CACHE) >= _CACHE_MAX:
                _CACHE.clear()
            out[(s['title'], s['artist'])] = _CACHE[k] = r
            fresh[digests[k]] = r
        await asyncio.to_thread(track_cache.put_many, fresh)
    return out
