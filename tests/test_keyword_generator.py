import src.collect.keyword_generator as kg


def test_parse_keywords_trims_and_limits():
    text = "- Alpha  \n* Beta\nGamma"
    assert kg._parse_keywords(text, limit=2) == ["Alpha", "Beta"]


def test_generate_keywords_dedup_and_seed(monkeypatch):
    class DummyClient:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def chat(self, prompt: str, **_: object) -> str:  # pragma: no cover - assertions below validate usage
            self.prompts.append(prompt)
            return "- cloud platform\n- enterprise crm\n- cloud platform"

    dummy = DummyClient()
    monkeypatch.setattr(kg, "default_client", dummy)

    result = kg.generate_keywords_from_brief(
        "面向 B2B 的 SaaS 产品，关注数据安全与自动化",
        max_keywords=5,
        seed_keywords=["SaaS", "自动化"],
    )

    assert result == ["cloud platform", "enterprise crm"]
    assert "SaaS" in dummy.prompts[0]
