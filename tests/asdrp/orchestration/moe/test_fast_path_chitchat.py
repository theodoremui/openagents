import pytest

from asdrp.orchestration.moe.fast_path import FastPathDetector


@pytest.mark.asyncio
async def test_fast_path_chitchat_whats_going_on_no_api_key(monkeypatch):
    # Ensure embeddings path is disabled so we validate lexical behavior.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    detector = FastPathDetector(similarity_threshold=0.75)
    agent = await detector.detect_fast_path("What's going on?")
    assert agent == "chitchat"


@pytest.mark.asyncio
async def test_fast_path_does_not_misroute_substantive_queries(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    detector = FastPathDetector(similarity_threshold=0.75)
    agent = await detector.detect_fast_path("What's going on with AAPL stock?")
    assert agent is None


@pytest.mark.asyncio
async def test_fast_path_chitchat_not_much(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    detector = FastPathDetector(similarity_threshold=0.75)
    agent = await detector.detect_fast_path("not much")
    assert agent == "chitchat"


@pytest.mark.asyncio
async def test_fast_path_not_misroute_not_much_about_stock(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    detector = FastPathDetector(similarity_threshold=0.75)
    agent = await detector.detect_fast_path("not much about AAPL stock")
    assert agent is None


