"""'Your Claude Code' provider: availability, keyless credentials, and the CLI's
result envelope. The CLI itself is never run here.

    python -m unittest tests.test_claude_code -v
"""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402

from services import claude_code  # noqa: E402
from services.claude_code import ClaudeCodeError, parse_result  # noqa: E402
from services.llm_auth import get_llm_credentials, get_optional_llm_credentials  # noqa: E402


class Availability(unittest.TestCase):
    def test_never_on_vercel(self):
        with mock.patch.dict(os.environ, {'VERCEL': '1'}), mock.patch('shutil.which', return_value='/bin/claude'):
            self.assertFalse(claude_code.available())

    def test_needs_the_cli(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch('shutil.which', return_value=None):
            self.assertFalse(claude_code.available())

    def test_can_be_switched_off(self):
        with mock.patch.dict(os.environ, {'CLAUDE_CODE': '0'}), mock.patch('shutil.which', return_value='/bin/claude'):
            self.assertFalse(claude_code.available())


class Credentials(unittest.TestCase):
    def test_keyless_when_available(self):
        with mock.patch.object(claude_code, 'available', return_value=True):
            creds = get_llm_credentials(x_llm_provider='claude-code', x_llm_key=None)
        self.assertEqual((creds.provider, creds.api_key), ('claude-code', ''))

    def test_refused_where_unavailable(self):
        with mock.patch.object(claude_code, 'available', return_value=False):
            with self.assertRaises(HTTPException) as ctx:
                get_llm_credentials(x_llm_provider='claude-code', x_llm_key=None)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_other_providers_still_need_a_key(self):
        with self.assertRaises(HTTPException) as ctx:
            get_llm_credentials(x_llm_provider='groq', x_llm_key=None)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIsNone(get_optional_llm_credentials(x_llm_provider='claude', x_llm_key=None))


class Envelope(unittest.TestCase):
    def test_result_text(self):
        self.assertEqual(parse_result(0, json.dumps({'result': '{"hold": []}', 'is_error': False}), ''), '{"hold": []}')

    def test_error_flag_with_exit_zero(self):
        with self.assertRaises(ClaudeCodeError):
            parse_result(0, json.dumps({'is_error': True, 'result': 'boom'}), '')

    def test_expired_login_reads_as_a_fix(self):
        out = json.dumps({'is_error': True, 'result': 'Failed to authenticate: OAuth session expired'})
        with self.assertRaises(ClaudeCodeError) as ctx:
            parse_result(1, out, '')
        self.assertIn('/login', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
