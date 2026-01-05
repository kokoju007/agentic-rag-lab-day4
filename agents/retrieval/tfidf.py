from __future__ import annotations

import math
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .base import SearchHit

_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"[0-9A-Za-z가-힣]+", re.IGNORECASE)


def _tokens(s: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(s)]


def _chunk_text(text: str, max_chars: int = 900) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in parts:
        if len(buf) + len(p) + 2 <= max_chars:
            buf = (buf + "\n\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks or [text[:max_chars]]


@dataclass(frozen=True)
class _Chunk:
    doc_id: str
    chunk_id: str
    text: str


class TfidfRetriever:
    def __init__(self, root: str = "docs", cache_dir: str = ".cache") -> None:
        self._root = Path(root)
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        self._chunks: list[_Chunk] = []
        self._idf: dict[str, float] = {}
        self._vecs: list[dict[str, float]] = []
        self._norms: list[float] = []

        self._build_or_load()

    def _snapshot(self) -> dict[str, float]:
        snap: dict[str, float] = {}
        if self._root.exists():
            for p in sorted(self._root.rglob("*.md")):
                snap[str(p)] = p.stat().st_mtime
        readme = Path("README.md")
        if readme.exists():
            snap[str(readme)] = readme.stat().st_mtime
        return snap

    def _cache_path(self) -> Path:
        return self._cache_dir / "tfidf_index.pkl"

    def _build_or_load(self) -> None:
        cache_path = self._cache_path()
        snap = self._snapshot()

        if cache_path.exists():
            try:
                with cache_path.open("rb") as f:
                    payload = pickle.load(f)
                if payload.get("snapshot") == snap:
                    self._chunks = payload["chunks"]
                    self._idf = payload["idf"]
                    self._vecs = payload["vecs"]
                    self._norms = payload["norms"]
                    return
            except Exception:
                pass

        self._build_index()
        with cache_path.open("wb") as f:
            pickle.dump(
                {
                    "snapshot": snap,
                    "chunks": self._chunks,
                    "idf": self._idf,
                    "vecs": self._vecs,
                    "norms": self._norms,
                },
                f,
            )

    def _iter_markdown_files(self) -> list[Path]:
        files: list[Path] = []
        if self._root.exists():
            files.extend(sorted(self._root.rglob("*.md")))
        readme = Path("README.md")
        if readme.exists():
            files.append(readme)
        # deterministic de-dupe
        seen: set[str] = set()
        out: list[Path] = []
        for p in files:
            k = str(p.resolve())
            if k in seen:
                continue
            seen.add(k)
            out.append(p)
        return out

    def _build_index(self) -> None:
        chunks: list[_Chunk] = []
        for p in self._iter_markdown_files():
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                text = p.read_text(encoding="utf-8", errors="replace")
            doc_id = str(p).replace("\\", "/")
            for i, c in enumerate(_chunk_text(text)):
                chunks.append(_Chunk(doc_id=doc_id, chunk_id=f"{i}", text=c))

        self._chunks = chunks
        N = len(chunks) or 1

        # DF
        df: dict[str, int] = {}
        token_sets: list[set[str]] = []
        for ch in chunks:
            ts = set(_tokens(ch.text))
            token_sets.append(ts)
            for t in ts:
                df[t] = df.get(t, 0) + 1

        self._idf = {t: (math.log((1 + N) / (1 + d)) + 1.0) for t, d in df.items()}

        vecs: list[dict[str, float]] = []
        norms: list[float] = []
        for ch in chunks:
            toks = _tokens(ch.text)
            tf: dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            v: dict[str, float] = {}
            for t, c in tf.items():
                if t in self._idf:
                    v[t] = (1.0 + math.log(c)) * self._idf[t]
            n = math.sqrt(sum(w * w for w in v.values())) or 1.0
            vecs.append(v)
            norms.append(n)

        self._vecs = vecs
        self._norms = norms

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        q_toks = _tokens(query)
        if not q_toks:
            return []

        q_tf: dict[str, int] = {}
        for t in q_toks:
            q_tf[t] = q_tf.get(t, 0) + 1

        qv: dict[str, float] = {}
        for t, c in q_tf.items():
            idf = self._idf.get(t)
            if idf is None:
                continue
            qv[t] = (1.0 + math.log(c)) * idf

        qn = math.sqrt(sum(w * w for w in qv.values())) or 1.0

        scored: list[tuple[float, int]] = []
        for i, v in enumerate(self._vecs):
            dot = 0.0
            for t, qw in qv.items():
                vw = v.get(t)
                if vw is not None:
                    dot += qw * vw
            score = dot / (qn * self._norms[i])
            if score > 0:
                scored.append((score, i))

        scored.sort(key=lambda x: (-x[0], self._chunks[x[1]].doc_id, self._chunks[x[1]].chunk_id))
        hits: list[SearchHit] = []
        for score, i in scored[:top_k]:
            ch = self._chunks[i]
            hits.append(
                SearchHit(score=score, doc_id=ch.doc_id, chunk_id=ch.chunk_id, text=ch.text)
            )

        return hits
