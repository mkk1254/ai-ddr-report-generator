"""LLM client using Google Gemini API (free tier)."""

import os
import time


def _is_quota_error(exc: BaseException) -> bool:
    """True if the exception is a 429 / quota exceeded error."""
    msg = (getattr(exc, "message", "") or str(exc)).lower()
    return (
        "429" in msg
        or "resource_exhausted" in msg
        or "quota" in msg
        or "rate limit" in msg
    )


def call_llm(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """Call Gemini API. Set GOOGLE_API_KEY or GEMINI_API_KEY in environment."""
    raw = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    api_key = (raw or "").strip()
    if not api_key or api_key.lower() in ("your-api-key-here", "your_api_key_here", ""):
        raise RuntimeError(
            "API key required. Set GOOGLE_API_KEY in .env with a key from https://aistudio.google.com/apikey"
        )
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError("google-genai package required. Install with: pip install google-genai")

    client = genai.Client(api_key=api_key)
    max_retries = 2
    retry_delay_sec = 65  # free tier is often per-minute; wait just over 1 min

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                ),
            )
            try:
                if hasattr(response, "text") and response.text:
                    return response.text
            except (ValueError, AttributeError):
                pass
            if response.candidates:
                cand = response.candidates[0]
                if cand.content and cand.content.parts:
                    part = cand.content.parts[0]
                    if hasattr(part, "text") and part.text:
                        return part.text
            return ""
        except Exception as e:
            if _is_quota_error(e) and attempt < max_retries:
                time.sleep(retry_delay_sec)
                continue
            if _is_quota_error(e):
                raise RuntimeError(
                    "Gemini API quota exceeded. Free tier has strict limits (e.g. requests per minute/day). "
                    "Wait a few minutes and try again, or check usage: https://ai.dev/rate-limit . "
                    "See rate limits: https://ai.google.dev/gemini-api/docs/rate-limits"
                ) from e
            raise
