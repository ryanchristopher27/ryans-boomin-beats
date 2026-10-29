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


class Reuploads(unittest.TestCase):
    def test_labels_are_checked_not_whole_titles(self):
        from services.deezer import is_reupload
        self.assertTrue(is_reupload('Money Trees (Speed)'))
        self.assertTrue(is_reupload('Money Trees (Cover)'))
        self.assertTrue(is_reupload('September - Sped Up'))
        self.assertTrue(is_reupload('Redbone [slowed + reverb]'))
        self.assertFalse(is_reupload('Need for Speed'))
        self.assertFalse(is_reupload('Undercover Lover'))
        self.assertFalse(is_reupload('Electric (R3hab Remix)'))  # remixes are real releases
        self.assertTrue(is_reupload('HUMBLE. (Official Video)'))
        self.assertTrue(is_reupload('Redbone - Lyrics'))
        self.assertFalse(is_reupload('HUMBLE. (Official Video)', wanted='humble official video'))

    def test_reupload_accounts_and_album_labels(self):
        from services.deezer import is_reupload
        self.assertTrue(is_reupload('money trees', 'sped up viral'))
        self.assertTrue(is_reupload('September', '', '', 'September (sped up + slowed)'))
        self.assertFalse(is_reupload('Sped Up', 'Some Band'))  # a song merely named that, no label

    def test_asking_for_a_version_allows_it(self):
        from services.deezer import is_reupload
        self.assertFalse(is_reupload('Redbone (Speed Up)', wanted='redbone sped up'))
        self.assertTrue(is_reupload('Redbone (Speed Up)', wanted='redbone slowed'))


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


class Preview(unittest.TestCase):
    def test_by_deezer_id_isrc_or_title(self):
        dz = fake({('/track/7', ''): {'preview': 'https://cdn/7.mp3'}, ('/track/isrc:USAAA0000001', ''): {'id': 5, 'preview': 'https://cdn/5.mp3'},
                   ('/search', 'Electric Alina Baraz'): {'data': [track(2, 'Electric', 'Alina Baraz')]}, ('/track/2', ''): {'preview': 'https://cdn/2.mp3'}})
        self.assertEqual(asyncio.run(dz.preview(deezer_id=7)), 'https://cdn/7.mp3')
        self.assertEqual(asyncio.run(dz.preview(isrc='USAAA0000001')), 'https://cdn/5.mp3')
        self.assertEqual(asyncio.run(dz.preview(title='Electric', artist='Alina Baraz')), 'https://cdn/2.mp3')

    def test_unknown_isrc_falls_back_to_title_and_nothing_found_is_none(self):
        dz = fake({('/track/isrc:USAAA0000001', ''): {'error': {'code': 800, 'message': 'no data'}},
                   ('/search', 'Electric Alina Baraz'): {'data': [track(2, 'Electric', 'Alina Baraz')]}, ('/track/2', ''): {'preview': 'https://cdn/2.mp3'}})
        self.assertEqual(asyncio.run(dz.preview(isrc='USAAA0000001', title='Electric', artist='Alina Baraz')), 'https://cdn/2.mp3')
        self.assertIsNone(asyncio.run(dz.preview(isrc='USAAA0000001')))
        self.assertIsNone(asyncio.run(fake({('/track/7', ''): {'preview': ''}}).preview(deezer_id=7)))

    def test_endpoint_returns_url_404_or_503_and_never_spends_spotify(self):
        from fastapi.testclient import TestClient
        import main
        from services import spotify_client
        before = spotify_client.searches_made
        for routes, status in (({('/track/7', ''): {'preview': 'https://cdn/7.mp3'}}, 200), ({('/track/7', ''): {'preview': ''}}, 404),
                               ({('/track/7', ''): {'error': {'code': 700}}}, 503)):
            with mock.patch.object(deezer, 'client', return_value=fake(routes)):
                r = TestClient(main.app).get('/preview/', params={'dz': 7})
            self.assertEqual(r.status_code, status)
        self.assertEqual(r.status_code, 503)
        self.assertEqual(spotify_client.searches_made, before)
        self.assertEqual(TestClient(main.app).get('/preview/', params={'isrc': 'bad'}).status_code, 422)


