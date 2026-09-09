"""LLM Gateway — NVIDIA Nemotron (chat) + Groq (streaming LLM + Whisper STT).

Architecture:
  - NVIDIA Nemotron-3.5  →  primary chat LLM (non-streaming fallback)
  - Groq LLaMA-3.3-70b  →  streaming chat responses (SSE, very fast)
  - Groq Whisper         →  STT (voice → text)
  - OpenAI / Gemini      →  fallback chain
  - Mock                 →  CI / no-key demo
"""

from __future__ import annotations

import asyncio
import json
import os
from enum import Enum
from typing import Any, AsyncIterator, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession


class Provider(str, Enum):
    NVIDIA = "nvidia"
    GROQ = "groq"       # also used for STT
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    MOCK = "mock"


# Default models per provider
DEFAULT_MODELS = {
    Provider.NVIDIA: "nvidia/nemotron-3.5-lightning-30b-a3b",
    Provider.GROQ:   "openai/gpt-oss-120b",   # fastest streaming model
    Provider.OPENAI: "gpt-4o-mini",
    Provider.GEMINI: "gemini-1.5-flash",
    Provider.OLLAMA: "llama3",
    Provider.MOCK:   "mock-model",
}

GROQ_STT_MODEL = "whisper-large-v3-turbo"  # best speed/accuracy ratio


