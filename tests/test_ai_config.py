import pytest

import ai


def test_missing_gemini_key_raises_helpful_error(monkeypatch):
    monkeypatch.setattr(ai, "GEMINI_API_KEY", "")
    monkeypatch.setattr(ai, "_client", None)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        ai.get_client()