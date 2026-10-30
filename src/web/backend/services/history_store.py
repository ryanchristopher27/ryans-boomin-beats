"""Listening history: each user's plays in Supabase (`listening_history`), kept
past Spotify's 50-play recently-played window. Saved from Profile visits and
while the DJ page is open; read back as stats for Profile. Best effort: when
Supabase is off or down, callers fall back to Spotify's 50 plays."""
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

import httpx

from config import SUPABASE_SERVICE_KEY, SUPABASE_URL, SYNC_ENABLED

log = logging.getLogger(__name__)

WINDOW_DAYS = 90
WEEKS = 12
_PAGE = 1000  # PostgREST's default max rows per response


class Unavailable(Exception):
    """Supabase is off, didn't answer, or rejected the request."""


def _client() -> httpx.Client:
    if not SYNC_ENABLED:
        raise Unavailable('history storage is off')
    return httpx.Client(
        base_url=f'{SUPABASE_URL}/rest/v1',
        headers={'apikey': SUPABASE_SERVICE_KEY, 'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}', 'Content-Type': 'application/json'},
        timeout=8.0,
    )


def rows_from_recent(user: str, items: list[dict]) -> list[dict]:
    """Spotify recently-played items as table rows (local files and episodes have no track id)."""
    rows = []
    for it in items:
        t = it.get('track') or {}
        if not it.get('played_at') or not t.get('id'):
            continue
        rows.append({
            'spotify_user_id': user,
            'played_at': it['played_at'],
            'track_id': t['id'],
            'title': (t.get('name') or '')[:300],
            'artist': ((t.get('artists') or [{}])[0].get('name') or '')[:300],
            'duration_ms': int(t.get('duration_ms') or 0),
        })
    return rows


def save(rows: list[dict]) -> None:
    """Insert plays; ones already stored (same user and timestamp) are ignored."""
    if not rows:
        return
    try:
        with _client() as http:
            res = http.post('/listening_history', json=rows, headers={'Prefer': 'resolution=ignore-duplicates,return=minimal'})
    except httpx.HTTPError as e:
        raise Unavailable(str(e)) from e
    if res.status_code >= 400:
        log.warning('[history] save -> %s %s', res.status_code, res.text[:200])
        raise Unavailable(f'Supabase {res.status_code}')


def plays_since(user: str, since: datetime) -> list[dict]:
    """The user's plays from `since` on, oldest first."""
    out = []
    try:
        with _client() as http:
            while True:
                res = http.get('/listening_history', params={
                    'spotify_user_id': f'eq.{user}', 'played_at': f'gte.{since.isoformat()}',
                    'select': 'played_at,artist,duration_ms', 'order': 'played_at.asc',
                    'limit': _PAGE, 'offset': len(out),
                })
                if res.status_code >= 400:
                    log.warning('[history] read -> %s %s', res.status_code, res.text[:200])
                    raise Unavailable(f'Supabase {res.status_code}')
                page = res.json()
                out += page
                if len(page) < _PAGE:
                    return out
    except httpx.HTTPError as e:
        raise Unavailable(str(e)) from e


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


def stats(plays: list[dict], tz_offset_min: int = 0, now: datetime | None = None) -> dict:
    """Profile's listening stats in the listener's local time. `tz_offset_min` is
    JavaScript's getTimezoneOffset(): minutes local time is behind UTC."""
    now = now or datetime.now(timezone.utc)
    local = lambda d: d - timedelta(minutes=tz_offset_min)  # noqa: E731
    today = local(now).date()
    hours, days = [0] * 24, [0] * 7
    week0 = today - timedelta(days=today.weekday() + 7 * (WEEKS - 1))  # Monday, WEEKS weeks back
    weeks = [{'start': (week0 + timedelta(weeks=i)).isoformat(), 'plays': 0, 'minutes': 0, 'artists': set()} for i in range(WEEKS)]
    active = set()
    minutes = 0
    for p in plays:
        at = local(_parse(p['played_at']))
        ms = int(p.get('duration_ms') or 0)
        hours[at.hour] += 1
        days[(at.weekday() + 1) % 7] += 1  # 0 = Sunday, like JavaScript's getDay()
        active.add(at.date())
        minutes += ms / 60000
        i = (at.date() - week0).days // 7
        if 0 <= i < WEEKS:
            weeks[i]['plays'] += 1
            weeks[i]['minutes'] += ms / 60000
            if p.get('artist'):
                weeks[i]['artists'].add(p['artist'].casefold())
    # Days in a row with a play, ending today (or yesterday, if today has none yet).
    day = today if today in active else today - timedelta(days=1)
    streak = 0
    while day in active:
        streak += 1
        day -= timedelta(days=1)
    top_artist = Counter(p['artist'] for p in plays if p.get('artist')).most_common(1)
    return {
        'since': plays[0]['played_at'] if plays else None,
        'plays': len(plays),
        'minutes': round(minutes),
        'days_active': len(active),
        'streak': streak,
        'hours': hours,
        'days': days,
        'weeks': [{**w, 'minutes': round(w['minutes']), 'artists': len(w['artists'])} for w in weeks],
        'top_artist': top_artist[0][0] if top_artist else None,
    }
