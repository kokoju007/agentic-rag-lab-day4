from __future__ import annotations

import re
from collections import Counter

from .base import SearchHit


def _tokens(s: str) -> list[str]:
    # ASCII + Korean tokenization
    return re.findall(r"[0-9A-Za-z가-힣]+", s.lower())


class KeywordRetriever:
    def __init__(self, docs: dict[str, str]) -> None:
        self._docs = docs

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        q = Counter(_tokens(query))
        hits: list[SearchHit] = []
        for doc_id, text in self._docs.items():
            t = Counter(_tokens(text))
            # simple overlap score
            score = float(sum((q & t).values()))
            if score <= 0:
                continue
            hits.append(
                SearchHit(score=score, doc_id=doc_id, chunk_id="full", text=text[:800])
            )
        hits.sort(key=lambda h: (-h.score, h.doc_id))
        return hits[:top_k]
