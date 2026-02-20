"""LLM provider abstraction for Ollama and OpenRouter.

Both use the OpenAI-compatible /v1/chat/completions format,
so the abstraction is intentionally thin.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger("pidog.llm")


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def model(self) -> str: ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]: ...


class OllamaProvider(LLMProvider):
    """Local Ollama instance using OpenAI-compatible endpoint."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self._base_url = (base_url or settings.ollama_url).rstrip("/")
        self._model = model or settings.ollama_model

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    async def chat(self, messages, tools=None, timeout=30.0):
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=timeout) as client:
            url = f"{self._base_url}/v1/chat/completions"
            logger.info(f"Ollama request: model={self._model}, messages={len(messages)}")
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()


class OpenRouterProvider(LLMProvider):
    """OpenRouter API (OpenAI-compatible)."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or settings.openrouter_api_key
        self._model = model or settings.openrouter_model

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def model(self) -> str:
        return self._model

    async def chat(self, messages, tools=None, timeout=30.0):
        if not self._api_key:
            raise ValueError("OpenRouter API key not configured (set PIDOG_OPENROUTER_API_KEY)")

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": "https://github.com/command-pidog",
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            url = "https://openrouter.ai/api/v1/chat/completions"
            logger.info(f"OpenRouter request: model={self._model}, messages={len(messages)}")
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()


def get_provider(name: str | None = None, model: str | None = None) -> LLMProvider:
    """Factory for LLM providers."""
    provider_name = name or settings.default_llm_provider
    if provider_name == "ollama":
        return OllamaProvider(model=model)
    elif provider_name == "openrouter":
        return OpenRouterProvider(model=model)
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use 'ollama' or 'openrouter'.")
