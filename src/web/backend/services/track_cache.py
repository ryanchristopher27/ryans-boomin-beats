"""Shared cache of Spotify search results in Supabase (`track_lookup`).

Spotify's Development Mode search quota is daily and shared by the whole
developer account, and the DJ's suggestions repeat songs constantly across a
night, across devices and across serverless instances. One lookup per song a
month instead of one per suggestion. Best effort: if Supabase is unconfigured
or down, callers just search as before.
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import httpx

from config import SUPABASE_SERVICE_KEY, SUPABASE_URL, SYNC_ENABLED

log = logging.getLogger(__name__)

FOUND_FOR = timedelta(days=30)
# Misses are mostly LLM inventions, but a new release can appear later.
MISS_FOR = timedelta(days=7)

_http: httpx.Client | None = None


def key(*parts) -> str:
    """Hashed row key. A leading namespace keeps sources apart in one table
    (plan Q1): `key('deezer', title, artist)`, `key('isrc', isrc)`. The legacy
    Spotify title search keeps its original shape `(title, artist, fallback)`
    so rows cached before Q1 stay valid."""
    norm = [str(int(p)) if isinstance(p, bool) else str(p).casefold().strip() for p in parts]
    return hashlib.sha256('|'.join(norm).encode()).hexdigest()


def _client() -> httpx.Client | None:
    global _http
    if not SYNC_ENABLED:
        return None
    if _http is None:
        _http = httpx.Client(
            base_url=f'{SUPABASE_URL}/rest/v1',
            headers={'apikey': SUPABASE_SERVICE_KEY, 'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                     'Content-Type': 'application/json'},
            timeout=4.0,
        )
    return _http


def get_many(keys: list[str], now: datetime | None = None) -> dict[str, dict | None]:
    """Fresh cached results for these keys: track dict, or None for a known miss."""
    http = _client()
    if not http or not keys:
        return {}
    now = now or datetime.now(timezone.utc)
    try:
        # Keys are hex digests, so they need no quoting inside in.(...).
        res = http.get('/track_lookup', params={
            'key': f'in.({",".join(keys)})',
            'created_at': f'gte.{(now - FOUND_FOR).isoformat()}',
            'select': 'key,track,created_at',
        })
        res.raise_for_status()
    except httpx.HTTPError as e:
        log.info('[track-cache] read skipped: %s', e)
        return {}
    out = {}
    for row in res.json():
        if row['track'] is None and datetime.fromisoformat(row['created_at']) < now - MISS_FOR:
            continue
        out[row['key']] = row['track']
    return out


def put_many(results: dict[str, dict | None]) -> None:
    http = _client()
    if not http or not results:
        return
    stamp = datetime.now(timezone.utc).isoformat()
    rows = [{'key': k, 'track': t, 'created_at': stamp} for k, t in results.items()]
    try:
        http.post('/track_lookup', params={'on_conflict': 'key'}, json=rows,
                  headers={'Prefer': 'resolution=merge-duplicates,return=minimal'}).raise_for_status()
    except httpx.HTTPError as e:
        log.info('[track-cache] write skipped: %s', e)
