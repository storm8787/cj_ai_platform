# 업무보고 작성기

## 1. 기능 개요

- **목적**: 입력한 키워드·내용을 바탕으로 공문 형식의 업무보고 문서 자동 생성
- **사용 대상**: 충주시청 공무원 (계획보고, 대책보고, 상황보고, 분석보고 등)
- **처리 내용**: 보고서 유형 선택 → 내용 입력 → GPT-4o로 섹션별 보고서 생성

---

## 2. 관련 파일

| 역할 | 파일 경로 |
|------|---------|
| 백엔드 라우터 | `backend/routers/report_writer.py` |
| 프롬프트 관리 | `backend/services/prompt_service.py` |
| HWPX 생성기 | `backend/services/hwpx_writer.py` |
| 프론트엔드 페이지 | `frontend/src/pages/ReportWriter.jsx` |

---

## 3. 주요 API 엔드포인트

API prefix: `/api/report-writer` (main.py에서 등록)

| 메서드 | 경로 | 설명 |
|-------|------|------|
| GET | `/api/report-writer/structures` | 보고서 유형 및 템플릿 목록 |
| POST | `/api/report-writer/generate` | 보고서 생성 |
| POST | `/api/report-writer/export-hwpx` | 편집된 보고서를 HWPX(한글) 파일로 다운로드 |
| GET | `/api/report-writer/status` | 서비스 상태 |

---

## 4. 주요 데이터 흐름

1. 사용자: 보고서 유형 선택 (**5개 카테고리**, 각 3~4개 세부 유형 = 총 16개)
2. 필수 입력: 제목, 유형/세부유형, 핵심 키워드(쉼표 구분), 분량
3. 선택 입력: 부서명, 작성자, 보고일자, **확인된 사실(자유 서술)** — 비우면 키워드 중심 생성
4. GPT-4o로 섹션별 보고서 생성 (확인된 사실을 최우선 근거로 사용, 미확인 수치는 자리표시자 처리)
5. 후처리:
   - 종결어미 개괄식 변환 — **항목 내 모든 문장** 대상(날짜 `2026. 1. 15.`·소수 `3.2`는 문장 분리 제외)
   - 마크다운 불릿(`-`,`*`,`•`)만 제거하고 **개조식 번호(1. 가. 1) ①)는 보존**
   - 행정기호 보존(`「」 → ℃ ㎡ ① ※` 등), 천단위 콤마 삽입
6. 응답: `sections` 배열 (title, order, content) + 머리말 정보(department, author, report_date)
   - `content` 항목이 개조식 번호로 시작하면 프론트가 해당 번호로 렌더링(없으면 `❍`)

### 입력 필드 (`ReportGenerateRequest`)

| 필드 | 필수 | 설명 |
|------|------|------|
| `title` | ✅ | 보고서 제목 |
| `report_type` / `detail_type` | ✅ | 대분류 / 세부유형 |
| `keywords` | ✅ | 핵심 키워드 (쉼표 구분) |
| `length` | | 간략/표준/상세 (섹션당 항목 수 + 항목당 문장 수 제어) |
| `department` / `author` / `report_date` | | 문서 머리말 (HWPX 대비) |
| `facts` | | 확인된 사실·배경·현황 자유 서술 |
| `custom_sections` | | 목차 커스터마이즈 (비면 기본 목차). 프론트 목차 편집 UI에서 전달 |

### 분량 규칙 (`LENGTH_RULES`)

| 분량 | 섹션당 항목 수 | 항목당 문장 수 |
|------|--------------|--------------|
| 간략 | 3~4 | 1~2 |
| 표준 | 4~6 | 2~3 |
| 상세 | 6~8 | 3~4 |

> ⚠️ 이전 문서에는 "4개 카테고리 / 부서·배경 입력"으로 적혀 있었으나, 실제 코드 기준으로 정정함.

---

## 5. 환경변수 및 외부 의존성

| 환경변수 | 역할 |
|---------|------|
| `OPENAI_API_KEY` | GPT-4o 보고서 생성 |

---

## 6. 수정 시 주의사항

- 보고서 유형별 작성 스타일: 서술형/나열형/효과형/방안형/분석형
- 프롬프트: `prompt_service.get("report_writer", ...)` 패턴으로 Supabase 관리 가능 (DB 우선 → 코드 fallback)
  - `system_prompt`, `build_prompt_template` 두 키는 DB에 없어도 관리자 '프롬프트 관리'에 **코드 기본값('미저장')으로 표시·수정 가능** (`services/prompt_defaults.py` 등록)
  - ⚠️ DB에 구버전 `build_prompt_template`이 저장돼 있으면 1·3단계 프롬프트 개선(사실/메타 치환자 등)이 반영 안 됨 → 관리자 화면에서 최신 내용으로 갱신 필요
- 후처리 로직 (용어 교정, 마크다운 제거) 라우터 내에 있음

---

## 7. 테스트 및 검증 방법

- `GET /api/report-writer/structures`로 유형 목록 확인
- POST `/generate`에 샘플 내용 전송 후 섹션 구조 확인

---

## 8. 향후 개선 과제

- 생성 보고서 HWPX 내보내기 기능 (머리말 정보 department/author/report_date 활용)
- ✅ 목차(섹션) 편집 UI — 프론트에서 항목 이름 수정·추가·삭제·순서 변경 가능 (2단계 완료)
- ✅ 후처리 품질 개선 — 문장단위 종결어미 교정, 개조식 번호 보존, 행정기호 보존 (3단계 완료)
- ✅ 생성 결과 인라인 편집 UX — '내용 편집' 토글로 제목·요약·섹션 제목·항목 수정/추가/삭제/순서변경, 편집 결과가 복사·TXT·HWPX에 반영 (4단계 완료)
- ✅ HWPX(한글) 내보내기 — `services/hwpx_writer.py`가 편집된 report를 OWPML(zip) HWPX로 변환 (5단계 완료)
- 보고서 유형 추가 (현재 5카테고리)

---

## 9. HWPX 내보내기 (services/hwpx_writer.py)

- **의존성**: 새 pip 패키지 없이 표준 라이브러리 `zipfile` + 기존 `lxml`만 사용 (CLAUDE.md 준수)
- **구조**: HWPX는 OWPML 규격 zip 컨테이너
  - `mimetype`(무압축, 최상단) · `version.xml` · `META-INF/container.xml` · `Contents/content.hpf` · `Contents/header.xml` · `Contents/section0.xml` · `settings.xml`
- **서식**: 제목(가운데 16pt bold) → 머리말(부서·보고일자·작성자) → □요약 → ■섹션 제목 → 개조식 본문
  - 개조식 번호(가./1)/①)는 텍스트로 보존, 한글 소분류·원문자는 들여쓰기(paraPr left margin), 마커 없는 항목은 `○` 부여
- **검증 한계 (중요)**: 이 저장소/CI 환경에는 한글(HWP)이 없어 **구조적 유효성(zip 레이아웃·XML well-formed·ID 참조 일관성)까지만 자동 검증**됨.
  실제 한글에서의 열림/렌더링은 배포 후 사용자가 확인해야 함.
  - 만약 열리지 않으면 `hwpx_writer.py`의 `_HEADER_XML` / `_sec_pr()` 를 실제 한글에서 저장한 빈 HWPX의 header.xml / secPr로 교체하면 확실히 호환됨(코드가 이 교체를 쉽게 하도록 분리되어 있음)
- **미포함(향후)**: 결재란 표, 제목 테두리 상자 — 컨테이너 호환이 확인된 뒤 추가 권장