class LLMResponse:
    """Standardised LLM response."""

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
    """Routes LLM calls: NVIDIA for chat, Groq for streaming + STT."""

    # Primary: NVIDIA → Groq (streaming) → OpenAI → Gemini → Mock
    FALLBACK_CHAIN = [
        Provider.NVIDIA,
        Provider.GROQ,
        Provider.OPENAI,
        Provider.GEMINI,
        Provider.OLLAMA,
        Provider.MOCK,
    ]

    def __init__(self, db: AsyncSession, user_id: str | None = None):
        self.db = db
        self.user_id = user_id
        self._provider_cache: Provider | None = None

    # ------------------------------------------------------------------
    # Provider key resolution (DB → env → error)
    # ------------------------------------------------------------------

    async def _get_key(self, provider: str) -> str | None:
        """Fetch decrypted key from user's DB api_keys, then environment."""
        if self.db and self.user_id:
            try:
                from app.services.api_key_service import get_active_api_key_raw
                key = await get_active_api_key_raw(self.db, user_id=self.user_id, provider=provider)
                if key:
                    return key
            except Exception:
                pass
        # Fall back to environment variable
        env_map = {
            "nvidia": ["NVIDIA_API_KEY", "LLM_API_KEY"],
            "groq": ["GROQ_API_KEY"],
            "openai": ["OPENAI_API_KEY"],
            "gemini": ["GEMINI_API_KEY"],
        }
        for env_var in env_map.get(provider, []):
            val = os.environ.get(env_var, "")
            if val:
                return val
        return None

    async def _get_active_provider(self) -> Provider:
        """Return the best available provider based on configured keys."""
        for p in [Provider.NVIDIA, Provider.GROQ, Provider.OPENAI, Provider.GEMINI]:
            key = await self._get_key(p.value)
            if key:
                return p
        return Provider.MOCK

    # ------------------------------------------------------------------
    # Non-streaming completion (NVIDIA primary, Groq fallback)
    # ------------------------------------------------------------------

    async def complete(
        self,
        prompt: str,
        *,
        provider: Provider | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Complete a prompt. NVIDIA is primary, Groq as first fallback."""
        target = provider or await self._get_active_provider()

        if target in self.FALLBACK_CHAIN:
            start = self.FALLBACK_CHAIN.index(target)
            chain = self.FALLBACK_CHAIN[start:] + self.FALLBACK_CHAIN[:start]
        else:
            chain = self.FALLBACK_CHAIN

        last_error: Exception | None = None
        for p in chain:
            try:
                result = await self._call(p, prompt, model=model, temperature=temperature,
                                          max_tokens=max_tokens, system_prompt=system_prompt)
                self._log_success(p, result)
                return result
            except Exception as e:
                last_error = e
                self._log_failure(p, e)
                continue

        return LLMResponse(
            text="AI service temporarily unavailable. Please check your API keys in Profile settings.",
            degraded=True,
            provider=Provider.MOCK,
        )

    # ------------------------------------------------------------------
    # Groq streaming (SSE) — primary streaming path
    # ------------------------------------------------------------------

    async def stream_groq(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream tokens from Groq via SSE. Yields raw text chunks.

        Falls back to NVIDIA non-streaming if Groq key not available.
        """
        groq_key = await self._get_key("groq")
        if groq_key:
            async for chunk in self._stream_groq_sse(
                prompt, groq_key, model=model or DEFAULT_MODELS[Provider.GROQ],
                temperature=temperature, max_tokens=max_tokens,
                system_prompt=system_prompt,
            ):
                yield chunk
        else:
            # Fallback: non-streaming NVIDIA, then fake-stream tokens
            result = await self.complete(prompt, temperature=temperature,
                                         max_tokens=max_tokens, system_prompt=system_prompt)
            for word in result.text.split(" "):
                yield word + " "
                await asyncio.sleep(0)

    async def _stream_groq_sse(
        self,
        prompt: str,
        api_key: str,
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        system_prompt: str | None,
    ) -> AsyncIterator[str]:
        """Internal Groq SSE streaming generator."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0]["delta"]
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    # ------------------------------------------------------------------
    # Groq Whisper STT
    # ------------------------------------------------------------------

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        *,
        filename: str = "audio.webm",
        content_type: str = "audio/webm",
        language: str | None = None,
    ) -> str:
        """Transcribe audio using Groq Whisper. Returns transcript text."""
        groq_key = await self._get_key("groq")
        if not groq_key:
            raise ValueError(
                "Groq API key not configured. Add it in Profile > AI Provider Keys."
            )

        # Use official groq Python SDK if available, otherwise raw httpx
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=groq_key)
            transcription = await client.audio.transcriptions.create(
                file=(filename, audio_bytes, content_type),
                model=GROQ_STT_MODEL,
                language=language,
                response_format="json",
            )
            return transcription.text
        except ImportError:
            # Fallback: raw httpx
            return await self._transcribe_httpx(
                audio_bytes, groq_key, filename=filename,
                content_type=content_type, language=language
            )

    async def _transcribe_httpx(
        self,
        audio_bytes: bytes,
        api_key: str,
        *,
        filename: str,
        content_type: str,
        language: str | None,
    ) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"file": (filename, audio_bytes, content_type)}
            data: dict[str, Any] = {
                "model": GROQ_STT_MODEL,
                "response_format": "json",
            }
            if language:
                data["language"] = language
            headers = {"Authorization": f"Bearer {api_key}"}
            r = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )
            r.raise_for_status()
            return r.json().get("text", "")

    # ------------------------------------------------------------------
    # LiveKit token generation
    # ------------------------------------------------------------------

    async def create_livekit_token(
        self,
        *,
        room_name: str,
        participant_identity: str,
        participant_name: str,
        metadata: str | None = None,
    ) -> str:
        """Generate a LiveKit access token for a voice room."""
        lk_api_key = os.environ.get("LIVEKIT_API_KEY", "")
        lk_api_secret = os.environ.get("LIVEKIT_API_SECRET", "")
        if not lk_api_key or not lk_api_secret:
            raise ValueError(
                "LiveKit credentials not configured. "
                "Add LIVEKIT_API_KEY and LIVEKIT_API_SECRET to your environment."
            )
        try:
            from livekit.api import AccessToken, VideoGrants
            builder = (
                AccessToken(lk_api_key, lk_api_secret)
                .with_identity(participant_identity)
                .with_name(participant_name)
                .with_grants(VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                ))
            )
            if metadata is not None:
                builder = builder.with_metadata(metadata)
            return builder.to_jwt()
        except ImportError:
            # livekit-api not installed, return placeholder
            raise ValueError("livekit-api package required. Run: pip install livekit-api")

    # ------------------------------------------------------------------
    # Individual provider callers
    # ------------------------------------------------------------------

    async def _call(
        self,
        provider: Provider,
        prompt: str,
        *,
        model: str | None,
        temperature: float,
        max_tokens: int | None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        m = model or DEFAULT_MODELS.get(provider, "")
        if provider == Provider.NVIDIA:
            return await self._call_nvidia(prompt, model=m, temperature=temperature,
                                            max_tokens=max_tokens, system_prompt=system_prompt)
        elif provider == Provider.GROQ:
            return await self._call_groq(prompt, model=m, temperature=temperature,
                                          max_tokens=max_tokens, system_prompt=system_prompt)
        elif provider == Provider.OPENAI:
            return await self._call_openai(prompt, model=m, temperature=temperature,
                                            max_tokens=max_tokens, system_prompt=system_prompt)
        elif provider == Provider.GEMINI:
            return await self._call_gemini(prompt, model=m, temperature=temperature,
                                            max_tokens=max_tokens)
        elif provider == Provider.OLLAMA:
            return await self._call_ollama(prompt, model=m, temperature=temperature,
                                            max_tokens=max_tokens)
        else:
            return await self._call_mock(prompt)

    async def _call_nvidia(
        self, prompt: str, *, model: str, temperature: float,
        max_tokens: int | None, system_prompt: str | None = None
    ) -> LLMResponse:
        api_key = await self._get_key("nvidia")
        if not api_key:
            raise ValueError("NVIDIA API key not configured.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            resp = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        return LLMResponse(
            text=text or "",
            model=data.get("model", model),
            provider=Provider.NVIDIA,
            usage=data.get("usage", {}),
        )

    async def _call_groq(
        self, prompt: str, *, model: str, temperature: float,
        max_tokens: int | None, system_prompt: str | None = None
    ) -> LLMResponse:
        api_key = await self._get_key("groq")
        if not api_key:
            raise ValueError("Groq API key not configured.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        return LLMResponse(
            text=text or "",
            model=data.get("model", model),
            provider=Provider.GROQ,
            usage=data.get("usage", {}),
        )

    async def _call_openai(
        self, prompt: str, *, model: str, temperature: float,
        max_tokens: int | None, system_prompt: str | None = None
    ) -> LLMResponse:
        api_key = await self._get_key("openai")
        if not api_key:
            raise ValueError("OpenAI API key not configured.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        return LLMResponse(
            text=text or "",
            model=data.get("model", model),
            provider=Provider.OPENAI,
            usage=data.get("usage", {}),
        )

    async def _call_gemini(
        self, prompt: str, *, model: str, temperature: float,
        max_tokens: int | None
    ) -> LLMResponse:
        api_key = await self._get_key("gemini")
        if not api_key:
            raise ValueError("Gemini API key not configured.")

        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            text = ""

        return LLMResponse(
            text=text or "",
            model=model,
            provider=Provider.GEMINI,
            usage=data.get("usageMetadata", {}),
        )

    async def _call_ollama(
        self, prompt: str, *, model: str, temperature: float,
        max_tokens: int | None
    ) -> LLMResponse:
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{ollama_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()

        return LLMResponse(
            text=data.get("response", "") or "",
            model=data.get("model", model),
            provider=Provider.OLLAMA,
        )

    async def _call_mock(self, prompt: str) -> LLMResponse:
        if os.environ.get("APP_ENV") not in ("test", "ci"):
            raise ValueError(
                "No AI provider key configured. "
                "Add NVIDIA or Groq key in Profile > AI Provider Keys."
            )
        text = (
            f"[MOCK] Simulated response to: '{prompt[:80]}...'\n\n"
            "This is a demo response. Add an NVIDIA or Groq API key in Profile > "
            "AI Provider Keys to enable real AI responses.\n\n"
            "---\nMedical disclaimer: These figures are explanations of what appears "
            "on the report, not a clinical interpretation. Discuss with a qualified doctor."
        )
        return LLMResponse(text=text, model="mock-model", provider=Provider.MOCK)

    def _log_success(self, provider: Provider, result: LLMResponse) -> None:
        pass  # TODO: cost tracking

    def _log_failure(self, provider: Provider, error: Exception) -> None:
        pass  # TODO: alerting