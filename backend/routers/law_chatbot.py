"""
법령정보 · 자치법규 챗봇 라우터 - 조문 검색 기반 구조

새 구조:
1. GPT가 사용자 질문을 '법률 쟁점/검색계획'으로 변환
2. 검색계획별 MCP 검색 수행
   - 국가법령
   - 자치법규
   - 행정규칙
3. 검색 후보의 전문/본문 조회
4. 본문을 조문 단위로 분리
5. 질문 및 조문 키워드와 관련 높은 조문만 선별
6. 선별된 조문 근거를 GPT에게 전달하여 최종 답변 생성

기존 구조와 차이:
- 기존: 키워드 → 법령 목록 → GPT 답변
- 신규: 법률 쟁점 → 법령/조례 전문 → 관련 조문 → GPT 답변
"""

import json
import pickle
import re
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import httpx
import numpy as np
import xml.etree.ElementTree as ET
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from FlagEmbedding import BGEM3FlagModel

from config import settings
from services.prompt_service import prompt_service
from services.korean_law_mcp_service import korean_law_mcp_service
from services.legal_query_planner import legal_query_planner


try:
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False
    print("[law-chatbot] ⚠️ rank_bm25 미설치, dense 검색만 사용")


router = APIRouter(prefix="/api/law-chatbot", tags=["law-chatbot"])

LAW_SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"
LAW_SERVICE_URL = "http://www.law.go.kr/DRF/lawService.do"

ANSWER_MODEL = "gpt-4o"

VECTORSTORE_DIR = Path(settings.LAW_CHATBOT_VECTORSTORE_PATH)
EMBEDDING_MODEL_NAME = settings.EMBEDDING_MODEL

VECTOR_SCORE_MIN = 0.30
VECTOR_SCORE_RELATIVE = 0.85

MAX_SEARCH_PLANS = 6
MAX_CANDIDATES_PER_PLAN = 4
MAX_DETAIL_DOCS = 5
MAX_ARTICLES_FOR_ANSWER = 12
MAX_CONTEXT_CHARS = 60000

_faiss_index = None
_faiss_data = None
_embedding_model = None
_bm25_index = None
_bm25_corpus = None


_DEFAULT_ANSWER_SYSTEM = """당신은 충주시청 공무원을 위한 법령·자치법규 전문 AI 어시스턴트입니다.

[역할]
공무원이 실무에서 바로 활용할 수 있도록 정확하고 구체적인 법령 정보를 제공합니다.

[답변 원칙]
1. 반드시 [검색된 참고자료]에 포함된 조문·근거를 우선 사용하세요.
2. 결론을 먼저 제시하세요.
3. 조문번호, 법령명, 조례명을 임의로 만들어내지 마세요.
4. 검색자료에 없는 세부 수치, 기간, 횟수는 단정하지 마세요.
5. 법령명은 정식 명칭 그대로 사용하세요.
6. 자치법규 질문이면 국가법령만으로 답하지 말고, 자치법규 검색 결과를 우선 확인하세요.
7. 지방자치단체의 금품·경품·물품 제공 질문은 공직선거법상 기부행위 가능성을 반드시 유의사항으로 검토하세요.
8. 실무 적용 시 담당부서, 법제팀, 선관위, 개인정보보호 담당자 등 확인이 필요한 경우 명확히 표시하세요.

[답변 형식]
1. 결론
2. 근거
   - 📌 법령명/조례명 조문번호: 핵심 내용
3. 실무 적용 시 유의사항
   - ⚠️ 필요한 경우 작성
4. 참고 법령 목록
   - 📋 목록 형태

[검색된 참고자료]
{context}"""


# =========================================================
# Pydantic 모델
# =========================================================

class AskRequest(BaseModel):
    question: str
    search_scope: str = "all"
    chat_history: Optional[List[dict]] = None


class SearchRequest(BaseModel):
    query: str
    target: str = "law"
    page: int = 1
    display: int = 20


# =========================================================
# 벡터스토어 로드
# =========================================================

def _load_vectorstore():
    global _faiss_index, _faiss_data, _bm25_index, _bm25_corpus

    if _faiss_index is not None:
        return

    faiss_path = VECTORSTORE_DIR / "index.faiss"
    pkl_path = VECTORSTORE_DIR / "index.pkl"
    bm25_path = VECTORSTORE_DIR / "bm25_corpus.pkl"

    if not faiss_path.exists() or not pkl_path.exists():
        print(f"[law-chatbot] ⚠️ 벡터스토어 없음: {VECTORSTORE_DIR}")
        return

    try:
        _faiss_index = faiss.read_index(str(faiss_path))

        with open(pkl_path, "rb") as f:
            _faiss_data = pickle.load(f)

        print(f"[law-chatbot] ✅ 벡터스토어 로드 완료: {_faiss_index.ntotal}개 문서")

        if _BM25_AVAILABLE and bm25_path.exists():
            with open(bm25_path, "rb") as f:
                bm25_data = pickle.load(f)

            _bm25_corpus = bm25_data.get("tokenized_corpus", [])

            if _bm25_corpus:
                _bm25_index = BM25Okapi(_bm25_corpus)
                print(f"[law-chatbot] ✅ BM25 인덱스 로드 완료: {len(_bm25_corpus)}개 문서")

    except Exception as e:
        print(f"[law-chatbot] ⚠️ 벡터스토어 로드 실패: {e}")


