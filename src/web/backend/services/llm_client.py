import asyncio


class LLMClient:
    def __init__(self, provider: str, api_key: str):
        self.provider = provider
        self.api_key = api_key

    async def generate(self, messages: list[dict], system_prompt: str) -> str:
        if self.provider == 'claude':
            return await self._generate_claude(messages, system_prompt)
        if self.provider == 'openai':
            return await self._generate_openai(messages, system_prompt)
        if self.provider == 'groq':
            return await self._generate_groq(messages, system_prompt)
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
            model='llama-3.3-70b-versatile',
            messages=all_messages,
        )
        return response.choices[0].message.content
