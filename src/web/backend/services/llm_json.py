"""Robust JSON extraction from LLM output.

Models are asked for bare JSON, but in practice they wrap it in markdown fences,
prepend a sentence of prose, or append a closing remark. Groq/Llama does this
most often, Claude and OpenAI occasionally. This module centralises the
salvage logic so both the playlist and song-profile paths behave identically.
"""
import json
import logging
import re

log = logging.getLogger(__name__)

# ```json ... ```  /  ``` ... ```  /  ~~~ ... ~~~
_FENCE = re.compile(r'^\s*(?:```|~~~)[a-zA-Z]*\s*\n?(.*?)\n?\s*(?:```|~~~)\s*$', re.DOTALL)

_OPEN_TO_CLOSE = {'{': '}', '[': ']'}


class LLMParseError(ValueError):
    """The model's output could not be parsed as JSON."""

    def __init__(self, message: str, raw: str):
        super().__init__(message)
        self.raw = raw

    @property
    def snippet(self) -> str:
        """First 300 chars of the offending output, for logs and error payloads."""
        collapsed = ' '.join(self.raw.split())
        return collapsed[:300]


def _strip_fence(text: str) -> str:
    match = _FENCE.match(text)
    return match.group(1).strip() if match else text.strip()


def _first_balanced(text: str) -> str | None:
    """Return the first balanced {...} or [...] block, ignoring braces inside strings."""
    start = None
    for i, ch in enumerate(text):
        if ch in _OPEN_TO_CLOSE:
            start = i
            break
    if start is None:
        return None

    opener = text[start]
    closer = _OPEN_TO_CLOSE[opener]
    depth = 0
    in_string = False
    escaped = False

    for i in range(start, len(text)):
        ch = text[i]
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def extract_json(raw: str, *, context: str = 'llm'):
    """Parse JSON out of a model response, tolerating fences and surrounding prose.

    Raises LLMParseError (carrying the raw output) if nothing parses.
    """
    if not raw or not raw.strip():
        raise LLMParseError('model returned an empty response', raw or '')

    candidates = []
    stripped = _strip_fence(raw)
    candidates.append(stripped)

    balanced = _first_balanced(stripped)
    if balanced and balanced != stripped:
        candidates.append(balanced)

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    err = LLMParseError('model did not return valid JSON', raw)
    log.warning('[%s] JSON parse failed; raw output: %s', context, err.snippet)
    raise err
