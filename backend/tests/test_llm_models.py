"""Gemini client: tries the next configured model when one is busy or retired."""
import io
import json
import urllib.error

import pytest

from services import llm


def _reply(obj):
    body = {"candidates": [{"content": {"parts": [{"text": json.dumps(obj)}]}}]}
    return io.BytesIO(json.dumps(body).encode())


def test_falls_back_to_next_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("GEMINI_MODEL", "busy-model, good-model")
    tried = []

    def fake_urlopen(req, timeout):
        tried.append(req.full_url)
        if "busy-model" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, None)
        return _reply({"ok": True})

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    assert llm.generate_json("hi") == {"ok": True}
    assert len(tried) == 2 and "good-model" in tried[1]


def test_all_models_down_raises_unavailable(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("GEMINI_MODEL", "a,b")

    def fake_urlopen(req, timeout):
        raise TimeoutError("timed out")

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(llm.LLMUnavailable):
        llm.generate_json("hi")


def test_bad_key_does_not_try_other_models(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("GEMINI_MODEL", "a,b")
    tried = []

    def fake_urlopen(req, timeout):
        tried.append(req.full_url)
        raise urllib.error.HTTPError(req.full_url, 403, "forbidden", {}, None)

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(llm.LLMUnavailable):
        llm.generate_json("hi")
    assert len(tried) == 1
