# Day-2 회고

## Day-2 목표
- `/ask → Orchestrator → Agents` 흐름을 최소 구조로 구현한다.
- 문서 질문과 일반 질문을 구분해 라우팅한다.
- 테스트로 라우팅과 응답 형식을 검증한다.

## 구현한 구조
- FastAPI `/ask`가 Orchestrator를 호출한다.
- Orchestrator가 규칙 기반으로 Agent를 선택한다.
- 선택된 Agent가 `answer`와 `evidence`를 반환한다.

## 에이전트 2개 역할
- **DocSearchAgent**: `docs/**/*.md`에서 키워드 기반으로 근거를 찾는다.
- **DirectAnswerAgent**: 일반 질문에 임시 답변을 제공한다.

## 라우팅 규칙
- `/ask`, `docs`, `day-1`, `엔드포인트` 등 문서성 키워드가 포함되면 DocSearchAgent.
- 그 외 질문은 DirectAnswerAgent.

## 테스트로 증명한 것
- `/health`가 200을 반환한다.
- 문서성 질문은 `doc_search`로 라우팅되고 evidence가 1개 이상 나온다.
- 일반 질문은 `direct_answer`로 라우팅된다.

## 다음 단계(Day-3) 계획
- 문서 검색을 벡터 검색으로 확장한다.
- 라우팅을 규칙 기반에서 모델 기반으로 개선한다.
- Agent별 도구 호출과 체이닝을 추가한다.
