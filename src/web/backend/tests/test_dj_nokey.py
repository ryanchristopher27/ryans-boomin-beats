"""F3e: /dj/suggest/ without an AI key falls back to Last.fm similar tracks,
checked on Deezer like every other pick. Offline: both services are faked."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from routers import dj  # noqa: E402
from services import lastfm_client  # noqa: E402

SIMILAR = [
    {'title': 'Sunday Best', 'artist': 'Surfaces', 'match': 1.0},
    {'title': '4EVA', 'artist': 'KAYTRANADA', 'match': 0.9},  # now playing: excluded
    {'title': 'Pink + White', 'artist': 'Frank Ocean', 'match': 0.8},
]


async def fake_info(title, artist):
    return {'tags': [{'name': 'house'}]}


async def fake_similar(title, artist, limit=30):
    return SIMILAR


async def fake_validate(batch, fallback=False):
    found = [{**e, 'spotify': {'id': f'dz:{e["title"]}', 'isrc': None, 'title': e['title'], 'artists': [e['artist']], 'image': '', 'explicit': False}} for e in batch]
    return found, []


class NoKeyDJ(unittest.TestCase):
    def setUp(self):
        for p in [
            mock.patch.object(main, 'DEVICE_KEY', ''),
            mock.patch.object(lastfm_client, 'track_info', side_effect=fake_info),
            mock.patch.object(lastfm_client, 'track_similar', side_effect=fake_similar),
            mock.patch.object(dj, '_spotify_recent', return_value=[]),
            mock.patch.object(dj, 'deezer_validate', side_effect=fake_validate),
        ]:
            p.start()
            self.addCleanup(p.stop)
        self.client = TestClient(main.app)

    def post(self, headers=None):
        body = {'now_playing': {'title': '4EVA', 'artist': 'KAYTRANADA'}}
        return self.client.post('/dj/suggest/', json=body, headers={'Authorization': 'Bearer t', **(headers or {})})

    def test_without_a_key_picks_come_from_lastfm(self):
        r = self.post()
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['source'], 'lastfm')
        self.assertEqual([m['move'] for m in data['moves']], ['similar'])
        titles = [t['title'] for t in data['moves'][0]['tracks']]
        self.assertEqual(titles, ['Sunday Best', 'Pink + White'])  # now playing left out

    def test_nothing_similar_says_why(self):
        with mock.patch.object(lastfm_client, 'track_similar', side_effect=_empty):
            data = self.post().json()
        self.assertEqual(data['moves'], [])
        self.assertIn('Add an AI key', data['error'])


async def _empty(*args, **kwargs):
    return []


if __name__ == '__main__':
    unittest.main()
