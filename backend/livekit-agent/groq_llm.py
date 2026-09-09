"""Per-user Groq chat-completions client for the LiveKit voice worker.

Uses the user's own Groq API key (loaded via :mod:`key_loader`) against
``https://api.groq.com/openai/v1/chat/completions`` — mirroring the
headers/body built by ``app.ai.gateway._call_groq``.

Replies are tuned for speech: short, plain-text, no markdown or lists.
"""

from __future__ import annotations

VOICE_SYSTEM_PROMPT: str = (
    "You are a warm, friendly voice assistant for a wellness app. "
    "Keep every reply short — one or two sentences, plain spoken words only. "
    "Never use markdown, lists, bullet points, emojis, or code. "
    "You may discuss general wellness topics only. "
    "Never diagnose any condition, never prescribe or dose any medication, "
    "and never give treatment instructions. "
    "If asked for medical advice, encourage seeing a qualified clinician."
)

NO_KEY_MESSAGE: str = (
    "Please add your Groq API key in Profile, AI Provider Keys, then rejoin voice."
)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound"]


class GroqKeyInvalid(Exception):
    """The user's Groq API key was rejected (HTTP 401)."""


class GroqUnavailable(Exception):
    """Groq request failed (network error, 4xx/5xx on all models, bad payload)."""


class UserGroqLLM:
    """Chat client bound to a single user's Groq API key."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def chat(self, messages: list[dict], system: str) -> str:
        """Send a chat request; fall through GROQ_MODELS on 4xx/5xx.

        Raises:
            GroqKeyInvalid: if Groq returns 401 for the key.
            GroqUnavailable: on any other failure.
        """
        import httpx

        history = [{"role": "system", "content": system}] + list(messages)
        last_error: Exception | None = None

        for model in GROQ_MODELS:
            payload = {
                "model": model,
                "messages": history,
                "temperature": 0.7,
                "max_tokens": 300,
                "stream": False,
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        GROQ_CHAT_URL,
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        json=payload,
                    )
            except Exception as exc:
                last_error = exc
                continue

            if resp.status_code == 401:
                raise GroqKeyInvalid("Groq API key rejected (401).")
            if 400 <= resp.status_code < 600:
                last_error = GroqUnavailable(f"Groq HTTP {resp.status_code}")
                continue

            try:
                data = resp.json()
            except Exception as exc:
                last_error = exc
                continue
            choices = data.get("choices", []) if isinstance(data, dict) else []
            if choices:
                text = choices[0].get("message", {}).get("content", "")
                if text:
                    return text
            last_error = GroqUnavailable("Empty response from Groq.")

        raise GroqUnavailable(str(last_error) if last_error else "Groq request failed.")
