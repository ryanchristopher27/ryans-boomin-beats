"""Search-count tests for services/spotify_validator.py (no network).

Run from src/web/backend:

    python -m unittest discover tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import spotify_validator  # noqa: E402

_TRACK = {'id': 't', 'name': 'A', 'artists': [{'name': 'X'}], 'album': {'name': 'Al', 'images': []},
          'external_urls': {'spotify': 'u'}, 'duration_ms': 1, 'explicit': False}


class FakeSpotify:
    def __init__(self, hits):
        self.hits, self.calls = hits, []

    def search(self, q, limit, type):
        self.calls.append(q)
        return {'tracks': {'items': [_TRACK] if q in self.hits else []}}


class SearchOne(unittest.TestCase):
    def setUp(self):
        spotify_validator._CACHE.clear()

    def test_hit_is_cached(self):
        sp = FakeSpotify({'track:A artist:X'})
        self.assertEqual(spotify_validator._search_one(sp, 'A', 'X')['id'], 't')
        spotify_validator._search_one(sp, 'a', 'x')  # case-insensitive key
        self.assertEqual(len(sp.calls), 1)

    def test_no_fallback_saves_a_search_and_caches_the_miss(self):
        sp = FakeSpotify(set())
        self.assertIsNone(spotify_validator._search_one(sp, 'A', 'X', fallback=False))
        self.assertIsNone(spotify_validator._search_one(sp, 'A', 'X', fallback=False))
        self.assertEqual(sp.calls, ['track:A artist:X'])

    def test_fallback_still_used_by_default(self):
        sp = FakeSpotify({'track:A'})
        self.assertEqual(spotify_validator._search_one(sp, 'A', 'X')['id'], 't')
        self.assertEqual(sp.calls, ['track:A artist:X', 'track:A'])

    def test_errors_are_not_cached(self):
        class Failing(FakeSpotify):
            def search(self, q, limit, type):
                raise RuntimeError('429')
        with self.assertRaises(RuntimeError):
            spotify_validator._search_one(Failing(set()), 'A', 'X')
        self.assertEqual(spotify_validator._CACHE, {})


if __name__ == '__main__':
    unittest.main()
