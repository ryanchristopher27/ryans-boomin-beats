"""Golden queries for type-ahead (reflect 2026-10-26): the searches that broke
in production, replayed from recorded Last.fm and Deezer answers
(golden/search_fixtures.json, made by golden/record.py), so a ranking change
that fixes one query can't quietly break another. Offline; no Spotify.

    python -m unittest tests.test_search_golden -v
"""
import json
import os
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'golden', 'search_fixtures.json')

# query -> what must hold. `first`: the top row (title, lead artist), compared
# case-insensitively. `top3`: each must appear in the first three rows.
# `once`: each appears exactly once. `none`: no row title matches the regex.
GOLDEN = {
    # The original was buried under re-uploads on Deezer.
    'money trees': {'first': ('Money Trees', 'Kendrick Lamar'), 'none': r'sped|slowed|speed'},
    # Mid-word: Last.fm returned "HONEY" and "Dirty Money" by Tre Loaded.
    # (Kendrick's original is missing mid-word: see KnownGaps.)
    'money tre': {'top3': [('Money Tree', 'Olympia Vitalis')], 'none': r'^honey|^dirty money'},
    # Uploads titled "Kendrick Lamar - Money Trees" by someone else.
    'kendrick lamar money': {'first': ('Money Trees', 'Kendrick Lamar'), 'none': r'kendrick lamar'},
    'kendrick lamar humble': {'first': ('HUMBLE.', 'Kendrick Lamar'), 'none': r'^humble by|slowed'},
    # The band September must not hide the song, and no "(Speed)" versions.
    'september': {'top3': [('September', 'Earth, Wind & Fire')], 'none': r'speed|sped|slowed'},
    'septem': {'top3': [('September', 'Earth, Wind & Fire')], 'none': r'speed|sped|slowed'},
    # One recording listed under several credits.
    'tadow': {'first': ('Tadow', 'Masego'), 'once': [('Tadow', 'Masego')]},
    # Five releases of one song.
    'come and get your love': {'first': ('Come and Get Your Love', 'Redbone'), 'once': [('Come and Get Your Love', 'Redbone')]},
    'redbone': {'top3': [('Redbone', 'Childish Gambino')], 'once': [('Redbone', 'Childish Gambino')]},
    'redbo': {'top3': [('Redbone', 'Childish Gambino')]},
    # Controls: plain popular songs.
    'dancing queen': {'first': ('Dancing Queen', 'ABBA')},
    'get lucky': {'first': ('Get Lucky', 'Daft Punk')},
    # Asking for a version keeps it.
    'redbone slowed': {'top3_matches': r'slowed'},
}


def _fold(s):
    return re.sub(r'[^0-9a-z]', '', s.casefold())


def _base(title):
    """'Get Lucky (feat. Pharrell Williams...)' and 'Come And Get Your Love (Single Version)' count as the song."""
    return _fold(re.split(r'\s[\(\[-]', title)[0])


def _row(t):
    return _base(t['title']), _fold(t['artists'][0] if t['artists'] else '')


def _want(pair):
    return _base(pair[0]), _fold(pair[1])


class GoldenQueries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURES) as f:
            cls.fixtures = json.load(f)

    def run_search(self, q):
        from fastapi.testclient import TestClient
        import main
        from services import deezer, lastfm_client, spotify_client

        rec = self.fixtures[q]
        found = {(t, a): song for t, a, song in rec['deezer_found']}

        async def fake_lastfm(query, limit=15):
            return rec['lastfm']

        async def fake_find_many(songs, dz=None):
            return {(s['title'], s['artist']): found.get((s['title'], s['artist'])) for s in songs}

        dz = mock.Mock()

        async def fake_deezer_search(query, limit=10):
            return rec['deezer_search']
        dz.search = fake_deezer_search
        before = spotify_client.searches_made
        with mock.patch.object(lastfm_client, 'track_search', side_effect=fake_lastfm), \
                mock.patch.object(deezer, 'find_many', side_effect=fake_find_many), \
                mock.patch.object(deezer, 'client', return_value=dz):
            r = TestClient(main.app).get('/search/', params={'searchValue': q})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(spotify_client.searches_made, before)
        return r.json()['tracks']

    def test_every_golden_query_is_recorded(self):
        self.assertEqual(sorted(self.fixtures), sorted(GOLDEN))

    def test_golden_queries(self):
        for q, want in GOLDEN.items():
            with self.subTest(q=q):
                tracks = self.run_search(q)
                rows = [_row(t) for t in tracks]
                shown = [f"{t['title']} — {', '.join(t['artists'])}" for t in tracks]
                self.assertTrue(rows, f'no results for {q!r}')
                if 'first' in want:
                    self.assertEqual(rows[0], _want(want['first']), shown)
                for pair in want.get('top3', []):
                    self.assertIn(_want(pair), rows[:3], shown)
                for pair in want.get('once', []):
                    self.assertEqual(rows.count(_want(pair)), 1, shown)
                if 'none' in want:
                    bad = [s for s, t in zip(shown, tracks) if re.search(want['none'], t['title'], re.I)]
                    self.assertFalse(bad, shown)
                if 'top3_matches' in want:
                    self.assertTrue(any(re.search(want['top3_matches'], t['title'], re.I) for t in tracks[:3]), shown)

    def test_every_query_shows_one_row_per_song_with_a_cover(self):
        for q in GOLDEN:
            with self.subTest(q=q):
                tracks = self.run_search(q)
                keys = [(_fold(t['title']), _fold(t['artists'][0] if t['artists'] else '')) for t in tracks]
                self.assertEqual(len(keys), len(set(keys)), keys)
                # Bare Last.fm rows (`lfm:`, too niche for Deezer) may have no art anywhere.
                self.assertEqual([t['title'] for t in tracks if not t['image'] and not t['id'].startswith('lfm:')], [])


class KnownGaps(GoldenQueries):
    """Wanted but not yet true. When one starts passing, move it into GOLDEN."""

    test_golden_queries = test_every_query_shows_one_row_per_song_with_a_cover = test_every_golden_query_is_recorded = None

    @unittest.expectedFailure
    def test_mid_word_finds_the_original(self):
        # Last.fm matches whole words only and Deezer's prefix search lacks Kendrick.
        rows = [_row(t) for t in self.run_search('money tre')]
        self.assertIn(_want(('Money Trees', 'Kendrick Lamar')), rows[:3])


if __name__ == '__main__':
    unittest.main()
