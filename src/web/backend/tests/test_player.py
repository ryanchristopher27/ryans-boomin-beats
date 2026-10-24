"""Synthetic tests for routers/player.py normalization and error mapping.

Run from src/web/backend:

    python -m unittest discover tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402
from spotipy import SpotifyException  # noqa: E402

from routers.player import normalize_playback, player_error  # noqa: E402


def _playback(**over):
    p = {
        'device': {'name': 'MacBook', 'type': 'Computer'},
        'shuffle_state': True,
        'repeat_state': 'off',
        'is_playing': True,
        'timestamp': 1000,
        'context': {'type': 'playlist', 'uri': 'spotify:playlist:x'},
        'progress_ms': 16261,
        'item': {
            'type': 'track', 'id': 't1', 'name': 'Egyptian Luvr',
            'artists': [{'name': 'Rejjie Snow'}, {'name': 'Aminé'}],
            'album': {'name': 'Dear Annie', 'images': [{'url': 'big'}, {'url': 'small'}]},
            'duration_ms': 256613, 'explicit': True,
            'external_urls': {'spotify': 'https://open.spotify.com/track/t1'},
        },
        'actions': {'disallows': {'resuming': True, 'pausing': False}},
    }
    p.update(over)
    return p


class NormalizePlayback(unittest.TestCase):
    def test_nothing_playing(self):
        self.assertEqual(normalize_playback(None), {'active': False})

    def test_track(self):
        n = normalize_playback(_playback())
        self.assertTrue(n['active'])
        self.assertEqual(n['track']['title'], 'Egyptian Luvr')
        self.assertEqual(n['track']['artists'], ['Rejjie Snow', 'Aminé'])
        self.assertEqual(n['track']['image'], 'big')  # largest, unlike /get-profile/
        self.assertEqual(n['disallows'], ['resuming'])  # only truthy entries
        self.assertEqual(n['context_uri'], 'spotify:playlist:x')
        self.assertFalse(n['smart_shuffle'])

    def test_episode_has_no_track(self):
        n = normalize_playback(_playback(item={'type': 'episode', 'name': 'Pod'}))
        self.assertTrue(n['active'])
        self.assertIsNone(n['track'])

    def test_missing_optional_fields(self):
        n = normalize_playback({'is_playing': False, 'item': None, 'progress_ms': None})
        self.assertEqual(n['progress_ms'], 0)
        self.assertEqual(n['disallows'], [])
        self.assertIsNone(n['context_uri'])

    def test_album_without_images(self):
        item = dict(_playback()['item'], album={'name': 'A', 'images': []})
        self.assertEqual(normalize_playback(_playback(item=item))['track']['image'], '')


class PlayerError(unittest.TestCase):
    def test_no_device(self):
        self.assertEqual(player_error(SpotifyException(404, -1, 'Not found.')),
                         {'error': 'no_active_device'})

    def test_premium(self):
        e = SpotifyException(403, -1, 'Premium required', reason='PREMIUM_REQUIRED')
        self.assertEqual(player_error(e), {'error': 'premium_required'})

    def test_restriction_is_not_premium(self):
        e = SpotifyException(403, -1, 'Restriction violated', reason='UNKNOWN')
        self.assertEqual(player_error(e), {'error': 'restricted', 'reason': 'UNKNOWN'})

    def test_expired_token_is_401(self):
        with self.assertRaises(HTTPException) as ctx:
            player_error(SpotifyException(401, -1, 'expired'))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_other_status_raises(self):
        with self.assertRaises(HTTPException):
            player_error(SpotifyException(500, -1, 'boom'))


if __name__ == '__main__':
    unittest.main()
