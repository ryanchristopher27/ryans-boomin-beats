"""Record what Last.fm and Deezer really return for the golden queries, so
test_search_golden.py can replay them offline. Re-run after changing a query or
when the sources drift; review the diff before committing. No Spotify calls.

    python tests/golden/record.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from routers import search  # noqa: E402
from services import deezer, lastfm_client  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from test_search_golden import FIXTURES, GOLDEN  # noqa: E402


async def record(q: str) -> dict:
    """One real call to the endpoint, keeping what each source answered."""
    got = {'lastfm': [], 'deezer_search': [], 'deezer_found': []}
    real_lastfm, real_find_many, dz = lastfm_client.track_search, deezer.find_many, deezer.client()
    real_search = dz.search

    async def lastfm_spy(query, limit=15):
        got['lastfm'] = await real_lastfm(query, limit)
        return got['lastfm']

    async def search_spy(query, limit=10):
        got['deezer_search'] = await real_search(query, limit)
        return got['deezer_search']

    async def find_many_spy(songs, dz=None):
        result = await real_find_many(songs, dz)
        got['deezer_found'] += [[s['title'], s['artist'], result.get((s['title'], s['artist']))] for s in songs]
        return result

    lastfm_client.track_search, deezer.find_many, dz.search = lastfm_spy, find_many_spy, search_spy
    try:
        await search.search(q)
    finally:
        lastfm_client.track_search, deezer.find_many, dz.search = real_lastfm, real_find_many, real_search
    return got


async def main():
    out = {}
    for q in GOLDEN:
        out[q] = await record(q)
        print(f'{q!r}: {len(out[q]["lastfm"])} Last.fm, {len(out[q]["deezer_search"])} Deezer, '
              f'{len(out[q]["deezer_found"])} lookups')
    with open(FIXTURES, 'w') as f:
        json.dump(out, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write('\n')


if __name__ == '__main__':
    asyncio.run(main())
