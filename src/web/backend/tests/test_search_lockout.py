"""Search lockout (services/spotify_client.search): after Spotify 429s a search,
no further searches are sent until its Retry-After passes. No network.

Run from src/web/backend:

    python -m unittest discover tests -v
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spotipy import SpotifyException  # noqa: E402

from services import spotify_client  # noqa: E402


class FakeSpotify:
    def __init__(self, fail_with=None):
        self.calls, self.fail_with = 0, fail_with

    def search(self, **kwargs):
        self.calls += 1
        if self.fail_with:
            raise self.fail_with
        return {'tracks': {'items': []}}


def quota_429(retry_after='120'):
    return SpotifyException(429, -1, 'Too many requests', reason='QUOTA_EXCEEDED',
                            headers={'Retry-After': retry_after})


class SearchLockout(unittest.TestCase):
    def setUp(self):
        spotify_client._search_locked_until = 0.0

    def tearDown(self):
        spotify_client._search_locked_until = 0.0

    def test_passes_through_when_not_locked(self):
        sp = FakeSpotify()
        spotify_client.search(sp, q='x')
        self.assertEqual(sp.calls, 1)
        self.assertEqual(spotify_client.search_lockout_remaining(), 0)

    def test_a_429_locks_out_later_searches_without_calling_spotify(self):
        with self.assertRaises(SpotifyException):
            spotify_client.search(FakeSpotify(fail_with=quota_429('120')), q='x')
        self.assertGreater(spotify_client.search_lockout_remaining(), 100)
        sp = FakeSpotify()
        with self.assertRaises(SpotifyException) as ctx:
            spotify_client.search(sp, q='y')
        self.assertEqual(sp.calls, 0)                     # never reached Spotify
        self.assertEqual(ctx.exception.http_status, 429)  # main.py maps it to 503 as before

    def test_lockout_expires(self):
        with self.assertRaises(SpotifyException):
            spotify_client.search(FakeSpotify(fail_with=quota_429('5')), q='x')
        with mock.patch.object(spotify_client.time, 'monotonic', return_value=spotify_client._search_locked_until + 1):
            sp = FakeSpotify()
            spotify_client.search(sp, q='y')
        self.assertEqual(sp.calls, 1)

    def test_bad_or_huge_retry_after_is_bounded(self):
        with self.assertRaises(SpotifyException):
            spotify_client.search(FakeSpotify(fail_with=quota_429('not-a-number')), q='x')
        self.assertLessEqual(spotify_client.search_lockout_remaining(), 60)
        spotify_client._search_locked_until = 0.0
        with self.assertRaises(SpotifyException):
            spotify_client.search(FakeSpotify(fail_with=quota_429('9999999')), q='x')
        self.assertLessEqual(spotify_client.search_lockout_remaining(), 24 * 60 * 60)

    def test_other_errors_do_not_lock(self):
        with self.assertRaises(SpotifyException):
            spotify_client.search(FakeSpotify(fail_with=SpotifyException(500, -1, 'boom')), q='x')
        self.assertEqual(spotify_client.search_lockout_remaining(), 0)


if __name__ == '__main__':
    unittest.main()
