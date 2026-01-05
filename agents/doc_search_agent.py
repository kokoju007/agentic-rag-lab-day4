from __future__ import annotations

from pathlib import Path

from agents.base import AgentResult
from agents.retrieval import SearchHit, TfidfRetriever


class DocSearchAgent:
    name = "doc_search"

    def __init__(
        self,
        docs_path: Path | None = None,
        retriever: TfidfRetriever | None = None,
    ) -> None:
        self._docs_path = docs_path or Path("docs")
        self._retriever = retriever or TfidfRetriever(root=str(self._docs_path))

    def run(
        self,
        question: str,
        actor: object | None = None,
        trace_id: str | None = None,
    ) -> AgentResult:
        _ = actor
        _ = trace_id
        hits = self._retriever.search(question, top_k=5)
        evidence = [self._format_hit(hit) for hit in hits]
        confidence = hits[0].score if hits else 0.0

        if evidence:
            answer = "문서를 참고해 요약을 제공합니다."
        else:
            answer = "관련 문서를 찾지 못했습니다."

        return AgentResult(answer=answer, evidence=evidence, confidence=confidence)

    def _format_hit(self, hit: SearchHit) -> str:
        snippet = " ".join(hit.text.splitlines()).strip()
        if len(snippet) > 240:
            snippet = f"{snippet[:237]}..."
        return f"{hit.doc_id}:{hit.chunk_id}: {snippet}"
