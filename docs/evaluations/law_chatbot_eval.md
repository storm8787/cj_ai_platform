# 법령 챗봇 자동 평가 시스템

## 개요

법령·자치법규 챗봇의 답변 품질을 정량적으로 평가하는 자동화 시스템입니다.

- **평가 케이스**: `backend/tests/law_chatbot_eval_cases.json` (10개)
- **평가 스크립트**: `backend/tests/evaluate_law_chatbot.py`
- **GitHub Actions**: `.github/workflows/law-chatbot-eval.yml` (수동 트리거)

---

## 평가 케이스 구조 (`law_chatbot_eval_cases.json`)

```json
{
  "id": "TC-001",
  "category": "여비",
  "question": "공무원이 출장 중 개인 차량을 이용한 경우 여비 지급 기준은?",
  "required_keywords": ["여비", "자동차운임", "자가용"],
  "required_any_of": [
    ["공무원여비규정", "여비 규정", "여비업무", "공무원 여비"],
    ["자가용", "개인차량", "자동차운임", "운임"]
  ],
  "forbidden_phrases": [
    "해당 내용에 대한 정확한 정보를 찾지 못했습니다"
  ],
  "fail_if_only": ["상시출장공무원 여비지급 규정"],
  "description": "국가 공무원여비규정에서 자가용 사용 시 자동차운임 지급 기준을 찾아야 함"
}
```

---

## 평가 기준 상세

| 항목 | 설명 | 점수 처리 |
|------|------|----------|
| `required_keywords` | 반드시 포함되어야 하는 키워드 | 개당 +1점, 없으면 감점 |
| `required_any_of` | 각 그룹에서 최소 1개 이상 포함 | 그룹당 +1점 |
| `forbidden_phrases` | 포함되면 안 되는 문구 | 포함 시 감점 |
| `fail_if_only` | 이것만 근거로 쓰면 실패 | 다른 필수 키워드와 함께 있으면 통과 |

모든 항목 통과 시 `passed: true`, 하나라도 실패 시 `passed: false`.

---

## 현재 테스트 케이스 목록

| ID | 카테고리 | 질문 요약 | 핵심 검증 법령 |
|----|--------|--------|-------------|
| TC-001 | 여비 | 개인차량 출장 여비 기준 | 공무원여비규정 |
| TC-002 | 정보공개 | 비공개 사유 | 정보공개법 제9조 |
| TC-003 | 수의계약 | 지방계약 수의계약 금액 기준 | 지방계약법 시행령 |
| TC-004 | 청탁금지법 | 식사 가액 기준 | 청탁금지법, 3만원 |
| TC-005 | 지방보조금 | 민간단체 보조금 절차 | 지방보조금 관리 법령 |
| TC-006 | 도로법 | 도로점용 위반 조치 | 도로법, 원상회복/변상금 |
| TC-007 | 육아휴직수당 | 지방공무원 육아휴직수당 | 지방공무원 수당 등에 관한 규정 |
| TC-008 | 개인정보 | 제3자 제공 기준 | 개인정보보호법 제17조 |
| TC-009 | 자치법규-연임 | 충주시 위원회 연임 횟수 | 충주시 조례 |
| TC-010 | 경품 | 지자체 경품 지급 가능 여부 | 공직선거법, 지방재정법 |

---

## 평가 실행 방법

### 로컬 실행

```bash
cd backend

# mock 평가 (API 키 불필요, 평가 로직 검증용)
python tests/evaluate_law_chatbot.py --mode mock

# planner 평가 (OPENAI_API_KEY 필요, 검색계획 품질 평가)
python tests/evaluate_law_chatbot.py --mode planner

# live 평가 (실행 중인 서버 필요, 전체 답변 품질 평가)
python tests/evaluate_law_chatbot.py --mode live --base-url http://localhost:8000

# 특정 케이스만 실행
python tests/evaluate_law_chatbot.py --mode mock --cases TC-001 TC-004

# 결과 JSON 저장
python tests/evaluate_law_chatbot.py --mode mock --output /tmp/eval_result.json
```

### GitHub Actions 실행

1. GitHub → Actions → "Law Chatbot Evaluation" 워크플로우
2. "Run workflow" 클릭
3. 파라미터 선택:
   - `mode`: mock 또는 planner
   - `case_ids`: 특정 케이스 ID (비워두면 전체)
4. 결과 아티팩트: `law-chatbot-eval-results` (30일 보관)

---

## 평가 모드별 특성

| 모드 | 필요 조건 | 평가 대상 | 용도 |
|-----|---------|---------|------|
| `mock` | 없음 | 하드코딩된 모범 답변 | 평가 로직 검증 |
| `planner` | `OPENAI_API_KEY` | GPT 검색계획 품질 | 검색계획 개선 확인 |
| `live` | 실행 중인 서버 + `LAW_API_OC` | 전체 답변 품질 | 최종 답변 품질 평가 |

---

## 평가 결과 출력 형식

```
결과: 10/10 통과
  ✅ [TC-001] 여비  100.0점
  ✅ [TC-002] 정보공개  100.0점
  ...

결과 JSON:
{
  "mode": "mock",
  "elapsed_seconds": 0.1,
  "passed": 10,
  "total": 10,
  "results": [
    {
      "case": { "id": "TC-001", ... },
      "result": {
        "passed": true,
        "score": 100.0,
        "details": [...]
      }
    }
  ]
}
```

---

## 새 평가 케이스 추가 방법

`backend/tests/law_chatbot_eval_cases.json`에 아래 형식으로 추가:

```json
{
  "id": "TC-011",
  "category": "카테고리명",
  "question": "질문 텍스트",
  "required_keywords": ["반드시 있어야 할 단어"],
  "required_any_of": [
    ["관련 법령명 후보들"],
    ["핵심 조문 키워드들"]
  ],
  "forbidden_phrases": ["있으면 안 되는 문구"],
  "fail_if_only": ["이것만 근거로 쓰면 실패할 키워드"],
  "description": "이 테스트 케이스의 의도 설명"
}
```

---

## 평가 결과 해석

- **mock 10/10**: 평가 로직 정상. 코드 수정 전 반드시 통과 확인.
- **planner 일부 실패**: GPT planner 검색계획 품질 문제 → `legal_query_planner.py` 프롬프트 수정
- **live 일부 실패**: 답변 품질 문제 → 원인 분석 (검색 실패? 조문 선별 실패? 답변 생성 실패?)
