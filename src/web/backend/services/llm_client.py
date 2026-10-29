import asyncio

from services.claude_code import ClaudeCodeError


class NeedsLLM(Exception):
    """'Your Claude Code' on the hosted backend (provider 'helper'): the server
    can't reach the user's machine, so it hands the prompt back. The page runs
    it on the local helper and repeats the request with the reply appended to
    `llm_replies`. Answered as 428 by main.py."""

    def __init__(self, prompt: str):
        super().__init__('This request needs a reply from your Claude Code.')
        self.prompt = prompt


class RelayError(ClaudeCodeError):
    """The page couldn't get a reply from the helper; its message is written for the user."""


def as_transcript(messages: list[dict], system_prompt: str = '') -> str:
    """One prompt for a one-shot CLI: a multi-turn history goes in as a labelled transcript."""
    if len(messages) == 1:
        body = messages[0]['content']
    else:
        body = '\n\n'.join(f"{m['role'].capitalize()}: {m['content']}" for m in messages)
    return f'{system_prompt}\n\n{body}' if system_prompt else body


class LLMClient:
    def __init__(self, provider: str, api_key: str, replies: tuple[str, ...] = (), relay_error: str | None = None):
        self.provider = provider
        self.api_key = api_key
        # The relay's replies so far, used in call order (each request replays from the start).
        self.replies = list(replies)
        # Set when the helper failed: the next call fails like any provider's would.
        self.relay_error = relay_error

    async def generate(self, messages: list[dict], system_prompt: str) -> str:
        if self.provider == 'claude':
            return await self._generate_claude(messages, system_prompt)
        if self.provider == 'openai':
            return await self._generate_openai(messages, system_prompt)
        if self.provider == 'groq':
            return await self._generate_groq(messages, system_prompt)
        if self.provider == 'claude-code':
            return await self._generate_claude_code(messages, system_prompt)
        if self.provider == 'helper':
            if self.replies:
                return self.replies.pop(0)
            if self.relay_error:
                raise RelayError(self.relay_error)
            raise NeedsLLM(as_transcript(messages, system_prompt))
        raise ValueError(f'Unknown provider: {self.provider}')

    async def _generate_claude(self, messages: list[dict], system_prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        response = await asyncio.to_thread(
            client.messages.create,
            model='claude-sonnet-5',
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text

    async def _generate_claude_code(self, messages: list[dict], system_prompt: str) -> str:
        from services import claude_code
        return await claude_code.run(as_transcript(messages), system_prompt)

    async def _generate_openai(self, messages: list[dict], system_prompt: str) -> str:
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        all_messages = [{'role': 'system', 'content': system_prompt}] + messages
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model='gpt-4o',
            messages=all_messages,
        )
        return response.choices[0].message.content

    async def _generate_groq(self, messages: list[dict], system_prompt: str) -> str:
        from groq import Groq
        client = Groq(api_key=self.api_key)
        all_messages = [{'role': 'system', 'content': system_prompt}] + messages
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model='openai/gpt-oss-120b',
            messages=all_messages,
            # gpt-oss is a reasoning model, and hidden reasoning counts against
            # Groq's on-demand budget (8k tokens/min). At the default effort a DJ
            # call spent 1,924 of 3,237 tokens reasoning and replies got cut off
            # (DJ4 result in docs/plan.md); low cuts that to ~30 and halves latency.
            reasoning_effort='low',
        )
        return response.choices[0].message.content
