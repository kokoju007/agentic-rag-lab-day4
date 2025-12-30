from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchHit:
    score: float
    doc_id: str
    chunk_id: str
    text: str


class Retriever(Protocol):
    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        ...