def _load_embedding_model():
    global _embedding_model

    if _embedding_model is not None:
        return

    try:
        _embedding_model = BGEM3FlagModel(EMBEDDING_MODEL_NAME, use_fp16=True)
        print(f"[law-chatbot] ✅ BGEM3 임베딩 모델 로드 완료: {EMBEDDING_MODEL_NAME}")
    except Exception as e:
        print(f"[law-chatbot] ❌ BGEM3 임베딩 모델 로드 실패: {e}")
        _embedding_model = None


# =========================================================
# 엔드포인트
# =========================================================

@router.post("/ask")
async def ask_question(req: AskRequest):
    from openai import AsyncOpenAI

    question = req.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="질문이 비어 있습니다.")

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # 1. GPT 기반 법률 쟁점/검색계획 생성
    search_plan = await legal_query_planner.create_plan(question)

    print(f"[law-chatbot] 검색계획 생성 완료: {json.dumps(search_plan, ensure_ascii=False)}")

    # 2. 검색계획 기반 검색 및 조문 선별
    search_results = await _execute_legal_search_plan(
        question=question,
        search_plan=search_plan,
    )

    # 3. 최종 답변 생성
    answer = await _generate_answer(
        client=client,
        question=question,
        search_plan=search_plan,
        search_results=search_results,
        chat_history=req.chat_history,
    )

    return answer


@router.post("/search")
async def search_law(req: SearchRequest):
    """
    단순 검색 API.
    프론트에서 별도 검색 기능이 필요할 때 사용.
    """
    results = await _search_target(
        target=req.target,
        query=req.query,
        display=req.display,
    )

    return {
        "results": results,
        "query": req.query,
        "target": req.target,
    }


@router.get("/status")
async def get_status():
    _load_vectorstore()

    return {
        "vectorstore": {
            "loaded": _faiss_index is not None,
            "doc_count": _faiss_index.ntotal if _faiss_index else 0,
        },
        "api": await _check_api_connection(),
    }


@router.get("/categories")
async def get_categories():
    return {
        "categories": [
            {"id": "all", "name": "통합검색", "icon": "📚"},
        ]
    }


# =========================================================
# 검색계획 실행
# =========================================================

