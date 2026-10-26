"""Choose-time Spotify resolve (plan Q1): exact by ISRC, title only without
one, the playable own-release preferred, and a search spent once per song.

    python -m unittest tests.test_resolver -v
"""
import asyncio
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from services import track_cache, track_resolver  # noqa: E402
from services.spotify_auth import get_spotify_token  # noqa: E402


def sp_track(tid, album_type='album', playable=True, explicit=False):
    return {'id': tid, 'name': tid, 'artists': [{'name': 'A'}], 'explicit': explicit, 'is_playable': playable,
            'duration_ms': 1000, 'external_urls': {'spotify': ''},
            'album': {'name': 'X', 'album_type': album_type, 'images': [{'url': 'i'}]}}


class Pick(unittest.TestCase):
    def test_prefers_the_album_then_single_then_compilation(self):
        items = [sp_track('comp', 'compilation'), sp_track('gone', playable=False), sp_track('single', 'single'), sp_track('album')]
        self.assertEqual(track_resolver._pick(items)['id'], 'album')
        self.assertEqual(track_resolver._pick(items[:3])['id'], 'single')
        self.assertEqual(track_resolver._pick([sp_track('comp', 'compilation')])['id'], 'comp')
        self.assertIsNone(track_resolver._pick([sp_track('gone', playable=False)]))

    def test_skips_reuploads_sharing_the_isrc(self):
        # Q0 spike: September's only "single" was a sped up + slowed re-release.
        reupload = sp_track('September', 'single')
        reupload['album']['name'] = 'September (sped up + slowed)'
        hits = [reupload, sp_track('best-of', 'compilation')]
        self.assertEqual(track_resolver._pick(hits, 'September')['id'], 'best-of')
        self.assertEqual(track_resolver._pick([reupload], 'September (sped up + slowed)')['id'], 'September')  # asked for it


class Resolve(unittest.TestCase):
    def setUp(self):
        track_resolver._CACHE.clear()
        self.stored, self.queries = {}, []
        for p in (mock.patch.object(track_cache, 'get_many', side_effect=lambda keys: {k: v for k, v in self.stored.items() if k in keys}),
                  mock.patch.object(track_cache, 'put_many', side_effect=self.stored.update),
                  mock.patch.object(track_resolver, 'app_client', return_value=object()),
                  mock.patch.object(track_resolver, 'search', side_effect=self.fake_search)):
            p.start()
            self.addCleanup(p.stop)

    def fake_search(self, spotify, purpose='', **kw):
        self.queries.append(kw['q'])
        assert kw['market'] == 'US'
        items = [] if 'NOPE' in kw['q'] else [sp_track('t-' + kw['q'][-4:])]
        return {'tracks': {'items': items}}

    def test_isrc_is_one_exact_search_and_cached(self):
        songs = [{'isrc': 'USUM71210785', 'title': 'Money Trees', 'artist': 'Kendrick Lamar'}]
        first = asyncio.run(track_resolver.resolve(songs))
        self.assertEqual(self.queries, ['isrc:USUM71210785'])
        track_resolver._CACHE.clear()  # another instance
        self.assertEqual(asyncio.run(track_resolver.resolve(songs)), first)
        self.assertEqual(len(self.queries), 1)

    def test_no_isrc_uses_a_strict_title_search(self):
        asyncio.run(track_resolver.resolve([{'isrc': None, 'title': 'Kiss', 'artist': 'Prince'}]))
        self.assertEqual(self.queries, ['track:Kiss artist:Prince'])

    def test_unknown_isrc_falls_back_to_title_and_misses_are_none(self):
        out = asyncio.run(track_resolver.resolve([{'isrc': 'NOPE00000000', 'title': 'NOPE', 'artist': 'X'}]))
        self.assertEqual(out, [None])
        self.assertEqual(len(self.queries), 2)

    def test_duplicates_in_one_request_search_once(self):
        song = {'isrc': 'USQE91500375', 'title': 'Electric', 'artist': 'Alina Baraz'}
        out = asyncio.run(track_resolver.resolve([song, song]))
        self.assertEqual(len(self.queries), 1)
        self.assertEqual(out[0], out[1])


class Concurrency(unittest.TestCase):
    def test_at_most_four_searches_in_flight(self):
        import threading
        import time
        track_resolver._CACHE.clear()
        lock, state = threading.Lock(), {'now': 0, 'peak': 0}

        def slow_lookup(spotify, song):
            with lock:
                state['now'] += 1
                state['peak'] = max(state['peak'], state['now'])
            time.sleep(0.03)
            with lock:
                state['now'] -= 1
            return {'id': song['isrc']}
        songs = [{'isrc': f'USAAA00000{i:02d}', 'title': 't', 'artist': 'a'} for i in range(12)]
        with mock.patch.object(track_resolver, '_lookup', side_effect=slow_lookup), \
                mock.patch.object(track_resolver, 'app_client', return_value=object()), \
                mock.patch.object(track_cache, 'get_many', return_value={}), mock.patch.object(track_cache, 'put_many'):
            asyncio.run(track_resolver.resolve(songs))
        self.assertLessEqual(state['peak'], 4)
        self.assertGreater(state['peak'], 1)


class Endpoint(unittest.TestCase):
    def setUp(self):
        main.app.dependency_overrides[get_spotify_token] = lambda: 'tok'
        self.client = TestClient(main.app)
        self.addCleanup(main.app.dependency_overrides.clear)

    def test_validates_isrc_shape_and_batch_size(self):
        self.assertEqual(self.client.post('/tracks/resolve/', json={'songs': [{'isrc': "x'; DROP"}]}).status_code, 422)
        self.assertEqual(self.client.post('/tracks/resolve/', json={'songs': [{'title': 't'}] * 51}).status_code, 422)
        self.assertEqual(self.client.post('/tracks/resolve/', json={'songs': []}).status_code, 422)

    def test_returns_tracks_in_order(self):
        async def fake(songs):
            return [{'id': s['title']} for s in songs]
        with mock.patch.object(track_resolver, 'resolve', side_effect=fake):
            r = self.client.post('/tracks/resolve/', json={'songs': [{'title': 'a'}, {'title': 'b'}]})
        self.assertEqual(r.json(), {'tracks': [{'id': 'a'}, {'id': 'b'}]})


class Schema(unittest.TestCase):
    def test_synced_items_accept_an_isrc(self):
        from routers.dj_state import DJStateDoc
        doc = DJStateDoc.model_validate({'queue': {'upcoming': [{'id': 'e', 'trackID': 't', 'title': 'x', 'isrc': 'USUM71210785'}]}})
        self.assertEqual(doc.queue.upcoming[0].isrc, 'USUM71210785')
        self.assertIsNone(DJStateDoc.model_validate({'queue': {'upcoming': [{'id': 'e', 'trackID': 't', 'title': 'x'}]}}).queue.upcoming[0].isrc)

    def test_player_tracks_carry_the_isrc(self):
        from routers.player import _track
        t = _track({'type': 'track', 'id': 'x', 'name': 'n', 'artists': [], 'album': {}, 'external_ids': {'isrc': 'USYAH1600107'}})
        self.assertEqual(t['isrc'], 'USYAH1600107')


if __name__ == '__main__':
    unittest.main()
