import json
import os
from typing import Generator

from openai import OpenAI
from pydantic import BaseModel

from .base import BaseLLMClient


class GrokClient(BaseLLMClient):
    def __init__(self, model_name: str = "grok-beta", api_key: str | None = None):
        """
        Initialize the Grok client using OpenAI's package.

        Args:
            model_name: Model ID (e.g. grok-beta, grok-2-latest).
            api_key: Optional API key; falls back to XAI_API_KEY env var.
        """
        key = api_key or os.environ.get("GROK_API_KEY") or os.environ.get("XAI_API_KEY")
        self.client = OpenAI(
            api_key=key,
            base_url="https://api.x.ai/v1",
        )
        self.model_name = model_name

    def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        schema: type[BaseModel],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> BaseModel:
        """
        Requests JSON from Grok and parses the response into the given Pydantic schema.
        We instruct the model to return JSON matching the schema.
        Note: xAI supports JSON mode.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        instruction = (
            f"{(system_prompt or '').strip()}\n\n"
            f"You MUST respond with a single valid JSON object that exactly matches this schema:\n"
            f"{schema_json}\n\n"
            f"Use the exact field names from the schema. Output raw JSON only — no markdown, no code fences."
        ).strip()

        completion_kw: dict = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "response_format": {"type": "json_object"},
            "temperature": temperature,
        }
        if max_tokens is not None:
            completion_kw["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**completion_kw)
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise ValueError("Grok returned empty content for structured output")
        
        data = json.loads(content)
        return schema.model_validate(data)

    def generate_text(
        self, prompt: str, system_prompt: str, temperature: float = 0.5
    ) -> str:
        """
        Generates a text response from the LLM.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=False,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    def generate_text_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.5,
    ) -> Generator[str, None, None]:
        """
        Streams a text response token-by-token.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
            temperature=temperature,
        )
        
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
