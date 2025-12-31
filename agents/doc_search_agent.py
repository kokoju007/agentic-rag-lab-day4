from __future__ import annotations

from pathlib import Path

from agents.base import AgentResult
from agents.retrieval import SearchHit, TfidfRetriever


class DocSearchAgent:
    name = "doc_search"

    def __init__(self, docs_path: Path | None = None, retriever: TfidfRetriever | None = None) -> None:
        self._docs_path = docs_path or Path("docs")
        self._retriever = retriever or TfidfRetriever(root=str(self._docs_path))

    def run(self, question: str) -> AgentResult:
        hits = self._retriever.search(question, top_k=5)
        evidence = [self._format_hit(hit) for hit in hits]
        confidence = hits[0].score if hits else 0.0

        if evidence:
            answer = "氍胳劀?愳劀 甏€???挫毄??彀眷晿?惦媹?? 歃濌卑毳??曥澑?挫＜?胳殧."
        else:
            answer = "氍胳劀?愳劀 甏€???挫毄??彀眷? 氇豁枅?惦媹??"

        return AgentResult(answer=answer, evidence=evidence, confidence=confidence)

    def _format_hit(self, hit: SearchHit) -> str:
        snippet = " ".join(hit.text.splitlines()).strip()
        if len(snippet) > 240:
            snippet = f"{snippet[:237]}..."
        return f"{hit.doc_id}:{hit.chunk_id}: {snippet}"
