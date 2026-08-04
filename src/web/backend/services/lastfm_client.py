import logging
import re
import httpx
from config import LASTFM_API_KEY

log = logging.getLogger(__name__)

BASE_URL = 'http://ws.audioscrobbler.com/2.0/'


async def track_info(title: str, artist: str) -> dict:
    params = {
        'method': 'track.getInfo',
        'api_key': LASTFM_API_KEY,
        'artist': artist,
        'track': title,
        'format': 'json',
        'autocorrect': 1,
    }
    if not LASTFM_API_KEY:
        log.warning('[lastfm] LASTFM_API_KEY is unset — tags and play counts unavailable')
        return _empty()

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(BASE_URL, params=params, timeout=5.0)
            data = res.json()
    except Exception as e:
        log.warning('[lastfm] request failed for %r by %r: %s', title, artist, e)
        return _empty()

    # Error 10 is an invalid API key — a config problem, not a missing track,
    # and it silently degraded every profile to zero tags before this log.
    if 'error' in data:
        log.warning('[lastfm] API error %s: %s', data.get('error'), data.get('message'))
        return _empty()

    if 'track' not in data:
        log.info('[lastfm] no track match for %r by %r', title, artist)
        return _empty()

    track = data['track']

    tags = []
    if 'toptags' in track and 'tag' in track['toptags']:
        tags = [
            {'name': t['name'], 'url': t['url']}
            for t in track['toptags']['tag']
            if t.get('name')
        ]

    wiki_summary = ''
    if 'wiki' in track and 'summary' in track['wiki']:
        raw = track['wiki']['summary']
        wiki_summary = re.sub(r'<[^>]+>', '', raw).strip()
        wiki_summary = wiki_summary.split('Read more on Last.fm')[0].strip()

    return {
        'tags': tags,
        'listeners': int(track.get('listeners', 0) or 0),
        'play_count': int(track.get('playcount', 0) or 0),
        'wiki_summary': wiki_summary,
    }


def _empty() -> dict:
    return {'tags': [], 'listeners': 0, 'play_count': 0, 'wiki_summary': ''}
