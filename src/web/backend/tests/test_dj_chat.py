import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop('DEVICE_KEY', None)

from fastapi.testclient import TestClient

import main
from routers.dj_chat import clean_actions

HELPER = {'X-LLM-Provider': 'helper'}
WIDGETS = [{'type': t, 'title': t, 'minW': 3, 'minH': 3} for t in ('nowPlaying', 'controls', 'moves', 'move', 'upNext')]


class CleanActions(unittest.TestCase):
    def test_keeps_valid_actions_and_drops_the_rest(self):
        raw = [
            {'type': 'preset', 'name': 'compass'},
            {'type': 'preset', 'name': 'disco'},
            {'type': 'layout', 'items': [{'type': 'moves', 'x': 0, 'y': 0, 'w': 8, 'h': 10}, {'type': 'move', 'kind': 'lift', 'x': 8, 'y': 0, 'w': 4, 'h': 5},
                                         {'type': 'move', 'kind': 'nope', 'x': 0, 'y': 0, 'w': 3, 'h': 3}, {'type': 'bogus', 'x': 0, 'y': 0, 'w': 3, 'h': 3}]},
            {'type': 'controls', 'mode': 'driver', 'adventurousness': 4, 'familiar': 'x'},
            {'type': 'goal', 'goal': {'kind': 'drift'}},
            {'type': 'goal', 'goal': {'kind': 'moon'}},
            {'type': 'refresh_moves', 'note': '  more upbeat  '},
            {'type': 'rm -rf'},
        ]
        out = clean_actions(raw, {w['type'] for w in WIDGETS})
        self.assertEqual([a['type'] for a in out], ['preset', 'layout', 'controls', 'goal', 'refresh_moves'])
        self.assertEqual(len(out[1]['items']), 2)
        self.assertEqual(out[2], {'type': 'controls', 'mode': 'driver', 'adventurousness': 1.0})
        self.assertEqual(out[4]['note'], 'more upbeat')


class Route(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.body = {'message': 'more 90s hip hop and put up next on the left', 'now_playing': {'title': '4EVA', 'artist': 'KAYTRANADA'}, 'widgets': WIDGETS,
                     'layout': [{'type': 'moves', 'x': 0, 'y': 0, 'w': 8, 'h': 10}]}

    def test_relays_then_returns_reply_checked_picks_and_actions(self):
        r = self.client.post('/dj/chat/', json=self.body, headers=HELPER)
        self.assertEqual(r.status_code, 428)
        self.assertIn('put up next on the left', r.json()['needs_llm']['prompt'])
        reply = json.dumps({'reply': 'On it.', 'picks': [{'title': 'Juicy', 'artist': 'The Notorious B.I.G.', 'reason': '90s classic.'}],
                            'actions': [{'type': 'preset', 'name': 'focus'}]})
        found = [{'title': 'Juicy', 'artist': 'The Notorious B.I.G.', 'spotify': {'id': 'dz:1', 'title': 'Juicy', 'artists': ['The Notorious B.I.G.'], 'image': '', 'isrc': 'USAR19400001', 'explicit': True}}]
        with patch('routers.dj.deezer_validate', AsyncMock(return_value=(found, []))):
            r = self.client.post('/dj/chat/', json={**self.body, 'llm_replies': [reply]}, headers=HELPER)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d['reply'], 'On it.')
        self.assertEqual([p['title'] for p in d['picks']], ['Juicy'])
        self.assertEqual(d['actions'], [{'type': 'preset', 'name': 'focus'}])

    def test_plain_text_answer_is_a_reply(self):
        r = self.client.post('/dj/chat/', json={**self.body, 'llm_replies': ['Sure, sounds fun!']}, headers=HELPER)
        self.assertEqual(r.json(), {'reply': 'Sure, sounds fun!', 'picks': [], 'actions': []})

    def test_needs_an_ai(self):
        self.assertEqual(self.client.post('/dj/chat/', json=self.body).status_code, 401)


if __name__ == '__main__':
    unittest.main()
