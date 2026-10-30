"""Library stats for Profile: Liked Songs (size, growth, decades, artists) and
your playlists. A full Liked Songs scan is one request per 50 songs, so the
summary is cached (track_lookup, key 'library' + user) and only rebuilt when the
library's size or newest like changes."""
from collections import Counter
from datetime import datetime, timezone

MAX_SONGS = 5000  # 100 requests; a bigger library is summarised from its newest 5,000


def summarize(items: list[dict], total: int, now: datetime | None = None) -> dict:
    """`items`: Spotify saved-track items ({added_at, track}), newest first."""
    now = now or datetime.now(timezone.utc)
    added = [datetime.fromisoformat(it['added_at'].replace('Z', '+00:00')) for it in items if it.get('added_at')]
    months = []
    y, m = now.year, now.month
    for _ in range(12):
        months.append(f'{y:04d}-{m:02d}')
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    months.reverse()
    by_month = Counter(d.strftime('%Y-%m') for d in added)
    decades = Counter()
    artists = Counter()
    for it in items:
        t = it.get('track') or {}
        year = ((t.get('album') or {}).get('release_date') or '')[:4]
        if year.isdigit():
            decades[f'{year[:3]}0s'] += 1
        for a in (t.get('artists') or [])[:1]:
            if a.get('name'):
                artists[a['name']] += 1
    return {
        'total': total,
        'scanned': len(items),
        'newest': items[0]['added_at'] if items else None,
        'oldest': min(added).isoformat() if added and len(items) >= total else None,
        'this_year': sum(1 for d in added if d.year == now.year),
        'this_month': by_month.get(now.strftime('%Y-%m'), 0),
        'months': [{'month': k, 'count': by_month.get(k, 0)} for k in months],
        'decades': [{'decade': k, 'count': v} for k, v in sorted(decades.items())],
        'top_artists': [{'name': k, 'count': v} for k, v in artists.most_common(5)],
    }


def playlist_stats(playlists: list[dict], me: str) -> dict:
    """`playlists`: /me/playlists items (the user's own and followed ones)."""
    playlists = [p for p in playlists if p]  # Spotify sends null for some unavailable playlists
    owned = [p for p in playlists if (p.get('owner') or {}).get('id') == me]
    count = lambda p: ((p.get('items') or p.get('tracks') or {}).get('total') or 0)  # noqa: E731 (renamed "items" in 2026)
    biggest = max(owned, key=count, default=None)
    return {
        'count': len(playlists),
        'owned': len(owned),
        'songs': sum(count(p) for p in owned),
        'collaborative': sum(1 for p in owned if p.get('collaborative')),
        'biggest': {'name': biggest.get('name', ''), 'songs': count(biggest)} if biggest else None,
    }
