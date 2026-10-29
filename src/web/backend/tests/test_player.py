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

from routers import player  # noqa: E402
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


class RateLimits(unittest.TestCase):
    """Tracker 477d21: player 429s back everyone off; tabs share one call."""

    def setUp(self):
        from unittest import mock
        from fastapi.testclient import TestClient
        import main
        from services.spotify_auth import get_spotify_token
        player._player_locked_until = 0.0
        player._state_cache.clear()
        self.calls = 0
        self.volumes = []
        self.fail_with = None
        outer = self

        class FakeSpotify:
            def current_playback(self):
                outer.calls += 1
                if outer.fail_with:
                    raise outer.fail_with
                return None

            def pause_playback(self):
                pass
            start_playback = next_track = previous_track = pause_playback

            def volume(self, percent):
                outer.volumes.append(percent)
                if outer.fail_with:
                    raise outer.fail_with
        self.patch = mock.patch.object(player, 'user_client', return_value=FakeSpotify())
        self.patch.start()
        main.app.dependency_overrides[get_spotify_token] = lambda: 'tok'
        self.client = TestClient(main.app)
        self.addCleanup(self.patch.stop)
        self.addCleanup(main.app.dependency_overrides.clear)

    def test_tabs_polling_together_share_one_spotify_call(self):
        for _ in range(3):
            self.assertEqual(self.client.get('/player/state/').json(), {'active': False})
        self.assertEqual(self.calls, 1)

    def test_a_429_backs_everyone_off_for_retry_after(self):
        self.fail_with = SpotifyException(429, -1, 'too many', headers={'Retry-After': '7'})
        r = self.client.get('/player/state/')
        self.assertEqual((r.status_code, r.json()['retry_after'], r.headers['Retry-After']), (503, 7, '7'))
        player._state_cache.clear()
        r = self.client.get('/player/state/')  # still locked: Spotify isn't called again
        self.assertEqual(r.status_code, 503)
        self.assertEqual(self.calls, 1)

    def test_a_command_clears_the_cached_state(self):
        self.client.get('/player/state/')
        self.client.post('/player/pause/')
        self.client.get('/player/state/')
        self.assertEqual(self.calls, 2)

    def test_lockouts_are_capped(self):
        self.fail_with = SpotifyException(429, -1, 'too many', headers={'Retry-After': '86400'})
        self.assertEqual(self.client.get('/player/state/').json()['retry_after'], player._MAX_LOCKOUT)

    def test_volume_sets_the_device_volume(self):
        self.assertEqual(self.client.post('/player/volume/', json={'percent': 20}).json(), {'ok': True})
        self.assertEqual(self.volumes, [20])

    def test_volume_is_validated_at_the_boundary(self):
        for body in ({'percent': 101}, {'percent': -1}, {'percent': 'loud'}, {}, {'percent': 5, 'x': 1}):
            self.assertEqual(self.client.post('/player/volume/', json=body).status_code, 422)
        self.assertEqual(self.volumes, [])

    def test_volume_maps_player_errors_and_backs_off_on_429(self):
        self.fail_with = SpotifyException(404, -1, 'Not found.')
        self.assertEqual(self.client.post('/player/volume/', json={'percent': 20}).json(), {'error': 'no_active_device'})
        self.fail_with = SpotifyException(429, -1, 'too many', headers={'Retry-After': '9'})
        r = self.client.post('/player/volume/', json={'percent': 20})
        self.assertEqual((r.status_code, r.json()['retry_after']), (503, 9))
        self.client.post('/player/volume/', json={'percent': 20})  # locked out: Spotify isn't called again
        self.assertEqual(len(self.volumes), 2)

    def test_state_reports_the_device_volume(self):
        n = normalize_playback(_playback(device={'name': 'MacBook', 'type': 'Computer', 'volume_percent': 63}))
        self.assertEqual(n['device']['volume'], 63)


if __name__ == '__main__':
    unittest.main()
