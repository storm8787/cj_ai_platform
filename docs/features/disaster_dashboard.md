# 재난상황 대시보드

## 1. 기능 개요

- **목적**: 카카오톡 재난상황 단톡방 TXT 파일을 업로드하면, 메시지를 파싱하여 사고별로 분류하고 현황 대시보드와 일일 보고서를 자동 생성
- **사용 대상**: 재난 대응 담당 공무원
- **처리 내용**: TXT 파싱 → 메시지 저장 → 사고 재구성 → 대시보드 통계 → 일일보고 생성

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/disaster_dashboard.py` |
| 사고 재구성 서비스 | `backend/services/disaster_incident_service.py` |
| 일일보고 생성 | `backend/services/disaster_report_service.py` |
| TXT 파싱 | `backend/services/disaster_parser_service.py` |
| 상수 정의 | `backend/services/disaster_constants.py` |
| 재난상황 훅 | `frontend/src/hooks/useDisasterSession.js` |
| 재난 상수 | `frontend/src/constants/disaster.js` |
| 업로드 페이지 | `frontend/src/pages/DisasterUpload.jsx` |
| 대시보드 페이지 | `frontend/src/pages/DisasterDashboard.jsx` |
| 사고 목록 | `frontend/src/pages/DisasterIncidents.jsx` |
| 일일보고 | `frontend/src/pages/DisasterDailyReport.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/disaster` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/api/disaster/upload` | 카카오톡 TXT 업로드 |
| GET | `/api/disaster/uploads` | 업로드 목록 |
| POST | `/api/disaster/analyze/{upload_id}` | 업로드 분석 (메시지 파싱 → 사고 재구성) |
| GET | `/api/disaster/upload/{upload_id}/summary` | 업로드 요약 |
| GET | `/api/disaster/incidents` | 사고 목록 (필터: upload_id/status/type/emd) |
| GET | `/api/disaster/incidents/{incident_id}` | 사고 상세 + 연결 메시지 |
| GET | `/api/disaster/dashboard/overview` | 통계 (유형별/상태별/읍면동별/시간별) |
| POST | `/api/disaster/reports/daily/generate` | 일일보고 생성 (GPT-4o) |
| GET | `/api/disaster/reports` | 일일보고 목록 |

---

## 4. 주요 데이터 흐름

```
카카오톡 TXT 업로드
    ↓
disaster_parser_service: 메시지 파싱 (4가지 날짜 형식 지원)
    → disaster_raw_messages 테이블 저장
    ↓
disaster_incident_service: 사고 재구성
    → 위치 유사도 매칭 (difflib, 80% threshold)
    → 상태 변경 추적 (reported → in_progress → completed/closed)
    → disaster_incidents 테이블 저장
    ↓
대시보드 통계 집계 (유형/상태/읍면동/시간대별)
    ↓
일일보고 생성 (gpt-4o, GPT-4o 자연어 보고서)
```

---

## 5. 핵심 구현 세부 사항

### 메시지 파싱 (4가지 날짜 형식)

- 한국어 형식: `2025년 7월 15일 오후 3:30`
- 점 형식: `2025. 7. 15. 오후 3:30`
- 구분선: `--------- 2025년 7월 15일 월요일 ---------`
- 대괄호 형식: `[홍길동] [오후 3:30] 메시지`

### EMD(읍면동) 추출 4단계 전략 (v8 개선)

1. `[대괄호]` 표기 전처리: `[호암직동]` → `호암직동` 으로 변환 후 매칭
2. `EMD_LIST` 공식 행정동명 직접 매칭 (`backend/data/eup_myeon_dong.txt`, 25개)
3. `EMD_ALIASES` 별칭 → 공식명 변환 (예: 호암동→호암직동, 가금면→금가면)
4. `RI_TO_EMD` 리(里) → 상위 읍면동 역조회 (`backend/data/ri_to_emd.json`, 33개 리)
5. Fallback 정규식 — **공식 목록에 있는 EMD만 반환** (임의 단어 오매칭 방지)

> ⚠️ `eup_myeon_dong.txt`에 없는 읍면동은 절대 반환하지 않음.  
> "00리" 패턴은 `ri_to_emd.json` 매핑으로 상위 읍면동을 찾아 반환.

### 사고 유형 분류 우선순위 (v8: 겨울 재난 추가)

| 유형 코드 | 한글 | 대표 키워드 | 계절 |
|-----------|------|------------|------|
| `landslide` | 산사태·토사유출 | 산사태, 토사, 낙석, 눈사태 | 여름/겨울 |
| `tree_fall` | 나무전도 | 나무전도, 수목전도, 나무 쓰러 | 연중 |
| `cold_wave` | 한파·동파 | 한파, 동파, 수도동파, 동결 | **겨울** |
| `heavy_snow` | 폭설·제설 | 폭설, 제설, 적설, 눈 쌓임 | **겨울** |
| `icing` | 도로결빙 | 결빙, 빙판, 블랙아이스 | **겨울** |
| `drainage` | 배수·맨홀·양수 | 맨홀, 역류, 배수, 양수 | 여름 |
| `flood` | 침수·범람 | 침수, 범람, 수위, 하천 | 여름 |
| `sinkhole` | 싱크홀·노면파손 | 싱크홀, 함몰, 노면파손 | 연중 |
| `rescue` | 수색·구조 | 실종, 수색, 인명구조 | 연중 |
| `facility` | 시설물 이상 | 시설물, 교량, 정전, 균열 | 연중 |
| `road_control` | 도로통제 | 통제, 차단, 통행제한 | 연중 |
| `inspection` | 기타/미분류 | (해당 없음) | - |

### 사고 상태 분류 (우선순위 순)

