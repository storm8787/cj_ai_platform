# 통계분석 (Pandas Agent)

## 1. 기능 개요

- **목적**: CSV/Excel 데이터를 업로드하고 자연어로 질의하면 LangChain Pandas Agent가 분석 수행
- **사용 대상**: 데이터 분석이 필요한 충주시청 공무원
- **처리 내용**: 파일 업로드 → DataFrame 생성 → 자연어 질의 → LangChain Agent 분석 → 결과 반환

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/data_analysis.py` |
| 프론트엔드 페이지 | `frontend/src/pages/DataAnalysis.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/data-analysis` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/data-analysis/upload` | CSV/Excel 업로드 및 준비 |
| POST | `/api/data-analysis/analyze` | 자연어 질의로 분석 |
| DELETE | `/api/data-analysis/file/{file_id}` | 임시 파일 삭제 |

---

## 4. 주요 데이터 흐름

```
CSV/Excel 업로드
    ↓
pandas로 DataFrame 생성
→ parquet 임시 저장 (file_id 발급)
→ 컬럼별 dtype/null/unique 정보 반환
    ↓
자연어 질의 입력
    ↓
LangChain create_pandas_dataframe_agent
    + OpenAI gpt-4o-mini
    → Python 코드 생성 및 실행 (allow_dangerous_code=True)
    ↓
분석 결과 반환
```

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | LangChain Pandas Agent (gpt-4o-mini) |

- **LangChain**: `langchain`, `langchain-openai`, `langchain-experimental`
- **pandas**: 데이터 처리
- **pyarrow**: parquet 임시 저장

---

## 6. 수정 시 주의사항

> ⚠️ `allow_dangerous_code=True` — LangChain Agent가 임의 Python 코드를 실행함.
> 사용자 입력으로 인한 코드 인젝션 위험에 유의.

- 임시 파일은 명시적으로 DELETE 호출하거나 서버 재시작 시 제거됨
- LangChain 버전: `langchain==0.2.16`, `langchain-experimental==0.0.65` 고정

---

## 7. 테스트 및 검증 방법

- 샘플 CSV 업로드 후 `file_id` 확인
- POST `/analyze`에 "평균을 구해줘" 같은 간단한 질의 전송
- 응답에 분석 결과 텍스트 포함 여부 확인

---

## 8. 향후 개선 과제

- 코드 실행 샌드박스 도입 (보안 강화)
- 분석 결과 시각화 (차트 이미지 반환)
- 세션 기반 multi-turn 분석 대화