async def _execute_legal_search_plan(
    question: str,
    search_plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    검색계획 기반으로 MCP/API 검색 → 본문 조회 → 관련 조문 선별
    """
    plans = search_plan.get("search_plans", []) or []
    plans = sorted(plans, key=lambda x: x.get("priority", 999))[:MAX_SEARCH_PLANS]

    all_candidates: List[Dict[str, Any]] = []
    selected_articles: List[Dict[str, Any]] = []
    vector_results: List[Dict[str, Any]] = []

    # 1. 검색계획별 후보 검색
    for plan in plans:
        target = plan.get("target", "all")
        law_name = plan.get("law_name", "")
        article_keywords = plan.get("article_keywords", []) or []

        if not law_name:
            continue

        print(
            f"[law-chatbot] 검색계획 실행: "
            f"target={target}, law_name={law_name}, keywords={article_keywords}"
        )

        candidates = await _search_by_plan(plan)

        if candidates:
            for c in candidates:
                c["_plan"] = plan
            all_candidates.extend(candidates)

    all_candidates = _deduplicate_candidates(all_candidates)
    all_candidates = _rank_candidates(question, all_candidates)

    print(f"[law-chatbot] 후보 검색 완료: count={len(all_candidates)}")

    # 2. 후보별 본문 조회 및 조문 선별
    detail_count = 0

    for candidate in all_candidates[:MAX_DETAIL_DOCS]:
        plan = candidate.get("_plan", {})
        article_keywords = plan.get("article_keywords", []) or []

        full_text = candidate.get("content", "") or ""

        if not full_text or len(full_text.strip()) < 50:
            try:
                full_text = await asyncio.wait_for(
                    _get_full_text(candidate),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                print(f"[law-chatbot] ⚠️ 본문 조회 timeout: {candidate.get('name')}")
                full_text = ""
            except Exception as e:
                print(f"[law-chatbot] ⚠️ 본문 조회 실패: {candidate.get('name')} / {e}")
                full_text = ""

        if not full_text:
            continue

        detail_count += 1

        articles = _split_text_into_articles(full_text)

        relevant_articles = _select_relevant_articles(
            question=question,
            articles=articles,
            article_keywords=article_keywords,
            law_name=candidate.get("name", ""),
            target=candidate.get("type", ""),
            source=candidate.get("source", ""),
        )

        for article in relevant_articles:
            article["law_name"] = candidate.get("name", "")
            article["target"] = candidate.get("type", "")
            article["category"] = candidate.get("category", "")
            article["enforcement_date"] = candidate.get("enforcement_date", "")
            article["source"] = candidate.get("source", "")
            article["candidate_id"] = candidate.get("id", "")
            article["plan_reason"] = plan.get("reason", "")
            selected_articles.append(article)

        if len(selected_articles) >= MAX_ARTICLES_FOR_ANSWER:
            break

    selected_articles = _deduplicate_articles(selected_articles)
    selected_articles = sorted(
        selected_articles,
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:MAX_ARTICLES_FOR_ANSWER]

    # 3. 자치법규 질문인데 조문이 없으면 벡터스토어 fallback
    if not selected_articles and _looks_like_local_question(question):
        print("[law-chatbot] 자치법규 조문 결과 없음 → 벡터스토어 fallback 시작")

        try:
            vector_results = await asyncio.wait_for(
                asyncio.to_thread(_search_vectorstore, question, 7),
                timeout=20.0,
            )
            vector_results = vector_results[:5]
            print(f"[law-chatbot] 벡터스토어 fallback 종료: count={len(vector_results)}")
        except asyncio.TimeoutError:
            print("[law-chatbot] 벡터스토어 fallback timeout")
            vector_results = []
        except Exception as e:
            print(f"[law-chatbot] 벡터스토어 fallback 실패: {e}")
            vector_results = []

    print(
        f"[law-chatbot] 검색계획 최종결과: "
        f"candidates={len(all_candidates)}, details={detail_count}, "
        f"articles={len(selected_articles)}, vector={len(vector_results)}"
    )

    return {
        "candidates": all_candidates,
        "selected_articles": selected_articles,
        "vector_results": vector_results,
        "detail_count": detail_count,
    }


async def _search_by_plan(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    target = plan.get("target", "all")
    law_name = plan.get("law_name", "")
    article_keywords = plan.get("article_keywords", []) or []

    queries = [law_name]

    # 법령명 + 핵심 조문 키워드 조합도 보조 검색
    for kw in article_keywords[:2]:
        if kw and kw not in law_name:
            queries.append(f"{law_name} {kw}")

    queries = list(dict.fromkeys([q.strip() for q in queries if q.strip()]))[:3]

    results: List[Dict[str, Any]] = []

    for query in queries:
        if target == "law":
            results.extend(await _search_target("law", query, display=8))
        elif target == "ordin":
            results.extend(await _search_target("ordin", query, display=8))
        elif target == "admrul":
            results.extend(await _search_target("admrul", query, display=8))
        else:
            # all: 너무 많은 timeout을 막기 위해 3종 병렬
            task_results = await asyncio.gather(
                _safe_search_target("law", query, display=6),
                _safe_search_target("ordin", query, display=6),
                _safe_search_target("admrul", query, display=6),
                return_exceptions=True,
            )

            for tr in task_results:
                if isinstance(tr, list):
                    results.extend(tr)

        if results:
            break

    return _deduplicate_candidates(results)[:MAX_CANDIDATES_PER_PLAN]


async def _safe_search_target(target: str, query: str, display: int = 8) -> List[Dict[str, Any]]:
    try:
        return await asyncio.wait_for(
            _search_target(target, query, display=display),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        print(f"[law-chatbot] ⚠️ 검색 timeout: target={target}, query={query}")
        return []
    except Exception as e:
        print(f"[law-chatbot] ⚠️ 검색 실패: target={target}, query={query}, error={e}")
        return []


async def _search_target(target: str, query: str, display: int = 10) -> List[Dict[str, Any]]:
    """
    target별 검색.
    1순위 MCP
    2순위 기존 law.go.kr API fallback
    """
    mcp_results: List[Dict[str, Any]] = []

    try:
        if target == "law":
            mcp_results = await korean_law_mcp_service.search_law(
                query=query,
                target="law",
                display=display,
            )
        elif target == "ordin":
            mcp_results = await korean_law_mcp_service.search_ordinance(
                query=query,
                display=display,
            )
        elif target == "admrul":
            mcp_results = await korean_law_mcp_service.search_admin_rule(
                query=query,
                display=display,
            )

        if mcp_results:
            print(f"[law-chatbot] MCP 검색 성공: target={target}, query={query}, count={len(mcp_results)}")
            return mcp_results

    except Exception as e:
        print(f"[law-chatbot] MCP 검색 예외: target={target}, query={query}, error={e}")

    # admrul은 MCP 실패 시 API도 시도
    direct_results = await _search_law_api_direct(
        query=query,
        targets=[target],
        display=display,
    )

    if direct_results:
        print(f"[law-chatbot] law.go.kr fallback 검색 성공: target={target}, query={query}, count={len(direct_results)}")

    return direct_results


# =========================================================
# 본문 조회
# =========================================================

async def _get_full_text(candidate: Dict[str, Any]) -> str:
    target = candidate.get("type", "law")
    item_id = candidate.get("id", "")
    name = candidate.get("name", "")

    # 1. MCP 상세조회
    try:
        if target == "law":
            text = await korean_law_mcp_service.get_law_text(
                mst=item_id,
                law_name=name,
            )
        elif target == "ordin":
            text = await korean_law_mcp_service.get_ordinance_text(
                ordin_seq=item_id,
                ordinance_name=name,
            )
        elif target == "admrul":
            text = await korean_law_mcp_service.get_admin_rule_text(
                admin_rule_id=item_id,
                admin_rule_name=name,
            )
        else:
            text = ""

        if text and len(text.strip()) > 50:
            print(f"[law-chatbot] MCP 본문 조회 성공: target={target}, name={name}, chars={len(text)}")
            return text

    except Exception as e:
        print(f"[law-chatbot] MCP 본문 조회 실패: target={target}, name={name}, error={e}")

    # 2. 기존 law.go.kr API fallback
    if item_id:
        text = await _fetch_full_text_from_law_api(
            mst=item_id,
            target=target,
        )

        if text:
            print(f"[law-chatbot] law.go.kr 본문 조회 성공: target={target}, name={name}, chars={len(text)}")
            return text

    return ""


async def _fetch_full_text_from_law_api(mst: str, target: str) -> str:
    oc = settings.LAW_API_OC

    if not oc:
        return ""

    if target not in ("law", "ordin", "admrul"):
        target = "law"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                LAW_SERVICE_URL,
                params={
                    "OC": oc,
                    "target": target,
                    "MST": mst,
                    "type": "XML",
                },
            )

            text = resp.content.decode("utf-8", errors="ignore")

            if text.strip().startswith("<!DOCTYPE") or text.strip().startswith("<html"):
                return ""

            return text

    except Exception as e:
        print(f"[law-chatbot] law.go.kr 본문 조회 실패: MST={mst}, target={target}, error={e}")
        return ""


# =========================================================
# 조문 분리 / 선별
# =========================================================

def _split_text_into_articles(text: str) -> List[Dict[str, Any]]:
    """
    XML 또는 일반 텍스트를 조문 단위로 분리
    """
    if not text:
        return []

    stripped = text.strip()

    if stripped.startswith("<"):
        parsed = _parse_articles_from_xml(stripped)
        if parsed:
            return parsed

    # JSON 문자열인 경우
    try:
        data = json.loads(stripped)
        json_articles = _extract_articles_from_json(data)
        if json_articles:
            return json_articles
    except Exception:
        pass

    return _split_plain_text_into_articles(stripped)


def _extract_articles_from_json(data: Any) -> List[Dict[str, Any]]:
    articles: List[Dict[str, Any]] = []

    if isinstance(data, list):
        for item in data:
            articles.extend(_extract_articles_from_json(item))
        return articles

    if not isinstance(data, dict):
        return []

    # 조문 리스트가 있는 경우
    for key in ["articles", "조문", "article_list", "items", "data", "results"]:
        value = data.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    number = _pick_first(item, ["number", "article_number", "조문번호", "조문키"])
                    title = _pick_first(item, ["title", "article_title", "조문제목", "조제목"])
                    content = _pick_first(item, ["content", "article_content", "조문내용", "조내용", "text"])
                    if content:
                        articles.append({
                            "number": number,
                            "title": title,
                            "content": content,
                        })
            if articles:
                return articles

    # 단일 조문 형태
    content = _pick_first(data, ["content", "article_content", "text", "본문", "조문내용", "조내용"])
    title = _pick_first(data, ["title", "article_title", "조문제목", "조제목"])
    number = _pick_first(data, ["number", "article_number", "조문번호", "조문키"])

    if content:
        return [{
            "number": number,
            "title": title,
            "content": content,
        }]

    return []


def _split_plain_text_into_articles(text: str) -> List[Dict[str, Any]]:
    """
    일반 텍스트를 제n조 패턴 기준으로 분리
    """
    text = text.replace("\r\n", "\n")

    pattern = re.compile(
        r"(?=(제\s*\d+\s*조(?:의\s*\d+)?\s*(?:\([^)]*\))?))"
    )

    matches = list(pattern.finditer(text))

    if not matches:
        # 조문 패턴이 없으면 전체를 하나의 문서로 처리
        return [{
            "number": "",
            "title": "",
            "content": text[:10000],
        }]

    articles: List[Dict[str, Any]] = []

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)

        block = text[start:end].strip()

        if not block:
            continue

        first_line = block.split("\n", 1)[0].strip()

        number = ""
        title = ""

        m = re.match(r"(제\s*\d+\s*조(?:의\s*\d+)?)(?:\s*\(([^)]*)\))?", first_line)

        if m:
            number = re.sub(r"\s+", "", m.group(1))
            title = m.group(2) or ""

        articles.append({
            "number": number,
            "title": title,
            "content": block,
        })

    return articles


def _parse_articles_from_xml(xml_text: str) -> List[Dict[str, Any]]:
    articles: List[Dict[str, Any]] = []

    try:
        root = ET.fromstring(xml_text)

        for jo in root.iter("조문"):
            number = ""
            title = ""
            content_parts = []

            for child in jo.iter():
                tag = child.tag
                text = (child.text or "").strip()

                if not text:
                    continue

                if tag in ("조문번호", "조문여부"):
                    continue
                elif tag in ("조내용", "조문내용"):
                    content_parts.append(text)
                    match = re.match(r"(제\d+조(?:의\d+)?)", text)
                    if match:
                        number = match.group(1)
                elif tag in ("조제목", "조문제목"):
                    title = text
                elif tag in ("항내용", "호내용", "목내용"):
                    content_parts.append(text)

            if content_parts:
                articles.append({
                    "number": number,
                    "title": title,
                    "content": "\n".join(content_parts),
                })

        # 별표
        for bt in root.iter("별표단위"):
            bt_title = bt.findtext("별표제목", "")
            bt_content = (bt.findtext("별표내용", "") or "").strip()

            if bt_title:
                articles.append({
                    "number": bt_title,
                    "title": "",
                    "content": bt_content if bt_content else f"(첨부파일로 제공 - {bt_title})",
                })

    except ET.ParseError as e:
        print(f"[law-chatbot] XML 파싱 오류: {e}")

    return articles


def _select_relevant_articles(
    question: str,
    articles: List[Dict[str, Any]],
    article_keywords: List[str],
    law_name: str,
    target: str,
    source: str,
) -> List[Dict[str, Any]]:
    if not articles:
        return []

    question_terms = _extract_query_terms(question)
    keyword_terms = []

    for kw in article_keywords or []:
        keyword_terms.extend(_extract_query_terms(kw))
        if kw:
            keyword_terms.append(kw)

    all_terms = list(dict.fromkeys(question_terms + keyword_terms))

    scored: List[Dict[str, Any]] = []

    for article in articles:
        title = article.get("title", "") or ""
        number = article.get("number", "") or ""
        content = article.get("content", "") or ""

        haystack = f"{number} {title} {content}"

        score = 0

        for term in all_terms:
            if not term:
                continue

            if term in title:
                score += 8
            if term in number:
                score += 5
            if term in content:
                score += 3

        # 조문번호 직접 언급 보정
        article_no_terms = re.findall(r"제\s*\d+\s*조(?:의\s*\d+)?", question)
        for article_no in article_no_terms:
            normalized = re.sub(r"\s+", "", article_no)
            if normalized and normalized in haystack.replace(" ", ""):
                score += 20

        # 자주 나오는 실무 키워드 보정
        boosts = [
            ("연임", ["연임", "임기"]),
            ("임기", ["임기"]),
            ("위원", ["위원", "위원회"]),
            ("지원금", ["지원금", "지원대상", "지원기준"]),
            ("제3자", ["제3자", "제공"]),
            ("위탁", ["위탁", "위탁계약"]),
            ("기부행위", ["기부행위", "금품", "제공"]),
            ("경품", ["경품", "금품", "기부행위"]),
            ("과업심의", ["과업심의", "과업심의위원회"]),
        ]

        for qkey, terms in boosts:
            if qkey in question:
                for t in terms:
                    if t in haystack:
                        score += 6

        if score > 0:
            new_article = dict(article)
            new_article["score"] = score
            scored.append(new_article)

    scored.sort(key=lambda x: x.get("score", 0), reverse=True)

    # 관련 조문을 못 찾은 경우, 상위 몇 개라도 제공
    if not scored:
        fallback = []
        for article in articles[:3]:
            item = dict(article)
            item["score"] = 1
            fallback.append(item)
        return fallback

    return scored[:4]


# =========================================================
# 기존 law.go.kr 직접 API fallback
# =========================================================

async def _search_law_api_direct(
    query: str,
    targets: List[str],
    display: int = 10,
) -> List[Dict[str, Any]]:
    oc = settings.LAW_API_OC

    if not oc:
        return []

    all_results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for target in targets:
            try:
                params = {
                    "OC": oc,
                    "target": target,
                    "type": "XML",
                    "query": query if target != "ordin" else _normalize_ordin_query(query),
                    "display": display,
                    "page": 1,
                }

                resp = await client.get(LAW_SEARCH_URL, params=params)

                if resp.status_code != 200:
                    continue

                text = resp.content.decode("utf-8", errors="ignore")

                if text.strip().startswith("<!DOCTYPE") or text.strip().startswith("<html"):
                    continue

                items = _parse_search_xml(text, target)

                for item in items:
                    item.setdefault("source", "law.go.kr-direct-api")

                all_results.extend(items)

            except Exception as e:
                print(f"[law-chatbot] 직접 API 검색 실패: target={target}, query={query}, error={e}")

    return all_results


def _normalize_ordin_query(query: str) -> str:
    q = query.strip()
    if "충주시" not in q and "충주" not in q:
        q = f"충주시 {q}"
    return q


def _parse_search_xml(xml_text: str, target: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    try:
        root = ET.fromstring(xml_text)
        total = root.findtext("totalCnt", "0")

        for item in (
            list(root.findall("law"))
            + list(root.findall("ordin"))
            + list(root.findall("admrul"))
            + list(root.findall("expc"))
        ):
            r: Dict[str, Any] = {
                "type": target,
                "total_count": int(total or 0),
            }

            if target == "ordin":
                r["id"] = item.findtext("자치법규일련번호", item.findtext("법령일련번호", ""))
                r["name"] = item.findtext("자치법규명", item.findtext("법령명한글", ""))
                r["category"] = item.findtext("자치법규종류", item.findtext("자치법규구분", item.findtext("법령구분명", "")))
                r["region"] = item.findtext("지자체기관명", item.findtext("자치단체명", ""))
                r["enforcement_date"] = item.findtext("시행일자", "")

            elif target == "admrul":
                r["id"] = item.findtext("행정규칙일련번호", item.findtext("법령일련번호", ""))
                r["name"] = item.findtext("행정규칙명", item.findtext("법령명한글", ""))
                r["category"] = item.findtext("행정규칙종류", item.findtext("법령구분명", ""))
                r["ministry"] = item.findtext("소관부처명", "")
                r["enforcement_date"] = item.findtext("시행일자", "")

            else:
                r["id"] = item.findtext("법령일련번호", "")
                r["name"] = item.findtext("법령명한글", "")
                r["category"] = item.findtext("법령구분명", "")
                r["ministry"] = item.findtext("소관부처명", "")
                r["enforcement_date"] = item.findtext("시행일자", "")
                r["status"] = item.findtext("현행연혁코드", "")

            if r.get("name"):
                results.append(r)

    except ET.ParseError as e:
        print(f"[law-chatbot] XML 검색결과 파싱 오류: {e}")

    return results


# =========================================================
# 벡터스토어 fallback
# =========================================================

def _search_vectorstore(query: str, top_k: int = 7) -> List[Dict[str, Any]]:
    _load_vectorstore()
    _load_embedding_model()

    if _faiss_index is None or _faiss_data is None or _embedding_model is None:
        return []

    output = _embedding_model.encode(
        [query],
        batch_size=1,
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )

    query_vec = np.array(output["dense_vecs"]).astype("float32")
    norms = np.linalg.norm(query_vec, axis=1, keepdims=True)
    norms[norms == 0] = 1
    query_vec = query_vec / norms

    dense_k = top_k * 3
    scores, indices = _faiss_index.search(query_vec, dense_k)

    dense_results: Dict[int, Dict[str, Any]] = {}

    for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
        if idx < 0 or idx >= len(_faiss_data["texts"]):
            continue
        if score < VECTOR_SCORE_MIN:
            continue

        dense_results[int(idx)] = {
            "rank": rank,
            "score": float(score),
        }

    bm25_results: Dict[int, Dict[str, Any]] = {}

    if _bm25_index is not None:
        query_tokens = _tokenize_korean(query)

        if query_tokens:
            bm25_scores = _bm25_index.get_scores(query_tokens)
            bm25_top_indices = np.argsort(bm25_scores)[::-1][:dense_k]

            for rank, idx in enumerate(bm25_top_indices):
                if bm25_scores[idx] > 0:
                    bm25_results[int(idx)] = {
                        "rank": rank,
                        "score": float(bm25_scores[idx]),
                    }

    k = 60
    rrf_scores: Dict[int, float] = {}
    all_indices = set(dense_results.keys()) | set(bm25_results.keys())

    for idx in all_indices:
        rrf = 0.0

        if idx in dense_results:
            rrf += 1.0 / (k + dense_results[idx]["rank"] + 1)

        if idx in bm25_results:
            rrf += 1.0 / (k + bm25_results[idx]["rank"] + 1)

        rrf_scores[idx] = rrf

    sorted_indices = sorted(rrf_scores.items(), key=lambda x: -x[1])

    results: List[Dict[str, Any]] = []

    for idx, rrf_score in sorted_indices[:top_k]:
        display_score = dense_results[idx]["score"] if idx in dense_results else rrf_score

        results.append({
            "content": _faiss_data["texts"][idx],
            "metadata": _faiss_data["metadatas"][idx],
            "score": float(display_score),
            "rrf_score": float(rrf_score),
            "sources": {
                "dense": idx in dense_results,
                "bm25": idx in bm25_results,
            },
        })

    return _apply_dynamic_threshold(results)


def _tokenize_korean(text: str) -> List[str]:
    text = re.sub(r"[^\w가-힣]", " ", text)
    tokens = text.split()
    return [t.lower() for t in tokens if len(t) > 1]


def _apply_dynamic_threshold(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not results:
        return results

    max_score = results[0]["score"]
    threshold = max_score * VECTOR_SCORE_RELATIVE

    return [r for r in results if r["score"] >= threshold][:5]


# =========================================================
# 답변 생성
# =========================================================

async def _generate_answer(
    client,
    question: str,
    search_plan: Dict[str, Any],
    search_results: Dict[str, Any],
    chat_history: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    selected_articles = search_results.get("selected_articles", []) or []
    vector_results = search_results.get("vector_results", []) or []
    candidates = search_results.get("candidates", []) or []

    context_parts: List[str] = []

    context_parts.append("[질문]")
    context_parts.append(question)

    context_parts.append("\n[법률 쟁점 및 검색계획]")
    context_parts.append(json.dumps(search_plan, ensure_ascii=False, indent=2))

    if selected_articles:
        context_parts.append("\n[검색된 참고자료 - 관련 조문]")
        for i, article in enumerate(selected_articles, 1):
            law_name = article.get("law_name", "")
            number = article.get("number", "")
            title = article.get("title", "")
            content = article.get("content", "")
            target = article.get("target", "")
            source = article.get("source", "")

            context_parts.append(
                f"\n({i}) [{_target_label(target)}] {law_name} {number} {title}\n"
                f"출처: {source}\n"
                f"{content[:5000]}"
            )

    elif vector_results:
        context_parts.append("\n[검색된 참고자료 - 자치법규 벡터스토어]")
        for i, r in enumerate(vector_results, 1):
            meta = r.get("metadata", {})
            context_parts.append(
                f"\n({i}) {meta.get('law_name', '')} {meta.get('article', '')} "
                f"(유사도: {r.get('score', 0):.2f})\n"
                f"{r.get('content', '')[:4000]}"
            )

    elif candidates:
        context_parts.append("\n[검색된 참고자료 - 법령/자치법규 후보 목록]")
        for i, c in enumerate(candidates[:10], 1):
            context_parts.append(
                f"({i}) [{_target_label(c.get('type', ''))}/{c.get('category', '')}] "
                f"{c.get('name', '')} "
                f"(시행: {c.get('enforcement_date', '')}, 출처: {c.get('source', '')})"
            )

    else:
        context_parts.append("\n[검색된 참고자료]")
        context_parts.append("(검색 결과 없음)")

    context = "\n".join(context_parts)

    if len(context) > MAX_CONTEXT_CHARS:
        print(f"[law-chatbot] ⚠️ 컨텍스트 초과: {len(context)}자 → {MAX_CONTEXT_CHARS}자로 절삭")
        context = context[:MAX_CONTEXT_CHARS] + "\n\n... (이하 생략)"

    template = prompt_service.get(
        "law_chatbot",
        "answer_system_prompt",
        default=_DEFAULT_ANSWER_SYSTEM,
    )

    system_prompt = template.format(context=context)

    print(f"[law-chatbot] GPT 컨텍스트: {len(context)}자")

    messages = [{"role": "system", "content": system_prompt}]

    if chat_history:
        for msg in chat_history[-8:]:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role in ("user", "assistant") and content:
                messages.append({
                    "role": role,
                    "content": content,
                })

    messages.append({
        "role": "user",
        "content": question,
    })

    try:
        response = await client.chat.completions.create(
            model=ANSWER_MODEL,
            messages=messages,
            temperature=0.2,
        )

        answer_text = response.choices[0].message.content

    except Exception as e:
        print(f"[law-chatbot] GPT 답변 생성 실패: {e}")
        answer_text = "죄송합니다. 답변 생성 중 오류가 발생했습니다."

    references = _build_references(
        selected_articles=selected_articles,
        vector_results=vector_results,
        candidates=candidates,
    )

    return {
        "answer": answer_text,
        "references": references,
        "search_info": {
            "planner_source": search_plan.get("source", ""),
            "candidate_count": len(candidates),
            "article_count": len(selected_articles),
            "vector_count": len(vector_results),
            "api_count": len(candidates),
            "detail_count": search_results.get("detail_count", 0),
        },
    }


def _build_references(
    selected_articles: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []

    for article in selected_articles:
        name = article.get("law_name", "")
        target = article.get("target", "")

        if not name:
            continue

        ref = {
            "name": name,
            "type": _target_label(target),
            "article": f"{article.get('number', '')} {article.get('title', '')}".strip(),
            "enforcement_date": article.get("enforcement_date", ""),
            "source": article.get("source", ""),
        }

        ref["url"] = _make_law_url(name, target)

        refs.append(ref)

    for r in vector_results[:3]:
        meta = r.get("metadata", {})
        name = meta.get("law_name", "")

        if not name:
            continue

        refs.append({
            "name": name,
            "type": "충주시 자치법규",
            "article": meta.get("article", ""),
            "source": "vectorstore",
        })

    if not refs:
        for c in candidates[:5]:
            name = c.get("name", "")
            target = c.get("type", "")

            if not name:
                continue

            refs.append({
                "name": name,
                "type": _target_label(target),
                "enforcement_date": c.get("enforcement_date", ""),
                "source": c.get("source", ""),
                "url": _make_law_url(name, target),
            })

    seen = set()
    unique_refs = []

    for ref in refs:
        key = f"{ref.get('name', '')}::{ref.get('article', '')}::{ref.get('type', '')}"

        if key not in seen:
            seen.add(key)
            unique_refs.append(ref)

    return unique_refs[:8]


# =========================================================
# 유틸
# =========================================================

def _target_label(target: str) -> str:
    return {
        "law": "국가법령",
        "ordin": "자치법규",
        "admrul": "행정규칙",
    }.get(target, "법령")


def _make_law_url(name: str, target: str) -> str:
    if not name:
        return ""

    if target == "ordin":
        return f"https://www.law.go.kr/자치법규/{name}"
    if target == "admrul":
        return f"https://www.law.go.kr/행정규칙/{name}"
    return f"https://www.law.go.kr/법령/{name}"


def _pick_first(item: Dict[str, Any], keys: List[str], default: str = "") -> str:
    for key in keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _extract_query_terms(text: str) -> List[str]:
    if not text:
        return []

    stopwords = {
        "알려줘", "알려주세요", "어떻게", "무엇", "뭐야", "대해",
        "따르면", "가능해", "가능한가", "몇번까지", "몇", "번",
        "기준", "구성", "경우", "관련", "내용", "있는지",
        "은", "는", "이", "가", "을", "를", "에", "의", "로", "으로",
        "그리고", "또는", "혹은", "무슨",
    }

    cleaned = re.sub(r"[^\w가-힣]", " ", text)
    words = [w.strip() for w in cleaned.split() if len(w.strip()) >= 2]

    return [w for w in words if w not in stopwords]


def _looks_like_local_question(question: str) -> bool:
    return any(x in question for x in ["충주시", "충주", "조례", "자치법규", "시행규칙"])


def _deduplicate_candidates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []

    for r in results:
        name = r.get("name", "")
        target = r.get("type", "")
        item_id = r.get("id", "")

        key = item_id or f"{target}::{name}"

        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


def _rank_candidates(question: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not results:
        return results

    terms = _extract_query_terms(question)

    def score_item(item: Dict[str, Any]) -> int:
        name = item.get("name", "") or ""
        category = item.get("category", "") or ""
        region = item.get("region", "") or ""
        target = item.get("type", "") or ""
        source = item.get("source", "") or ""

        haystack = f"{name} {category} {region} {target} {source}"

        score = 0

        for term in terms:
            if term in name:
                score += 8
            elif term in haystack:
                score += 3

        if "충주" in question and ("충주" in name or "충주" in region):
            score += 15

        if "조례" in question and "조례" in name:
            score += 10

        if "위원회" in question and "위원회" in name:
            score += 10

        if "소프트웨어" in question and "소프트웨어" in name:
            score += 10

        if "개인정보" in question and "개인정보" in name:
            score += 10

        if ("충주" in question or "조례" in question) and target == "ordin":
            score += 8

        return score

    return sorted(results, key=score_item, reverse=True)


def _deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []

    for a in articles:
        key = (
            a.get("law_name", ""),
            a.get("number", ""),
            a.get("title", ""),
            a.get("content", "")[:80],
        )

        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique


async def _check_api_connection() -> Dict[str, Any]:
    result = {
        "mcp": {
            "enabled": False,
            "connected": False,
        },
        "law_api": {
            "connected": False,
        },
        "connected": False,
    }

    try:
        mcp_status = await korean_law_mcp_service.check_connection()
        result["mcp"] = mcp_status
    except Exception as e:
        result["mcp"] = {
            "enabled": True,
            "connected": False,
            "reason": str(e),
        }

    oc = settings.LAW_API_OC

    if not oc:
        result["law_api"] = {
            "connected": False,
            "reason": "LAW_API_OC 미설정",
        }
    else:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    LAW_SEARCH_URL,
                    params={
                        "OC": oc,
                        "target": "law",
                        "type": "XML",
                        "query": "헌법",
                        "display": 1,
                    },
                )

                text = resp.content.decode("utf-8", errors="ignore")
                is_xml = not text.strip().startswith("<!DOCTYPE")

                result["law_api"] = {
                    "connected": is_xml,
                    "status_code": resp.status_code,
                }

        except Exception as e:
            result["law_api"] = {
                "connected": False,
                "reason": str(e),
            }

    result["connected"] = bool(
        result.get("mcp", {}).get("connected")
        or result.get("law_api", {}).get("connected")
    )

    return result