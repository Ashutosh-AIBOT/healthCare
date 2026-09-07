"""LLM Gateway with multi-provider support including NVIDIA NIM/Nemotron."""

from __future__ import annotations

import httpx
from enum import Enum
from typing import Any, AsyncIterator, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class Provider(str, Enum):
    """Supported LLM providers."""

    NVIDIA = "nvidia"  # NVIDIA NIM/Nemotron
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"
    OLLAMA = "ollama"
    MOCK = "mock"


class LLMResponse:
    """Standardized LLM response."""

    def __init__(
        self,
        text: str,
        *,
        model: str | None = None,
        provider: Provider | None = None,
        usage: dict | None = None,
        citations: list[dict] | None = None,
        degraded: bool = False,
    ):
        self.text = text
        self.model = model
        self.provider = provider
        self.usage = usage or {}
        self.citations = citations or []
        self.degraded = degraded


class LLMGateway:
    """Gateway that routes calls to the appropriate LLM provider."""

    # Fallback chain: primary → secondary → ... → mock
    FALLBACK_CHAIN = [
        Provider.NVIDIA,
        Provider.OPENAI,
        Provider.GEMINI,
        Provider.GROQ,
        Provider.OLLAMA,
        Provider.MOCK,
    ]

    def __init__(self, db: AsyncSession, user_id: str | None = None):
        self.db = db
        self.user_id = user_id
        self._provider_cache: Provider | None = None

    async def _get_active_provider(self) -> Provider:
        """Fetch the active provider from user's API keys in the database.

        Returns the Provider enum based on which key is set and active.
        Falls back to MOCK if no key is configured.
        """
        # TODO: Query the api_keys table for the user's active keys
        # For now, check environment
        import os
        nvidia_key = os.environ.get("NVIDIA_API_KEY")
        if nvidia_key:
            return Provider.NVIDIA
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            return Provider.OPENAI
        # If no key, default to mock for demo
        return Provider.MOCK

    async def complete(
        self,
        prompt: str,
        *,
        provider: Provider | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Complete a prompt using the selected provider with fallback.

        Routes to the specified provider, or the active user provider,
        with automatic fallback through the chain if a call fails.
        """
        # Determine which provider to use
        target_provider = provider or await self._get_active_provider()

        # Build the fallback chain starting from the selected provider
        if target_provider in self.FALLBACK_CHAIN:
            start_idx = self.FALLBACK_CHAIN.index(target_provider)
            chain = self.FALLBACK_CHAIN[start_idx:] + self.FALLBACK_CHAIN[:start_idx]
        else:
            chain = self.FALLBACK_CHAIN

        last_error: Exception | None = None

        for p in chain:
            try:
                result = await self._call_provider(
                    p, prompt, temperature=temperature, max_tokens=max_tokens
                )
                # Record the successful provider for analytics
                self._log_success(p, result)
                return result
            except Exception as e:
                last_error = e
                self._log_failure(p, e)
                continue

        # All providers failed - return degraded mock response
        return LLMResponse(
            text="AI service temporarily unavailable. Please add a valid API key in your profile settings.",
            degraded=True,
            provider=Provider.MOCK,
        )

    async def _call_provider(
        self,
        provider: Provider,
        prompt: str,
        *,
        temperature: float,
        max_tokens: int | None,
    ) -> LLMResponse:
        """Make a single provider call."""

        if provider == Provider.NVIDIA:
            return await self._call_nvidia(prompt, temperature=temperature, max_tokens=max_tokens)
        elif provider == Provider.OPENAI:
            return await self._call_openai(prompt, temperature=temperature, max_tokens=max_tokens)
        elif provider == Provider.GEMINI:
            return await self._call_gemini(prompt, temperature=temperature, max_tokens=max_tokens)
        elif provider == Provider.GROQ:
            return await self._call_groq(prompt, temperature=temperature, max_tokens=max_tokens)
        elif provider == Provider.OLLAMA:
            return await self._call_ollama(prompt, temperature=temperature, max_tokens=max_tokens)
        elif provider == Provider.MOCK:
            return await self._call_mock(prompt, temperature=temperature, max_tokens=max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def _call_nvidia(self, prompt: str, *, temperature: float, max_tokens: int | None) -> LLMResponse:
        """Call NVIDIA NIM API with Nemotron 3.5 model.

        NVIDIA NIM endpoint: POST https://ai.nvidia.com/v1/chat/completions
        Model: nvidia/nemotron-3.5-lightning-30b-a3b
        """
        api_key = self._get_nvidia_key()
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://ai.nvidia.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract the response text
        choices = data.get("choices", [])
        if choices and len(choices) > 0:
            text = choices[0].get("message", {}).get("content", "")
        else:
            text = ""

        # Extract usage info if available
        usage = data.get("usage", {})
        model = data.get("model", "nvidia/nemotron-3.5-lightning-30b-a3b")

        return LLMResponse(
            text=text or "",
            model=model,
            provider=Provider.NVIDIA,
            usage=usage or {},
        )

    async def _call_openai(self, prompt: str, *, temperature: float, max_tokens: int | None) -> LLMResponse:
        """Call OpenAI API."""
        api_key = self._get_openai_key()
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model or "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        usage = data.get("usage", {})
        model = data.get("model", "gpt-4o-mini")

        return LLMResponse(
            text=text or "",
            model=model,
            provider=Provider.OPENAI,
            usage=usage or {},
        )

    async def _call_gemini(self, prompt: str, *, temperature: float, max_tokens: int | None) -> LLMResponse:
        """Call Google Gemini API."""
        api_key = self._get_gemini_key()
        payload = {
            "model": model or "gemini-1.5-flash",
            "contents": [prompt],
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # Gemini response format
        text = data.get("text", "") or ""
        usage = data.get("usageMetadata", {})
        model = data.get("model", "gemini-1.5-flash")

        return LLMResponse(
            text=str(text) or "",
            model=model,
            provider=Provider.GEMINI,
            usage=usage or {},
        )

    async def _call_groq(self, prompt: str, *, temperature: float, max_tokens: int | None) -> LLMResponse:
        """Call Groq API."""
        api_key = self._get_groq_key()
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model or "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        usage = data.get("usage", {})
        model = data.get("model", "llama-3.1-8b-instant")

        return LLMResponse(
            text=text or "",
            model=model,
            provider=Provider.GROQ,
            usage=usage or {},
        )

    async def _call_ollama(self, prompt: str, *, temperature: float, max_tokens: int | None) -> LLMResponse:
        """Call local Ollama API."""
        payload = {
            "model": model or "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        text = data.get("response", "")
        model = data.get("model", "llama3")

        return LLMResponse(
            text=text or "",
            model=model,
            provider=Provider.OLLAMA,
        )

    async def _call_mock(self, prompt: str, *, temperature: float, max_tokens: int | None) -> LLMResponse:
        """Mock response for demo/CI when no API key is configured."""
        text = f"[MOCK] This is a simulated response to: '{prompt[:80]}...'\n\n"
        text += "This would be a real LLM response if an API key were configured.\n"
        text += "Please add an NVIDIA NIM API key or other provider key in your profile to enable AI features."
        text += "\n\n---\n"
        text += "Medical disclaimer: These figures are explanations of what appears on the report, not a clinical interpretation. Discuss them with a qualified doctor."

        return LLMResponse(
            text=text,
            model="mock-model",
            provider=Provider.MOCK,
        )

    # Key getters - will be integrated with DB api_keys table
    def _get_nvidia_key(self) -> str:
        """Get NVIDIA API key from environment or DB."""
        import os
        key = os.environ.get("NVIDIA_API_KEY", "")
        if key:
            return key
        # TODO: Fetch from api_keys table
        raise ValueError("NVIDIA API key not configured")

    def _get_openai_key(self) -> str:
        """Get OpenAI API key."""
        import os
        key = os.environ.get("OPENAI_API_KEY", "")
        if key:
            return key
        raise ValueError("OpenAI API key not configured")

    def _get_gemini_key(self) -> str:
        """Get Google Gemini API key."""
        import os
        key = os.environ.get("GEMINI_API_KEY", "")
        if key:
            return key
        raise ValueError("Gemini API key not configured")

    def _get_groq_key(self) -> str:
        """Get Groq API key."""
        import os
        key = os.environ.get("GROQ_API_KEY", "")
        if key:
            return key
        raise ValueError("Groq API key not configured")

    def _log_success(self, provider: Provider, result: LLMResponse) -> None:
        """Log successful provider call for analytics."""
        # TODO: Integrate with cost tracking and analytics
        pass

    def _log_failure(self, provider: Provider, error: Exception) -> None:
        """Log failed provider call for analytics."""
        # TODO: Integrate with cost tracking and analytics
        pass