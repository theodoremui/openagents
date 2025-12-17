import pytest

from asdrp.orchestration.moe.fast_path import FastPathDetector


class _EmbeddingsClientBad:
    class embeddings:
        @staticmethod
        async def create(*args, **kwargs):
            # Simulate an SDK response object with data=None (observed failure mode)
            class R:
                data = None
            return R()


@pytest.mark.asyncio
async def test_fast_path_does_not_crash_on_bad_embedding_response(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    d = FastPathDetector()
    # force-enable embeddings path by injecting a bad client
    d._client = _EmbeddingsClientBad()  # type: ignore[attr-defined]
    # Should not raise; should simply skip embeddings fast path
    assert await d.detect_fast_path("Show me on a map") is None