class SearchEndpoint(unittest.TestCase):
    """Type-ahead: Last.fm ranks (originals first), Deezer fills in, re-uploads
    drop, and no Spotify search is spent. Last.fm and Deezer are faked."""

    def run_search(self, q, lastfm, deezer_search=(), deezer_found=None, deezer_down=False):
        from fastapi.testclient import TestClient
        import main
        from services import lastfm_client, spotify_client

        async def fake_lastfm(query, limit=15):
            return lastfm

        async def fake_find_many(songs):
            return {(x['title'], x['artist']): (deezer_found or {}).get(x['title']) for x in songs}
        dz = fake({('/search', ''): {'error': {'code': 700}}} if deezer_down else {('/search', q): {'data': list(deezer_search)}})
        before = spotify_client.searches_made
        with mock.patch.object(lastfm_client, 'track_search', side_effect=fake_lastfm), \
                mock.patch.object(deezer, 'find_many', side_effect=fake_find_many), \
                mock.patch.object(deezer, 'client', return_value=dz):
            r = TestClient(main.app).get('/search/', params={'searchValue': q})
        self.assertEqual(spotify_client.searches_made, before)  # never Spotify
        return r

    def song(self, title, artist, isrc):
        return {'deezer_id': 1, 'title': title, 'artists': [artist], 'album': 'A', 'image': 'img',
                'explicit': False, 'isrc': isrc, 'duration_ms': 1000}

    def test_the_original_comes_first_and_reuploads_drop(self):
        lastfm = [{'title': 'Money Trees', 'artist': 'Kendrick Lamar', 'listeners': 2210951},
                  {'title': 'Money Trees', 'artist': 'Kendrick Lamar, Jay Rock', 'listeners': 56847},  # same song
                  {'title': 'Money Trees (Sped Up)', 'artist': 'sped up viral', 'listeners': 9000}]
        # (Kendrick leads: popular and confirmed on Deezer, though Deezer's search lacks him.)
        deezer_search = [track(9, 'money trees (sped up version)', 'sped up viral'), track(3, 'MONEY TREES', 'Rilès', isrc='FR0000000001')]
        r = self.run_search('money trees', lastfm, deezer_search, {'Money Trees': self.song('Money Trees', 'Kendrick Lamar', 'USUM71210785')})
        self.assertEqual([(t['title'], t['artists'][0]) for t in r.json()['tracks']],
                         [('Money Trees', 'Kendrick Lamar'), ('MONEY TREES', 'Rilès')])
        self.assertEqual(r.json()['tracks'][0]['id'], 'USUM71210785')

    def test_a_lastfm_hit_deezer_lacks_still_shows_with_lastfms_cover(self):
        r = self.run_search('rare', [{'title': 'Rare Cut', 'artist': 'Someone', 'listeners': 10, 'image': 'https://lastfm/cover.png'}])
        t = r.json()['tracks'][0]
        self.assertEqual((t['id'], t['isrc'], t['title'], t['image']), ('lfm:rarecut|someone', None, 'Rare Cut', 'https://lastfm/cover.png'))

    def test_lastfm_placeholder_star_is_no_cover(self):
        from services.lastfm_client import _image
        star = 'https://lastfm.freetls.fastly.net/i/u/300x300/2a96cbd8b46e442fc41c2b86b821562f.png'
        self.assertEqual(_image([{'#text': 'https://a/small.png', 'size': 'small'}, {'#text': star, 'size': 'large'}]), 'https://a/small.png')
        self.assertEqual(_image([{'#text': star}]), '')

    def test_asking_for_a_reupload_keeps_it(self):
        lastfm = [{'title': 'Redbone (Slowed)', 'artist': 'Someone', 'listeners': 10}]
        self.assertEqual(len(self.run_search('redbone slowed', lastfm).json()['tracks']), 1)

    def test_one_recording_under_several_credits_shows_once(self):
        lastfm = [{'title': 'Tadow', 'artist': a, 'listeners': 1} for a in ('Masego', 'Masego, FKJ', 'Fkj & Masego')]
        tadow = self.song('Tadow', 'Masego', 'QM24S1703810')
        r = self.run_search('tadow', lastfm, [track(1, 'Tadow', 'Masego', isrc='QM24S1703810')], {'Tadow': tadow})
        self.assertEqual([t['id'] for t in r.json()['tracks']], ['QM24S1703810'])

    def test_mid_word_lets_deezer_lead(self):
        # Last.fm only has whole-word junk mid-word: unpopular, so Deezer's prefix matches lead.
        lastfm = [{'title': 'Septem', 'artist': 'Hexis', 'listeners': 4000}]
        deezer_search = [track(1, 'September', 'Earth, Wind & Fire', isrc='USSM17800845'),
                         track(2, 'September (Speed)', 'Ren', isrc='FR0000000002')]
        r = self.run_search('septem', lastfm, deezer_search)
        self.assertEqual([t['title'] for t in r.json()['tracks']], ['September', 'Septem'])

    def test_irrelevant_results_drop(self):
        r = self.run_search('money tre', [{'title': 'HONEY (ARE U COMING?)', 'artist': 'Måneskin', 'listeners': 900000}],
                            [track(3, 'MONEY TREES', 'Rilès', isrc='FR0000000001')])
        self.assertEqual([t['title'] for t in r.json()['tracks']], ['MONEY TREES'])

    def test_artist_dash_song_uploads_drop(self):
        lastfm = [{'title': 'Kendrick Lamar - Money Trees', 'artist': 'Music', 'listeners': 900000},
                  {'title': 'Money Trees', 'artist': 'Kendrick Lamar', 'listeners': 2210951},
                  {'title': 'Kendrick Lamar - money without me (Official Audio)', 'artist': 'Kendrick Lamar', 'listeners': 5000}]
        found = {'Money Trees': self.song('Money Trees', 'Kendrick Lamar', 'USUM71210785')}
        r = self.run_search('kendrick lamar money', lastfm, [], found)
        self.assertEqual([(t['title'], t['artists'][0]) for t in r.json()['tracks']], [('Money Trees', 'Kendrick Lamar')])

    def test_uploads_naming_the_searched_artist_drop_but_features_stay(self):
        lastfm = [{'title': 'HUMBLE.', 'artist': 'Kendrick Lamar', 'listeners': 2000000},
                  {'title': 'humble by kendrick lamar', 'artist': 'John AND Jimmy', 'listeners': 100},
                  {'title': 'kendrick lamar ~ humble ﾉ slowed + reverb ﾉ', 'artist': 'rum world', 'listeners': 100},
                  {'title': 'Humble Pie (feat. Kendrick Lamar)', 'artist': 'Someone', 'listeners': 100}]
        found = {'HUMBLE.': self.song('HUMBLE.', 'Kendrick Lamar', 'USUM71703085')}
        titles = [t['title'] for t in self.run_search('kendrick lamar humble', lastfm, [], found).json()['tracks']]
        self.assertEqual(titles, ['HUMBLE.', 'Humble Pie (feat. Kendrick Lamar)'])

    def test_dashed_song_titles_stay(self):
        lastfm = [{'title': 'September - Live', 'artist': 'Earth, Wind & Fire', 'listeners': 10},
                  {'title': 'Cry for You', 'artist': 'September', 'listeners': 10}]  # a band named September
        self.assertEqual(len(self.run_search('september', lastfm).json()['tracks']), 2)

    def test_one_row_per_song_per_artist(self):
        versions = [track(1, 'Come and Get Your Love (Single Version)', 'Redbone', isrc='USAAA0000001'),
                    track(2, 'Come And Get Your Love', 'Redbone', isrc='USAAA0000002'),
                    track(3, 'Come and Get Your Love (Re-Record)', 'Redbone', isrc='USAAA0000003'),
                    track(4, 'Redbone', 'Childish Gambino', isrc='USYAH1600107')]
        r = self.run_search('redbone', [], versions)
        self.assertEqual([t['title'] for t in r.json()['tracks']], ['Come and Get Your Love (Single Version)', 'Redbone'])

    def test_lastfm_down_falls_back_to_deezer(self):
        r = self.run_search('redbone', [], [track(5, 'Redbone', 'Childish Gambino', isrc='USYAH1600107')])
        self.assertEqual([t['id'] for t in r.json()['tracks']], ['USYAH1600107'])

    def test_both_down_is_a_503(self):
        self.assertEqual(self.run_search('x', [], deezer_down=True).status_code, 503)


if __name__ == '__main__':
    unittest.main()
