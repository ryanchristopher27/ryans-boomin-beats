"""The hosted instance's guard (main.require_device_key): the iOS app's device
key, or a Spotify token for an allowlisted account (the hosted web app)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

KEY = 'test-device-key'


def lookup(token):
    """A fake Spotify /me: 'alice-token' is alice, 'expired' is a dead token."""
    if token == 'expired':
        raise HTTPException(status_code=401, detail='Spotify session expired. Log in again.')
    return {'alice-token': 'alice', 'mallory-token': 'mallory'}[token]


class Guard(unittest.TestCase):
    def setUp(self):
        patches = [
            mock.patch.object(main, 'DEVICE_KEY', KEY),
            mock.patch.object(main, 'ALLOWED_SPOTIFY_USERS', {'alice'}),
            mock.patch.object(main.spotify_identity, 'user_id', side_effect=lookup),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.client = TestClient(main.app)

    def get(self, **headers):
        # A guarded route that needs nothing else: unknown paths 404 once past the guard.
        return self.client.get('/no-such-route/', headers=headers).status_code

    def test_device_key_passes(self):
        self.assertEqual(self.get(**{'x-device-key': KEY}), 404)

    def test_wrong_device_key_and_nothing_are_rejected(self):
        self.assertEqual(self.get(**{'x-device-key': 'nope'}), 401)
        self.assertEqual(self.get(), 401)

    def test_allowlisted_spotify_account_passes(self):
        self.assertEqual(self.get(authorization='Bearer alice-token'), 404)

    def test_other_spotify_accounts_are_refused(self):
        self.assertEqual(self.get(authorization='Bearer mallory-token'), 403)

    def test_expired_token_says_so(self):
        self.assertEqual(self.get(authorization='Bearer expired'), 401)

    def test_bearer_path_is_off_without_an_allowlist(self):
        with mock.patch.object(main, 'ALLOWED_SPOTIFY_USERS', set()):
            self.assertEqual(self.get(authorization='Bearer alice-token'), 401)

    def test_preflight_and_root_stay_open(self):
        self.assertNotEqual(self.client.options('/search/', headers={'Origin': 'http://127.0.0.1:5173', 'Access-Control-Request-Method': 'GET'}).status_code, 401)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_local_instance_has_no_guard(self):
        with mock.patch.object(main, 'DEVICE_KEY', ''):
            self.assertEqual(self.get(), 404)


if __name__ == '__main__':
    unittest.main()
