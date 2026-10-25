"""Tests for shared DJ state (SY1): optimistic concurrency, user scoping, the
primary role, heartbeat throttling and request bounds. Supabase and Spotify
are faked; nothing here touches the network.

Run from src/web/backend:

    python -m unittest discover tests -v
"""
import os
import sys
import unittest
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from routers import dj_state  # noqa: E402
from services import dj_store  # noqa: E402
from services.dj_store import Conflict, heartbeat_due, now, primary_info  # noqa: E402
from services.spotify_identity import current_user  # noqa: E402


class FakeStore:
    """In-memory stand-in with the same conditional-update semantics."""

    def __init__(self):
        self.rows, self.heartbeats = {}, 0

    def read(self, user):
        return self.rows.get(user)

    def create(self, user, state, device, label):
        if user in self.rows:
            raise Conflict()
        self.rows[user] = {'spotify_user_id': user, 'version': 1, 'state': state, 'primary_device': device,
                           'primary_label': label, 'primary_seen_at': now().isoformat() if device else None}
        return self.rows[user]

    def update(self, user, state, expected):
        row = self.rows.get(user)
        if not row or row['version'] != expected:
            raise Conflict()
        row.update(state=state, version=expected + 1)
        return row

    def claim_primary(self, user, device, label):
        row = self.rows.get(user)
        if row:
            row.update(primary_device=device, primary_label=label, primary_seen_at=now().isoformat())
        return row

    def heartbeat(self, user, device):
        self.heartbeats += 1


def _doc(title='A'):
    return {'state': {'queue': {'upcoming': [{'id': 'u1', 'trackID': 't1', 'title': title}]}}}


class SyncAPI(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        self.user = 'alice'
        main.app.dependency_overrides[dj_state.get_store] = lambda: self.store
        main.app.dependency_overrides[current_user] = lambda: self.user
        self.client = TestClient(main.app)

    def tearDown(self):
        main.app.dependency_overrides.clear()

    def put(self, version, body=None, device='phone'):
        return self.client.put('/dj/state', json=body or _doc(),
                               headers={'If-Match': str(version), 'X-DJ-Device': device, 'X-DJ-Label': 'iPhone'})

    def test_empty_state_reads_as_version_zero(self):
        self.assertEqual(self.client.get('/dj/state').json(), {'version': 0, 'state': None, 'primary': None})

    def test_first_write_seeds_and_makes_the_device_primary(self):
        r = self.put(0)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['version'], 1)
        self.assertEqual(r.json()['primary']['device'], 'phone')
        self.assertTrue(r.json()['primary']['online'])

    def test_stale_write_gets_409_with_the_current_document(self):
        self.put(0)
        self.assertEqual(self.put(1, _doc('phone edit')).status_code, 200)
        r = self.put(1, _doc('web edit'), device='web')  # based on v1, row is now v2
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()['version'], 2)
        self.assertEqual(r.json()['state']['queue']['upcoming'][0]['title'], 'phone edit')

    def test_seeding_twice_conflicts(self):
        self.put(0)
        self.assertEqual(self.put(0, device='web').status_code, 409)

    def test_users_are_scoped_by_token_identity(self):
        self.put(0)
        self.user = 'bob'
        self.assertEqual(self.client.get('/dj/state').json()['version'], 0)

    def test_drive_from_here_moves_the_primary(self):
        self.put(0)
        r = self.client.post('/dj/primary', json={'device': 'web', 'label': 'MacBook web'})
        self.assertEqual(r.json()['primary']['device'], 'web')
        self.assertEqual(r.json()['version'], 1)  # claiming doesn't touch the document

    def test_claim_without_a_session_is_404(self):
        self.assertEqual(self.client.post('/dj/primary', json={'device': 'web'}).status_code, 404)

    def test_document_is_validated_and_bounded(self):
        bad = [
            {'state': {'queue': {'upcoming': [{'id': 'u', 'trackID': 't', 'title': 'x', 'mystery': 1}]}}},
            {'state': {'surprise': {}}},
            {'state': {'options': {'mode': 'autopilot'}}},
            {'state': {'queue': {'upcoming': [{'id': f'u{i}', 'trackID': 't', 'title': 'x'} for i in range(201)]}}},
            {'state': {'options': {'goal': {'kind': 'arc', 'minutes': 1, 'startedAt': '2026-10-25T00:00:00Z'}}}},
        ]
        for body in bad:
            self.assertEqual(self.put(0, body).status_code, 422, body)

    def test_if_match_is_required(self):
        self.assertEqual(self.client.put('/dj/state', json=_doc()).status_code, 422)

    def test_unconfigured_server_answers_503(self):
        main.app.dependency_overrides.pop(dj_state.get_store)
        original = dj_state.SYNC_ENABLED
        dj_state.SYNC_ENABLED = False
        try:
            self.assertEqual(self.client.get('/dj/state').status_code, 503)
        finally:
            dj_state.SYNC_ENABLED = original


class Primary(unittest.TestCase):
    def row(self, seconds_ago):
        return {'primary_device': 'phone', 'primary_label': 'iPhone',
                'primary_seen_at': (now() - timedelta(seconds=seconds_ago)).isoformat()}

    def test_online_until_sixty_seconds_of_silence(self):
        self.assertTrue(primary_info(self.row(59))['online'])
        self.assertFalse(primary_info(self.row(61))['online'])

    def test_heartbeat_written_at_most_every_fifteen_seconds(self):
        self.assertFalse(heartbeat_due(self.row(5), 'phone'))
        self.assertTrue(heartbeat_due(self.row(16), 'phone'))

    def test_only_the_primary_heartbeats(self):
        self.assertFalse(heartbeat_due(self.row(30), 'web'))

    def test_no_primary(self):
        self.assertIsNone(primary_info({'primary_device': None}))


class PlayerPiggyback(unittest.TestCase):
    def test_sync_failure_never_breaks_player_state(self):
        from routers import player
        original = dj_state.get_store

        def boom():
            raise HTTPException(status_code=503)
        dj_state.get_store = boom
        try:
            self.assertIsNone(player.dj_status('token', 'phone'))
        finally:
            dj_state.get_store = original


if __name__ == '__main__':
    unittest.main()