- `closed`: "해제|통행 재개|개통|상황 종료"
- `completed`: "복구 완료|처리 완료|제설 완료|염화칼슘 살포 완료|..."
- `in_progress`: "조치중|수색중|작업중|제설중|..."
- `monitoring`: "모니터링|설치 완료|이상없음"
- `reported`: (기본값 / "~예정")

### 사고 병합 로직 (상태 흐름 기반 그룹핑)

- 같은 `(emd, incident_type, location)` 메시지는 하나의 사건으로 병합
- 유형 호환 그룹: `flood ↔ drainage ↔ road_control`, `landslide ↔ road_control`, etc.
- 위치 유사도 ≥ 80% (`difflib.SequenceMatcher`)
- 접두어 매칭: "목행용탄동" vs "목행용탄동 용탄교 진입로" → 0.85점 처리
- `closed` 상태를 만나면 사건 종결 → 이후 같은 위치 메시지는 새 사건으로 인식

### 동시 분석 방지

- `analysis_status` 필드: `uploaded` → `analyzing` → `analyzed`
- `analyzing` 중 중복 호출 시 **409 Conflict** 반환

### 대시보드 overview API 응답 필드 (v7.1+)

| 필드 | 설명 |
|------|------|
| `total` | 전체 사건 수 |
| `active_count` | 진행중 사건 수 |
| `done_count` | 완료/종결 사건 수 |
| `affected_emd_count` | 사건 발생 읍면동 수 |
| `top_type` / `top_type_label` | 최다 발생 유형 코드·라벨 |
| `by_type` / `by_type_labeled` | 유형별 집계 (코드키 / 한글라벨키) |
| `by_status` / `by_status_labeled` | 상태별 집계 |
| `by_emd` | 읍면동별 집계 |
| `recent_incidents` | 최근 업데이트 사건 10건 (type_label, status_label 포함) |
| `emd_map_data` | 읍면동별 위경도·사건수·진행중 수 목록 |

---

## 6. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | 일일보고 GPT-4o 생성 |
| `SUPABASE_URL`, `SUPABASE_KEY` | 모든 데이터 저장 |
| `VITE_KAKAO_MAP_KEY` (프론트) | 카카오맵 표시 (없으면 EMD 도트맵 fallback) |

**Supabase 테이블**:
- `disaster_uploads`: 업로드 파일 정보 + 분석 상태
- `disaster_raw_messages`: 파싱된 메시지
- `disaster_incidents`: 재구성된 사고 목록
- `disaster_incident_messages`: 사고-메시지 연결 테이블
- `disaster_daily_reports`: 일일보고 저장

---

## 7. 수정 시 주의사항

- 일일보고 생성 모델: `gpt-4o` (다른 기능의 `gpt-4o-mini`와 다름)
- 프롬프트: `prompt_service.get("disaster", ...)` 패턴 (3단계 fallback)
- TXT 파일 인코딩: UTF-8 / CP949 자동 감지
- 빈 배열 insert 방지: `if incident_rows: insert(...)` 가드 필요 (없으면 crash)
- 개인정보: 일일보고 GPT 프롬프트에 보고자 이름 포함하지 않도록 주의
- 프론트엔드: `useDisasterSession()` 훅 사용 (sessionStorage 리액티브)
- 상수 변경 시: `backend/services/disaster_constants.py`와 `frontend/src/constants/disaster.js` 양쪽 모두 업데이트 필요

---

## 8. 테스트 및 검증 방법

### 자동화 검증 스크립트

```bash
cd /home/user/cj_ai_platform
python backend/tests/evaluate_disaster_dashboard.py
```

7개 항목을 자동 검증 (PASS/WARN/FAIL 결과):
1. TXT 파싱 (메시지 수, 날짜 파싱)
2. EMD 추출 (별칭 포함)
3. 사고 유형 분류 (rescue, drainage, flood 등)
4. 상태 분류 (closed, in_progress, completed 등)
5. 사건 병합 (유형 호환 그룹, 위치 유사도)
6. Overview 구조 (active_count, done_count 등 신규 필드 포함)
7. 위치 유사도 임계값 동작

**샘플 데이터**: `backend/tests/fixtures/disaster_sample_kakao.txt`
- 충주시 12개 읍면동, 9가지 사고 유형, 75개 메시지

### 수동 확인

- 카카오톡 TXT 파일 업로드 후 `/api/disaster/analyze/{id}` 호출
- `GET /api/disaster/incidents` 응답에서 사고 분류·상태 확인
- `GET /api/disaster/dashboard/overview` 통계 데이터 및 `emd_map_data` 확인
- 일일보고 생성 후 `report_text` 내용 품질 확인

---

## 9. 대시보드 UI 구성 (v7.1)

`frontend/src/pages/DisasterDashboard.jsx`

- **요약 카드 5개**: 총 사건·진행중(빨간 하이라이트)·완료종결·발생읍면동·최다유형
- **지도 영역**: `VITE_KAKAO_MAP_KEY` 있으면 카카오맵, 없으면 EMD 도트맵 fallback
  - 도트맵: 위경도 기준 EMD 위치에 버블 배치, 크기=사건 수, 빨강=진행중·초록=완료
  - hover 시 EMD명·전체/진행중 건수 툴팁 표시
- **최근 사건 카드**: 유형/상태 필터 + 최근 10건 목록
- **차트 3개**: 유형별·상태별·읍면동별 수평 바 차트 (외부 라이브러리 미사용)

---

## 10. 향후 개선 과제

- 파싱 규칙 외 형식의 카카오톡 메시지 처리 (신규 버전 대응)
- 사고 유형 분류 정확도 개선 (현재 키워드 기반)
- 실시간 업데이트 (WebSocket 또는 polling)
- 지도에서 사건 클릭 시 상세 화면 연동
