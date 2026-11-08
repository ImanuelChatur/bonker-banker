"""Thin Gemini client (standard library only, so no extra dependency)."""
import json
import urllib.error
import urllib.request

import config

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMUnavailable(RuntimeError):
    pass


def available() -> bool:
    return config.gemini_key() is not None


# Worth trying the next model on: retired/unknown model, rate limit, server error or overload.
_RETRY_CODES = {404, 429, 500, 502, 503, 504}


def generate_json(prompt: str, schema: dict | None = None, timeout: int = 45) -> dict:
    """Ask Gemini for a JSON object, trying each configured model in turn. Key is sent in a header, never in the URL."""
    key = config.gemini_key()
    if not key:
        raise LLMUnavailable("GEMINI_API_KEY is not set")
    gen = {"temperature": 0, "responseMimeType": "application/json"}
    if schema:
        gen["responseSchema"] = schema
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gen}).encode()
    last = None
    for model in config.gemini_models():
        req = urllib.request.Request(
            ENDPOINT.format(model=model), data=body, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = json.load(r)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in _RETRY_CODES:
                continue
            break
        except OSError as e:   # network error or timeout
            last = e
            continue
        parts = payload["candidates"][0]["content"]["parts"]
        return json.loads("".join(p.get("text", "") for p in parts if not p.get("thought")))
    raise LLMUnavailable(f"Gemini request failed: {last}")
