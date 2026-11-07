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


def generate_json(prompt: str, schema: dict | None = None, timeout: int = 120) -> dict:
    """Ask Gemini for a JSON object. Key is sent in a header, never in the URL."""
    key = config.gemini_key()
    if not key:
        raise LLMUnavailable("GEMINI_API_KEY is not set")
    gen = {"temperature": 0, "responseMimeType": "application/json"}
    if schema:
        gen["responseSchema"] = schema
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gen}).encode()
    req = urllib.request.Request(
        ENDPOINT.format(model=config.gemini_model()), data=body, method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.load(r)
    except urllib.error.URLError as e:
        raise LLMUnavailable(f"Gemini request failed: {e}") from e
    return json.loads(payload["candidates"][0]["content"]["parts"][0]["text"])
