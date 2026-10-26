"""'Your Claude Code' as an LLM provider: the local backend runs the owner's own
`claude` CLI on their Claude subscription, so there's no API key or bill.

Mirrors Trip Fairy's helper (packages/helper/lib/core.mjs), text in, text out:
no tools, no MCP servers, no user settings or hooks, an empty temp dir as cwd,
the prompt over stdin (never argv), no saved session. Only available where the
CLI is installed and never on Vercel, which has neither the CLI nor the login.
"""
import asyncio
import json
import os
import re
import shutil
import tempfile

TIMEOUT_S = 120
# Sonnet: fast enough for a per-track prefetch, strong enough for the DJ's JSON.
MODEL = 'sonnet'

_LOGIN_TROUBLE = re.compile(
    r'failed to authenticate|oauth|not logged in|log ?in again|/login|session expired|authentication[_ ]error', re.I)


class ClaudeCodeError(Exception):
    pass


def available() -> bool:
    if os.environ.get('VERCEL') or os.environ.get('CLAUDE_CODE') == '0':
        return False
    return shutil.which('claude') is not None


_sandbox: str | None = None
# Each call is a whole CLI process; a burst (several tabs, a profile plus a
# suggestion round) would otherwise spawn one per request (review S3).
_gate: asyncio.Semaphore | None = None


def _semaphore() -> asyncio.Semaphore:
    global _gate
    if _gate is None:
        _gate = asyncio.Semaphore(2)
    return _gate


def _cwd() -> str:
    global _sandbox
    if _sandbox is None:
        _sandbox = tempfile.mkdtemp(prefix='boomin-beats-claude-')
    return _sandbox


def _failure(text: str) -> ClaudeCodeError:
    if _LOGIN_TROUBLE.search(text or ''):
        return ClaudeCodeError('Your Claude Code needs you to sign in again: run `claude` in a terminal, then /login.')
    return ClaudeCodeError(text or 'Claude Code returned an error.')


def parse_result(code: int, out: str, err: str) -> str:
    """The CLI can exit 0 yet flag failure in its JSON envelope, so check both."""
    try:
        env = json.loads(out)
    except ValueError:
        env = None
    if isinstance(env, dict) and env.get('is_error'):
        raise _failure(str(env.get('result') or ''))
    if code != 0:
        raise _failure(err.strip() or (str(env.get('result')) if isinstance(env, dict) else '') or f'claude exited {code}')
    if isinstance(env, dict):
        return str(env.get('result') or '')
    return out.strip()


async def run(prompt: str, system_prompt: str) -> str:
    if not available():
        raise ClaudeCodeError('Your Claude Code only works when the backend runs on your own Mac.')
    async with _semaphore():
        return await _run(prompt, system_prompt)


async def _run(prompt: str, system_prompt: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        'claude', '-p', '--output-format', 'json',
        '--tools', '', '--strict-mcp-config', '--setting-sources', 'project',
        '--no-session-persistence', '--model', MODEL,
        '--system-prompt', system_prompt,
        cwd=_cwd(),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(prompt.encode()), TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        raise ClaudeCodeError('Claude Code took too long to answer.')
    return parse_result(proc.returncode, out.decode(errors='replace'), err.decode(errors='replace'))
