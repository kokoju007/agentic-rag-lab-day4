from __future__ import annotations

import re
from pathlib import Path

from agents.base import AgentResult


class DocSearchAgent:
    name = "doc_search"

    def __init__(self, docs_path: Path | None = None) -> None:
        self._docs_path = docs_path or Path("docs")

    def run(self, question: str) -> AgentResult:
        keywords = self._extract_keywords(question)
        evidence: list[str] = []
        if self._docs_path.exists():
            for path in sorted(self._docs_path.rglob("*.md")):
                try:
                    lines = path.read_text(encoding="utf-8").splitlines()
                except OSError:
                    continue
                for line_number, line in enumerate(lines, start=1):
                    if self._matches(line, keywords):
                        evidence.append(f"{path.as_posix()}:{line_number}: {line.strip()}")
                    if len(evidence) >= 5:
                        break
                if len(evidence) >= 5:
                    break

        if evidence:
            answer = "문서에서 관련 내용을 찾았습니다. 증거를 확인해주세요."
        else:
            answer = "문서에서 관련 내용을 찾지 못했습니다."

        return AgentResult(answer=answer, evidence=evidence)

    def _extract_keywords(self, question: str) -> list[str]:
        tokens = re.findall(r"[\w/.-]+", question.lower())
        return [token for token in tokens if len(token) > 1]

    def _matches(self, line: str, keywords: list[str]) -> bool:
        lowered = line.lower()
        return any(keyword in lowered for keyword in keywords)
