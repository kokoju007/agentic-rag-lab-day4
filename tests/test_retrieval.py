from agents.retrieval.tfidf import TfidfRetriever


def test_tfidf_retriever_returns_hits(tmp_path, monkeypatch):
    # temp docs
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("hello world\n\npassword reset guide", encoding="utf-8")
    (docs / "b.md").write_text("oracle database tuning", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    r = TfidfRetriever(root="docs", cache_dir=".cache")
    hits = r.search("password reset", top_k=3)
    assert hits
    assert "password" in hits[0].text.lower()
