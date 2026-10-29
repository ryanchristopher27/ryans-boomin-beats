import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop('DEVICE_KEY', None)

from fastapi.testclient import TestClient

import main
from services import lastfm_client
from services.llm_client import LLMClient, NeedsLLM

HELPER = {'X-LLM-Provider': 'helper'}


class Relay(unittest.IsolatedAsyncioTestCase):
    async def test_replies_are_used_in_order_then_it_asks(self):
        c = LLMClient('helper', '', replies=('one', 'two'))
        self.assertEqual(await c.generate([{'role': 'user', 'content': 'a'}], 'sys'), 'one')
        self.assertEqual(await c.generate([{'role': 'user', 'content': 'b'}], 'sys'), 'two')
        with self.assertRaises(NeedsLLM) as e:
            await c.generate([{'role': 'user', 'content': 'c'}], 'sys')
        self.assertEqual(e.exception.prompt, 'sys\n\nc')


class RelayRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_recap_answers_428_with_the_prompt_then_uses_the_reply(self):
        body = {'songs': [{'id': 'a', 'title': 'Lovely Day', 'artist': 'Bill Withers'}]}
        r = self.client.post('/dj/recap/', json=body, headers=HELPER)
        self.assertEqual(r.status_code, 428)
        self.assertIn('Lovely Day', r.json()['needs_llm']['prompt'])
        r = self.client.post('/dj/recap/', json={**body, 'llm_replies': ['"A sunny soul night."']}, headers=HELPER)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['recap'], 'A sunny soul night.')

    def test_bad_replies_are_refused(self):
        body = {'songs': [{'id': 'a', 'title': 'x', 'artist': 'y'}], 'llm_replies': 'not a list'}
        self.assertEqual(self.client.post('/dj/recap/', json=body, headers=HELPER).status_code, 400)

    def test_song_profile_relays_one_grounded_call(self):
        info = {**lastfm_client._empty(), 'tags': [{'name': 'soul'}]}
        with patch('routers.song_profile.lastfm_client.track_info', AsyncMock(return_value=info)):
            r = self.client.post('/song/profile/?title=Lovely%20Day&artist=Bill%20Withers', json={}, headers=HELPER)
            self.assertEqual(r.status_code, 428)
            self.assertIn('soul', r.json()['needs_llm']['prompt'])

    def test_a_helper_failure_degrades_like_any_provider(self):
        info = lastfm_client._empty()
        with patch('routers.song_profile.lastfm_client.track_info', AsyncMock(return_value=info)):
            r = self.client.post('/song/profile/?title=a&artist=b', json={'llm_error': "Can't reach your Claude Code helper."}, headers=HELPER)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['analysis_error'], "Can't reach your Claude Code helper.")

    def test_a_helper_key_is_never_required(self):
        # No X-LLM-Key, and no local Claude Code check (that's 'claude-code' only).
        r = self.client.post('/dj/recap/', json={'songs': []}, headers=HELPER)
        self.assertNotIn(r.status_code, (400, 401))


if __name__ == '__main__':
    unittest.main()
