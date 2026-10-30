import os
import sys
import unittest
from datetime import datetime, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop('DEVICE_KEY', None)

from fastapi.testclient import TestClient

import main
from services import history_store

NOW = datetime(2026, 10, 29, 18, 0, tzinfo=timezone.utc)  # a Thursday


def play(ts, artist='A', ms=180000):
    return {'played_at': ts, 'artist': artist, 'duration_ms': ms}


class Stats(unittest.TestCase):
    def test_local_time_buckets_weeks_streak(self):
        plays = [
            play('2026-10-26T01:30:00Z', 'Drake'),     # Mon 01:30 UTC = Sun 20:30 in UTC-5
            play('2026-10-28T23:00:00Z', 'Drake'),     # Wed 18:00 local
            play('2026-10-29T15:00:00Z', 'Mac Miller', 240000),  # Thu 10:00 local
        ]
        s = history_store.stats(plays, tz_offset_min=300, now=NOW)
        self.assertEqual(s['plays'], 3)
        self.assertEqual(s['minutes'], 10)
        self.assertEqual(s['hours'][20], 1)
        self.assertEqual(s['hours'][18], 1)
        self.assertEqual(s['days'][0], 1)  # the first play is Sunday locally
        self.assertEqual(s['streak'], 2)   # Wed + Thu (Sun is not adjacent)
        self.assertEqual(s['top_artist'], 'Drake')
        this_week, last_week = s['weeks'][-1], s['weeks'][-2]
        self.assertEqual(this_week['start'], '2026-10-26')
        self.assertEqual((this_week['plays'], this_week['artists']), (2, 2))
        self.assertEqual(last_week['plays'], 1)  # Sunday belongs to the week before

    def test_empty(self):
        s = history_store.stats([], now=NOW)
        self.assertEqual((s['plays'], s['streak'], s['since']), (0, 0, None))

    def test_rows_skip_items_without_a_track_id(self):
        items = [{'played_at': 't1', 'track': {'id': 'x', 'name': 'Song', 'artists': [{'name': 'A'}], 'duration_ms': 1000}},
                 {'played_at': 't2', 'track': {'id': None, 'name': 'Local file'}}]
        self.assertEqual([r['track_id'] for r in history_store.rows_from_recent('u', items)], ['x'])


class Routes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.items = [{'played_at': '2026-10-29T15:00:00Z', 'track': {'id': 'x', 'name': 'Song', 'artists': [{'name': 'A'}], 'duration_ms': 1000}}]
        spotify = mock.MagicMock()
        spotify.current_user_recently_played.return_value = {'items': self.items}
        self.patches = [mock.patch('routers.spotify_actions.user_client', return_value=spotify),
                        mock.patch('routers.spotify_actions.spotify_identity.user_id', return_value='u1')]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_recently_played_saves_and_returns_history(self):
        with mock.patch.object(history_store, 'save') as save, mock.patch.object(history_store, 'plays_since', return_value=[play('2026-10-29T15:00:00Z')]):
            r = self.client.get('/spotify/recently-played/?tz=300', headers={'Authorization': 'Bearer t'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(save.call_args[0][0][0]['spotify_user_id'], 'u1')
        self.assertEqual(r.json()['history']['plays'], 1)
        self.assertEqual(r.json()['played_at'], ['2026-10-29T15:00:00Z'])

    def test_storage_down_still_answers_with_spotifys_plays(self):
        with mock.patch.object(history_store, 'save', side_effect=history_store.Unavailable('off')):
            r = self.client.get('/spotify/recently-played/', headers={'Authorization': 'Bearer t'})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()['history'])
        self.assertEqual(r.json()['count'], 1)

    def test_sync(self):
        with mock.patch.object(history_store, 'save'):
            r = self.client.post('/history/sync/', headers={'Authorization': 'Bearer t'})
        self.assertEqual(r.json(), {'stored': True, 'seen': 1})


if __name__ == '__main__':
    unittest.main()
