"""Deezer as the display source (plan Q1): matching rules from the Q0 spike,
the top-tracks fallback, and outages never cached as misses. HTTP is mocked.

    python -m unittest tests.test_deezer -v
"""
import asyncio
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402

from services import deezer, track_cache  # noqa: E402
from services.deezer import Deezer, DeezerUnavailable, artist_matches, title_matches  # noqa: E402


def track(tid, title, artist, isrc='USAAA0000001', explicit=False):
    return {'id': tid, 'title': title, 'artist': {'name': artist}, 'explicit_lyrics': explicit, 'readable': True,
            'duration': 200, 'isrc': isrc, 'album': {'cover_medium': f'https://img/{tid}'}}


def fake(routes):
    """routes: {(path, q or ''): json}."""
    def handler(request):
        q = request.url.params.get('q', '')
        body = routes.get((request.url.path, q), routes.get((request.url.path, ''), {'data': []}))
        return httpx.Response(200, json=body)
    return Deezer(httpx.AsyncClient(base_url='https://api.deezer.com', transport=httpx.MockTransport(handler)))


class Matching(unittest.TestCase):
    def test_featured_and_listed_artists(self):
        self.assertTrue(artist_matches('Kendrick Lamar feat. Jay Rock', 'Kendrick Lamar'))
        self.assertTrue(artist_matches('Earth, Wind & Fire', 'Earth, Wind & Fire'))
        self.assertTrue(artist_matches('Run The Jewels & Cardi B', 'Cardi B'))
        self.assertFalse(artist_matches('Run The Jewels', 'Cardi B'))

    def test_titles_ignore_suffixes_but_not_reuploads(self):
        self.assertTrue(title_matches('Money Trees', 'Money Trees (feat. Jay Rock)'))
        self.assertTrue(title_matches('September', 'September - 2018 Remaster'))
        self.assertFalse(title_matches('Money Trees', 'money trees (kendrick lamar, jay rock) (sped up version)'))
        self.assertTrue(title_matches('Redbone (Slowed)', 'Redbone (slowed)'))  # asked for it
        self.assertFalse(title_matches('Electric', 'Electricity'))


class Find(unittest.TestCase):
    def test_search_hit_needs_title_and_artist(self):
        dz = fake({('/search', 'Electric Alina Baraz'): {'data': [
            track(1, 'Fantasy', 'Alina Baraz'),            # right artist, wrong song
            track(2, 'Electric', 'Alina Baraz', isrc='USQE91500375')]}})
        song = asyncio.run(dz.find('Electric', 'Alina Baraz'))
        self.assertEqual((song['deezer_id'], song['isrc']), (2, 'USQE91500375'))

    def test_miss_falls_back_to_the_artists_top_tracks(self):
        dz = fake({
            ('/search', 'Money Trees Kendrick Lamar'): {'data': [track(9, 'money trees (sped up version)', 'sped up viral')]},
            ('/search/artist', 'Kendrick Lamar'): {'data': [{'id': 525046, 'name': 'Kendrick Lamar'}]},
            ('/artist/525046/top', ''): {'data': [dict(track(7, 'Money Trees', 'Kendrick Lamar'), isrc=None)]},
            ('/track/7', ''): {'isrc': 'USUM71210785'},
        })
        song = asyncio.run(dz.find('Money Trees', 'Kendrick Lamar'))
        self.assertEqual((song['deezer_id'], song['isrc']), (7, 'USUM71210785'))

    def test_invented_song_is_none(self):
        dz = fake({('/search/artist', 'Masego'): {'data': [{'id': 1, 'name': 'Masego'}]},
                   ('/artist/1/top', ''): {'data': [track(3, 'Tadow', 'Masego')]}})
        self.assertIsNone(asyncio.run(dz.find('Sailing Soul(s)', 'Masego')))

    def test_deezer_errors_raise(self):
        dz = fake({('/search', ''): {'error': {'code': 4, 'message': 'Quota limit exceeded'}}})
        with mock.patch('services.deezer.asyncio.sleep', new=mock.AsyncMock()), self.assertRaises(DeezerUnavailable):
            asyncio.run(dz.find('A', 'B'))  # still limited after every retry


class Pacing(unittest.TestCase):
    def test_bursts_are_spread_over_the_window(self):
        calls = []

        def handler(request):
            calls.append(asyncio.get_event_loop().time())
            return httpx.Response(200, json={'data': []})
        dz = Deezer(httpx.AsyncClient(base_url='https://x', transport=httpx.MockTransport(handler)), max_per_window=5, window_s=0.2)

        async def burst():
            await asyncio.gather(*[dz._get('/search', q=str(i)) for i in range(12)])
        asyncio.run(burst())
        span = max(calls) - min(calls)
        self.assertGreaterEqual(span, 0.35)  # 12 requests at 5 per 0.2 s need at least two refills

    def test_rate_limit_errors_are_retried(self):
        replies = iter([{'error': {'code': 4, 'message': 'Quota limit exceeded'}}, {'data': [track(1, 'A', 'B')]}])
        dz = Deezer(httpx.AsyncClient(base_url='https://x', transport=httpx.MockTransport(lambda r: httpx.Response(200, json=next(replies)))))
        with mock.patch('services.deezer.asyncio.sleep', new=mock.AsyncMock()):
            self.assertEqual(len(asyncio.run(dz._get('/search', q='A B'))['data']), 1)


class FindMany(unittest.TestCase):
    def setUp(self):
        deezer._CACHE.clear()
        self.stored = {}
        for p in (mock.patch.object(track_cache, 'get_many', side_effect=lambda keys: {k: v for k, v in self.stored.items() if k in keys}),
                  mock.patch.object(track_cache, 'put_many', side_effect=self.stored.update)):
            p.start()
            self.addCleanup(p.stop)

    def test_cached_across_instances_and_outages_not_cached(self):
        dz = fake({('/search', 'Electric Alina Baraz'): {'data': [track(2, 'Electric', 'Alina Baraz')]},
                   ('/search', 'Down Deezer'): {'error': {'code': 700, 'message': 'down'}}})
        songs = [{'title': 'Electric', 'artist': 'Alina Baraz'}, {'title': 'Down', 'artist': 'Deezer'}]
        out = asyncio.run(deezer.find_many(songs, dz))
        self.assertEqual(out[('Electric', 'Alina Baraz')]['deezer_id'], 2)
        self.assertNotIn(('Down', 'Deezer'), out)  # unchecked, not "missing"
        self.assertEqual(len(self.stored), 1)
        deezer._CACHE.clear()  # a new instance reads the shared cache
        broken = fake({('/search', ''): {'error': {'code': 700}}})
        self.assertEqual(asyncio.run(deezer.find_many(songs[:1], broken))[('Electric', 'Alina Baraz')]['deezer_id'], 2)


if __name__ == '__main__':
    unittest.main()
