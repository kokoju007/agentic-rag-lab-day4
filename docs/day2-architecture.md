# Day-2 Architecture

## 목표
- `/ask → Orchestrator → Agent` 흐름의 최소 멀티 에이전트 구조를 제공한다.

## 구성요소
- **Orchestrator**: 규칙 기반으로 질문을 분류하고 적절한 Agent를 선택한다.
- **DirectAnswerAgent**: 문서가 아닌 일반 질문에 임시 답변을 반환한다.
- **DocSearchAgent**: `docs/**/*.md`에서 키워드/라인 매칭으로 증거를 찾는다.

## 요청 흐름
1. `/ask`가 질문을 수신한다.
2. Orchestrator가 질문을 검사해 Agent를 선택한다.
3. 선택된 Agent가 답변과 증거를 반환한다.
4. 응답에는 `trace_id`와 빈 `citations` 목록이 포함된다.

## 라우팅 규칙
- 문서성 키워드(`/ask`, `엔드포인트`, `docs`, `day-1` 등)가 포함되면 DocSearchAgent.
- 그 외는 DirectAnswerAgent.

## 다음 확장 포인트
- 벡터 검색/임베딩 기반 DocSearch 강화.
- Agent별 도구 호출 및 체이닝.
- 라우팅을 분류 모델 또는 정책 테이블로 확장.
