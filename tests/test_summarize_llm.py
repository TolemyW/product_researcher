import src.summarize.llm as llm
from src.storage.data_store import RawDocument


def test_extract_bullets_prefers_list():
    text = "- first point\nsecond point"
    assert llm._extract_bullets(text, limit=3) == ["first point", "second point"]


def test_summarize_llm_success(monkeypatch):
    doc = RawDocument(url="https://example.com", title="Example", content="内容一。内容二。", fetched_at="now")

    class DummyClient:
        def chat(self, prompt: str, **_: object) -> str:  # pragma: no cover - assertions via output
            assert "Example" in prompt
            return "- 要点1\n- 要点2\n- 要点3"

    monkeypatch.setattr(llm, "default_client", DummyClient())

    summaries = llm.summarize_documents_llm([doc], max_points=2, fallback_to_basic=False)
    assert len(summaries) == 1
    assert summaries[0].bullet_points == ["要点1", "要点2"]


def test_summarize_llm_fallback(monkeypatch):
    doc = RawDocument(url="https://example.com", title="Example", content="Sentence one. Sentence two.", fetched_at="now")

    class FailingClient:
        def chat(self, *_: object, **__: object) -> str:  # pragma: no cover - triggered exception path
            raise RuntimeError("missing key")

    monkeypatch.setattr(llm, "default_client", FailingClient())

    summaries = llm.summarize_documents_llm([doc], max_points=1, fallback_to_basic=True)
    assert summaries[0].bullet_points == ["Sentence one."]
