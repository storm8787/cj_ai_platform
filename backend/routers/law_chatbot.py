"""
법령정보 · 자치법규 챗봇 라우터

변경 방향:
1. 프론트의 국가법령/자치법규 선택 구조를 사실상 폐지
2. 모든 질문은 MCP 기반 통합검색 우선
3. MCP 검색은 경량 병렬검색 방식 적용
   - 국가법령
   - 자치법규
   - 행정규칙
4. MCP 실패 시 기존 law.go.kr API fallback
5. 자치법규 벡터스토어는 충주/조례/자치법규성 질문이면서,
   MCP/API 자치법규 결과가 없을 때만 보조검색
6. 본문 조회는 timeout을 적용하여 답변 생성을 막지 않도록 처리
7. 기존 응답 형식(answer, references, search_info)은 유지
"""

import os
import json
import pickle
import re
import asyncio
from pathlib import Path
from typing import Optional, List

import faiss
import numpy as np
import httpx
import xml.etree.ElementTree as ET
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from FlagEmbedding import BGEM3FlagModel

from config import settings
from services.prompt_service import prompt_service
from services.korean_law_mcp_service import korean_law_mcp_service

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
KEYWORD_MODEL = "gpt-4o"
UTILITY_MODEL = "gpt-4o-mini"

VECTORSTORE_DIR = Path(settings.LAW_CHATBOT_VECTORSTORE_PATH)
EMBEDDING_MODEL_NAME = settings.EMBEDDING_MODEL

VECTOR_SCORE_MIN = 0.30
VECTOR_SCORE_RELATIVE = 0.85

MAX_RETRY = 2

_faiss_index = None
_faiss_data = None
_embedding_model = None
_bm25_index = None
_bm25_corpus = None


_DEFAULT_EXTRACT_KEYWORDS = """당신은 법령 검색 전문가입니다. 사용자의 질문에서 국가법령정보센터 API 검색에 적합한 키워드를 추출하세요.

[규칙]
1. 법령명이나 핵심 법률 용어를 2~3개 추출
2. 실무 상황이면 관련 법령명을 추론
3. 가능하면 정확한 법령명을 포함
4. 반드시 JSON 배열로만 응답. 다른 텍스트 없이.

[예시]
"관외출장 갔는데 초과근무 되나?" → ["지방공무원 복무규정", "초과근무"]
"정근수당 받을 수 있나?" → ["공무원보수규정", "정근수당"]
"육아휴직 복직 후 수당" → ["공무원보수규정", "육아휴직"]
"연차 안 쓰면 수당 나오나?" → ["공무원보수규정", "연가보상비"]
"10년차 공무원 연가일수" → ["지방공무원 복무규정", "국가공무원 복무규정"]
"소프트웨어사업 과업심의" → ["소프트웨어진흥법", "소프트웨어사업"]
"건축 허가 기준" → ["건축법"]
"개인정보 제3자 제공" → ["개인정보보호법", "제3자 제공"]
"충주시 출산 지원 조례" → ["충주시 출산 지원 조례", "출산 지원금"]"""

_DEFAULT_ALTERNATIVE_KEYWORDS = """사용자의 법령 관련 질문에 대해 국가법령정보센터 API 검색용 키워드를 생성하세요.
이전에 시도한 키워드로는 검색 결과가 없었습니다.
다른 법령명이나 다른 표현의 키워드를 2~3개 제안하세요.
반드시 JSON 배열로만 응답하세요.

전략:
- 상위법/시행령/시행규칙 등 관련 법령명을 시도
- 더 넓은 범위의 법령명을 시도
- 동의어나 유사 표현을 시도"""

_DEFAULT_ANSWER_SYSTEM = """당신은 충주시청 공무원을 위한 법령·자치법규 전문 AI 어시스턴트입니다.

[역할]
공무원이 실무에서 바로 활용할 수 있도록 정확하고 구체적인 법령 정보를 제공합니다.

[답변 전략]

1단계: [검색된 참고자료]에 답이 있는 경우
→ 반드시 조문 번호를 정확히 인용하며 구체적으로 답변하세요.
→ 법령명은 정식 명칭 그대로 사용하세요.
→ 수치(일수, 금액, 기간 등)가 있으면 반드시 구체적으로 제시하세요.

2단계: 검색 결과에 충분한 답이 없지만, 일반 법률 지식으로 답할 수 있는 경우
→ 답변하되, 답변 끝에 다음 문구를 표시하세요.
💡 이 내용은 AI의 일반 법률 지식을 기반으로 한 답변입니다. 정확한 조문 확인은 국가법령정보센터(law.go.kr)에서 확인하시기 바랍니다.

3단계: 둘 다 모르는 경우
→ "해당 내용에 대한 정확한 정보를 찾지 못했습니다. 법제팀 또는 국가법령정보센터에서 확인하시기 바랍니다."

[답변 형식]
1. 결론을 먼저 한 문장으로 제시
2. 근거 조문 인용
3. 실무 적용 시 유의사항이 있으면 ⚠️로 안내
4. 답변 마지막에 📋 참고 법령 목록

[절대 금지 규칙]
- 검색 결과에 있더라도 질문 대상과 다른 법령은 절대 인용하지 마세요.
- 법령명을 임의로 변경하거나 축약하지 마세요.
- 확인할 수 없는 조문 번호를 만들어내지 마세요.
- 표(별표)의 수치를 해석할 때 구간을 정확히 매칭하세요.

[검색된 참고자료]
{context}"""


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

    _faiss_index = faiss.read_index(str(faiss_path))

    with open(pkl_path, "rb") as f:
        _faiss_data = pickle.load(f)

    print(f"[law-chatbot] ✅ 벡터스토어 로드 완료: {_faiss_index.ntotal}개 문서")

    if _BM25_AVAILABLE and bm25_path.exists():
        try:
            with open(bm25_path, "rb") as f:
                bm25_data = pickle.load(f)

            _bm25_corpus = bm25_data.get("tokenized_corpus", [])

            if _bm25_corpus:
                _bm25_index = BM25Okapi(_bm25_corpus)
                print(f"[law-chatbot] ✅ BM25 인덱스 로드 완료: {len(_bm25_corpus)}개 문서")
            else:
                print("[law-chatbot] ⚠️ BM25 코퍼스가 비어있음")

        except Exception as e:
            print(f"[law-chatbot] ⚠️ BM25 로드 실패: {e}")


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


class AskRequest(BaseModel):
    question: str
    search_scope: str = "all"
    chat_history: Optional[List[dict]] = None


class SearchRequest(BaseModel):
    query: str
    target: str = "law"
    page: int = 1
    display: int = 20


@router.post("/ask")
async def ask_question(req: AskRequest):
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    search_keywords = await _extract_search_keywords(client, req.question)
    print(f"[law-chatbot] 키워드: {search_keywords}")

    vector_results, api_results = await _agentic_search(
        client=client,
        question=req.question,
        initial_keywords=search_keywords,
        search_scope=req.search_scope,
    )

    detail_texts = []

    # 본문 조회는 전체 답변을 막지 않도록 timeout 적용
    for r in api_results[:3]:
        mst = r.get("id", "")
        target = r.get("type", "law")

        if target not in ("law", "ordin", "admrul"):
            target = "law"

        if not mst:
            continue

        try:
            relevant = await asyncio.wait_for(
                _fetch_relevant_articles(
                    mst=mst,
                    target=target,
                    question=req.question,
                    keywords=search_keywords,
                    name=r.get("name", ""),
                    source=r.get("source", ""),
                ),
                timeout=10.0,
            )

            if relevant:
                detail_texts.append({
                    "name": r.get("name", ""),
                    "content": relevant,
                })

        except asyncio.TimeoutError:
            print(
                f"[law-chatbot] ⚠️ 본문 조회 timeout, 검색결과만으로 답변 진행: "
                f"name={r.get('name', '')}, target={target}"
            )

        except Exception as e:
            print(
                f"[law-chatbot] ⚠️ 본문 조회 실패, 검색결과만으로 답변 진행: "
                f"name={r.get('name', '')}, target={target}, error={e}"
            )

    print(
        f"[law-chatbot] 최종 결과: "
        f"vector={len(vector_results)}, api={len(api_results)}, detail={len(detail_texts)}"
    )

    answer = await _generate_answer(
        client=client,
        question=req.question,
        vector_results=vector_results,
        api_results=api_results,
        detail_texts=detail_texts,
        chat_history=req.chat_history,
    )

    return answer


@router.post("/search")
async def search_law(req: SearchRequest):
    results = await _call_law_search_api(
        target=req.target,
        query=req.query,
        page=req.page,
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


async def _safe_search_task(label: str, coro, timeout: float = 8.0) -> dict:
    """
    병렬검색용 안전 실행 래퍼.
    """
    try:
        print(f"[law-chatbot] {label} 시작")

        items = await asyncio.wait_for(coro, timeout=timeout)

        if not items:
            print(f"[law-chatbot] {label} 종료: count=0")
            return {"label": label, "items": []}

        print(f"[law-chatbot] {label} 종료: count={len(items)}")
        return {"label": label, "items": items}

    except asyncio.TimeoutError:
        print(f"[law-chatbot] ⚠️ {label} timeout")
        return {"label": label, "items": []}

    except Exception as e:
        print(f"[law-chatbot] ⚠️ {label} 실패: {e}")
        return {"label": label, "items": []}


async def _agentic_search(
    client, question: str, initial_keywords: list, search_scope: str,
) -> tuple:
    """
    경량 병렬검색 기반 통합검색 버전.

    핵심 정책:
    1. 사전기반으로 국가/자치법규를 단정하지 않음
    2. MCP는 대표 검색어 1개만 사용해 3종 병렬검색
       - 국가법령
       - 자치법규
       - 행정규칙
    3. MCP가 실패하면 기존 law.go.kr API fallback
    4. 자치법규 벡터스토어는 다음 경우에만 실행
       - 충주/조례/자치법규성 질문이고
       - MCP/API 자치법규 결과가 없을 때
    """

    all_api_results = []
    all_vector_results = []

    # 1. 검색어 구성
    search_terms = []

    for kw in initial_keywords or []:
        if isinstance(kw, str) and kw.strip():
            search_terms.append(kw.strip())

    if question and question.strip():
        search_terms.append(question.strip())

    deduped_terms = []
    seen_terms = set()

    for term in search_terms:
        if term not in seen_terms:
            seen_terms.add(term)
            deduped_terms.append(term)

    search_terms = deduped_terms[:3]

    if not search_terms:
        search_terms = [_simple_keyword_extract(question)]

    primary_term = search_terms[0]

    print(f"[law-chatbot] 경량 통합검색 시작: primary={primary_term}, terms={search_terms}")

    # 2. MCP 3종 병렬검색
    mcp_tasks = [
        _safe_search_task(
            label=f"MCP 국가법령 검색: {primary_term}",
            coro=korean_law_mcp_service.search_law(
                query=primary_term,
                target="law",
                display=8,
            ),
            timeout=8.0,
        ),
        _safe_search_task(
            label=f"MCP 자치법규 검색: {primary_term}",
            coro=korean_law_mcp_service.search_ordinance(
                query=primary_term,
                display=8,
            ),
            timeout=8.0,
        ),
        _safe_search_task(
            label=f"MCP 행정규칙 검색: {primary_term}",
            coro=korean_law_mcp_service.search_admin_rule(
                query=primary_term,
                display=8,
            ),
            timeout=8.0,
        ),
    ]

    task_results = await asyncio.gather(*mcp_tasks, return_exceptions=True)

    for result in task_results:
        if isinstance(result, Exception):
            print(f"[law-chatbot] MCP task 예외 무시: {result}")
            continue

        if not result:
            continue

        items = result.get("items", [])
        if items:
            all_api_results.extend(items)

    all_api_results = _deduplicate_api_results(all_api_results)

    print(f"[law-chatbot] MCP 경량검색 결과: api={len(all_api_results)}")

    # 3. MCP 결과가 없으면 기존 law.go.kr API fallback
    if not all_api_results:
        print("[law-chatbot] MCP 결과 없음, 기존 law.go.kr API fallback 시작")

        for kw in search_terms[:2]:
            if not kw:
                continue

            try:
                print(f"[law-chatbot] 기존 국가법령 API 직접검색 시작: keyword={kw}")
                law_results = await _search_law_api_direct(
                    query=kw,
                    targets=["law"],
                )
                print(
                    f"[law-chatbot] 기존 국가법령 API 직접검색 종료: "
                    f"keyword={kw}, count={len(law_results)}"
                )
                all_api_results.extend(law_results)

            except Exception as e:
                print(f"[law-chatbot] 기존 국가법령 API 직접검색 예외: {e}")

            try:
                print(f"[law-chatbot] 기존 자치법규 API 직접검색 시작: keyword={kw}")
                ordin_results = await _search_law_api_direct(
                    query=kw,
                    targets=["ordin"],
                )
                print(
                    f"[law-chatbot] 기존 자치법규 API 직접검색 종료: "
                    f"keyword={kw}, count={len(ordin_results)}"
                )
                all_api_results.extend(ordin_results)

            except Exception as e:
                print(f"[law-chatbot] 기존 자치법규 API 직접검색 예외: {e}")

            all_api_results = _deduplicate_api_results(all_api_results)

            if all_api_results:
                print(f"[law-chatbot] 기존 API fallback 성공: count={len(all_api_results)}")
                break

    # 4. 자치법규 벡터스토어 보조검색 여부 판단
    vector_hint_words = [
        "충주시",
        "충주",
        "조례",
        "자치법규",
        "시행규칙",
    ]

    should_search_vector_by_question = any(word in question for word in vector_hint_words)

    has_ordinance_result = any(
        r.get("type") == "ordin" or "자치법규" in str(r.get("type", ""))
        for r in all_api_results
    )

    # 핵심:
    # MCP/API에서 자치법규 결과가 이미 있으면 벡터스토어를 돌리지 않음
    should_search_vector = should_search_vector_by_question and not has_ordinance_result

    if should_search_vector:
        print(
            "[law-chatbot] 자치법규 벡터스토어 보조검색 시작 "
            f"(reason=local_question_without_ordinance_result)"
        )

        try:
            vector_results = await asyncio.wait_for(
                asyncio.to_thread(_search_vectorstore, question, 7),
                timeout=20.0,
            )
            all_vector_results = (vector_results or [])[:5]
            print(f"[law-chatbot] 자치법규 벡터스토어 보조검색 종료: count={len(all_vector_results)}")

        except asyncio.TimeoutError:
            print("[law-chatbot] 자치법규 벡터스토어 보조검색 timeout")
            all_vector_results = []

        except Exception as e:
            print(f"[law-chatbot] 자치법규 벡터스토어 보조검색 실패: {e}")
            all_vector_results = []

    else:
        if should_search_vector_by_question and has_ordinance_result:
            print("[law-chatbot] 자치법규 MCP/API 결과 존재 → 벡터스토어 보조검색 생략")
        else:
            print("[law-chatbot] 자치법규 벡터스토어 보조검색 생략")

    all_api_results = _deduplicate_api_results(all_api_results)

    print(
        f"[law-chatbot] 경량 통합검색 최종결과: "
        f"api={len(all_api_results)}, vector={len(all_vector_results)}"
    )

    return all_vector_results, all_api_results


async def _generate_alternative_keywords(
    client, question: str, tried_keywords: list
) -> list:
    system_content = prompt_service.get(
        "law_chatbot",
        "alternative_keywords",
        default=_DEFAULT_ALTERNATIVE_KEYWORDS,
    )

    try:
        response = await client.chat.completions.create(
            model=UTILITY_MODEL,
            messages=[
                {"role": "system", "content": system_content},
                {
                    "role": "user",
                    "content": (
                        f"질문: {question}\n"
                        f"이미 시도한 키워드 (결과 없음): {tried_keywords}\n"
                        f"다른 키워드를 제안해주세요."
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=100,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        keywords = json.loads(raw)

        if isinstance(keywords, list) and len(keywords) > 0:
            return keywords[:3]

    except Exception as e:
        print(f"[law-chatbot] 대안 키워드 생성 실패: {e}")

    return []


async def _extract_search_keywords(client, question: str) -> list:
    system_content = prompt_service.get(
        "law_chatbot",
        "extract_keywords",
        default=_DEFAULT_EXTRACT_KEYWORDS,
    )

    try:
        response = await client.chat.completions.create(
            model=KEYWORD_MODEL,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": question},
            ],
            temperature=0.1,
            max_tokens=100,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        keywords = json.loads(raw)

        if isinstance(keywords, list) and len(keywords) > 0:
            return keywords[:3]

    except Exception as e:
        print(f"[law-chatbot] 키워드 추출 실패: {e}")

    return [_simple_keyword_extract(question)]


def _simple_keyword_extract(question: str) -> str:
    stopwords = {
        "알려줘", "알려주세요", "뭐야", "어떻게", "무엇", "어떤",
        "규정은", "내용은", "관련", "대해", "있나요", "있어",
        "인가요", "해줘", "해주세요", "어떻게돼", "몇일이야",
        "기준이", "기준", "구성은", "좀", "그", "이", "저",
        "것", "수", "등", "및", "의", "에", "은", "는",
        "가", "를", "을", "에서", "으로", "로",
    }

    words = question.strip().split()
    keywords = [w for w in words if w not in stopwords and len(w) > 1]

    return " ".join(keywords) if keywords else question


def _search_vectorstore(query: str, top_k: int = 7) -> list:
    """Hybrid Search: dense(FAISS) + BM25 결과를 RRF로 합산"""
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

    dense_results = {}

    for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
        if idx < 0 or idx >= len(_faiss_data["texts"]):
            continue
        if score < VECTOR_SCORE_MIN:
            continue

        dense_results[int(idx)] = {
            "rank": rank,
            "score": float(score),
        }

    bm25_results = {}

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
    rrf_scores = {}
    all_indices = set(dense_results.keys()) | set(bm25_results.keys())

    for idx in all_indices:
        rrf = 0.0
        if idx in dense_results:
            rrf += 1.0 / (k + dense_results[idx]["rank"] + 1)
        if idx in bm25_results:
            rrf += 1.0 / (k + bm25_results[idx]["rank"] + 1)
        rrf_scores[idx] = rrf

    sorted_indices = sorted(rrf_scores.items(), key=lambda x: -x[1])

    results = []

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

    if results:
        dense_only = sum(
            1 for r in results if r["sources"]["dense"] and not r["sources"]["bm25"]
        )
        bm25_only = sum(
            1 for r in results if r["sources"]["bm25"] and not r["sources"]["dense"]
        )
        both = sum(
            1 for r in results if r["sources"]["dense"] and r["sources"]["bm25"]
        )

        print(f"[law-chatbot] Hybrid 검색: dense만={dense_only}, bm25만={bm25_only}, 둘다={both}")

    return results


def _tokenize_korean(text: str) -> list:
    text = re.sub(r"[^\w가-힣]", " ", text)
    tokens = text.split()
    return [t.lower() for t in tokens if len(t) > 1]


def _apply_dynamic_threshold(results: list) -> list:
    if not results:
        return results

    max_score = results[0]["score"]
    threshold = max_score * VECTOR_SCORE_RELATIVE

    filtered = [r for r in results if r["score"] >= threshold]

    return filtered[:5]


async def _search_law_api(query: str, targets: list) -> list:
    """
    기존 law.go.kr 직접 API fallback.
    국가법령은 MCP 우선 검색 후 실패 시 fallback.
    자치법규는 기존 API 방식 유지.
    """
    oc = settings.LAW_API_OC
    all_results = []

    for target in targets:
        if target == "law":
            try:
                mcp_results = await korean_law_mcp_service.search_law(
                    query=query,
                    target=target,
                    display=10,
                )

                if mcp_results:
                    print(f"[law-chatbot] MCP 검색 성공: query={query}, count={len(mcp_results)}")
                    all_results.extend(mcp_results)
                    continue

            except Exception as e:
                print(f"[law-chatbot] MCP 검색 예외, 기존 API fallback 진행: {e}")

        if target == "ordin":
            try:
                mcp_results = await korean_law_mcp_service.search_ordinance(
                    query=query,
                    display=10,
                )

                if mcp_results:
                    print(f"[law-chatbot] MCP 자치법규 검색 성공: query={query}, count={len(mcp_results)}")
                    all_results.extend(mcp_results)
                    continue

            except Exception as e:
                print(f"[law-chatbot] MCP 자치법규 검색 예외, 기존 API fallback 진행: {e}")

        if not oc:
            continue

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                params = {
                    "OC": oc,
                    "target": target,
                    "type": "XML",
                    "query": query if target != "ordin" else f"충주시 {query}",
                    "display": 10,
                    "page": 1,
                }

                resp = await client.get(LAW_SEARCH_URL, params=params)

                if resp.status_code != 200:
                    continue

                text = resp.content.decode("utf-8")

                if text.strip().startswith("<!DOCTYPE") or text.strip().startswith("<html"):
                    continue

                items = _parse_search_xml(text, target)

                for item in items:
                    item.setdefault("source", "law.go.kr-api")

                all_results.extend(items)

            except Exception as e:
                print(f"[law-chatbot] API 검색 실패 (target={target}): {e}")

    return all_results


async def _search_law_api_direct(query: str, targets: list) -> list:
    """
    기존 law.go.kr 직접 API 검색 전용 함수.

    용도:
    - MCP가 실패했을 때 fallback으로만 사용
    - MCP를 다시 호출하지 않음
    """
    oc = settings.LAW_API_OC

    if not oc:
        return []

    all_results = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for target in targets:
            try:
                params = {
                    "OC": oc,
                    "target": target,
                    "type": "XML",
                    "query": query if target != "ordin" else f"충주시 {query}",
                    "display": 10,
                    "page": 1,
                }

                resp = await client.get(LAW_SEARCH_URL, params=params)

                if resp.status_code != 200:
                    print(
                        f"[law-chatbot] 직접 API 응답 오류: "
                        f"target={target}, status={resp.status_code}"
                    )
                    continue

                text = resp.content.decode("utf-8")

                if text.strip().startswith("<!DOCTYPE") or text.strip().startswith("<html"):
                    print(
                        f"[law-chatbot] 직접 API HTML/인증 응답 감지: "
                        f"target={target}, query={query}"
                    )
                    continue

                items = _parse_search_xml(text, target)

                for item in items:
                    item.setdefault("source", "law.go.kr-direct-api")

                all_results.extend(items)

            except Exception as e:
                print(
                    f"[law-chatbot] 직접 API 검색 실패: "
                    f"target={target}, query={query}, error={e}"
                )

    return all_results


async def _call_law_search_api(target: str, query: str, page: int, display: int) -> list:
    """
    /api/law-chatbot/search에서 사용하는 직접 검색 API.
    """
    if target == "law":
        try:
            mcp_results = await korean_law_mcp_service.search_law(
                query=query,
                target=target,
                display=display,
            )
            if mcp_results:
                return mcp_results
        except Exception as e:
            print(f"[law-chatbot] /search MCP 실패, 기존 API fallback 진행: {e}")

    if target == "ordin":
        try:
            mcp_results = await korean_law_mcp_service.search_ordinance(
                query=query,
                display=display,
            )
            if mcp_results:
                return mcp_results
        except Exception as e:
            print(f"[law-chatbot] /search MCP 자치법규 실패, 기존 API fallback 진행: {e}")

    oc = settings.LAW_API_OC

    if not oc:
        raise HTTPException(status_code=500, detail="LAW_API_OC 환경변수 미설정")

    async with httpx.AsyncClient(timeout=15.0) as client:
        params = {
            "OC": oc,
            "target": target,
            "type": "XML",
            "query": query,
            "display": display,
            "page": page,
        }

        resp = await client.get(LAW_SEARCH_URL, params=params)
        text = resp.content.decode("utf-8")

        if text.strip().startswith("<!DOCTYPE"):
            raise HTTPException(status_code=502, detail="법령 API 인증 실패")

        results = _parse_search_xml(text, target)

        for item in results:
            item.setdefault("source", "law.go.kr-api")

        return results


async def _fetch_relevant_articles(
    mst: str,
    target: str,
    question: str,
    keywords: list,
    name: str = "",
    source: str = "",
) -> str:
    """
    법령 본문/관련 조문 조회.

    1순위:
    - 국가법령: MCP get_law_text
    - 자치법규: MCP get_ordinance
    - 행정규칙: MCP get_admin_rule

    2순위:
    - 기존 law.go.kr lawService.do 직접 API fallback
    """
    if target == "law":
        try:
            mcp_text = await korean_law_mcp_service.get_law_text(
                mst=mst,
                law_name=name,
                question=question,
            )

            if mcp_text and len(mcp_text.strip()) > 20:
                print(f"[law-chatbot] MCP 국가법령 본문 조회 성공: MST={mst}, chars={len(mcp_text)}")
                return mcp_text[:8000]

        except Exception as e:
            print(f"[law-chatbot] MCP 국가법령 본문 조회 실패, 기존 API fallback 진행: {e}")

    if target == "ordin":
        try:
            mcp_text = await korean_law_mcp_service.get_ordinance_text(
                ordin_seq=mst,
                ordinance_name=name,
            )

            if mcp_text and len(mcp_text.strip()) > 20:
                print(f"[law-chatbot] MCP 자치법규 본문 조회 성공: id={mst}, chars={len(mcp_text)}")
                return mcp_text[:8000]

        except Exception as e:
            print(f"[law-chatbot] MCP 자치법규 본문 조회 실패, 기존 API fallback 진행: {e}")

    if target == "admrul":
        try:
            mcp_text = await korean_law_mcp_service.get_admin_rule_text(
                admin_rule_id=mst,
                admin_rule_name=name,
            )

            if mcp_text and len(mcp_text.strip()) > 20:
                print(f"[law-chatbot] MCP 행정규칙 본문 조회 성공: id={mst}, chars={len(mcp_text)}")
                return mcp_text[:8000]

        except Exception as e:
            print(f"[law-chatbot] MCP 행정규칙 본문 조회 실패, 기존 API fallback 진행: {e}")

    oc = settings.LAW_API_OC

    if not oc:
        return ""

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.get(
                LAW_SERVICE_URL,
                params={
                    "OC": oc,
                    "target": target,
                    "MST": mst,
                    "type": "XML",
                },
            )

            text = resp.content.decode("utf-8")

            if text.strip().startswith("<!DOCTYPE"):
                return ""

        except Exception as e:
            print(f"[law-chatbot] 본문 조회 실패 (MST={mst}): {e}")
            return ""

    articles = _parse_articles_from_xml(text)

    if not articles:
        return ""

    search_terms = set()

    for word in question.split():
        if len(word) >= 2:
            search_terms.add(word)

    for kw in keywords:
        for word in kw.split():
            if len(word) >= 2:
                search_terms.add(word)

    stopwords = {
        "어떻게", "어떤", "무엇", "알려줘", "알려주세요", "규정은",
        "기준이", "기준은", "몇일이야", "있나요", "인가요", "해줘",
        "어떻게돼", "뭐야", "구성은", "해야해", "받을수", "있을까",
        "경우", "했을경우", "복직했을경우", "대상사업은",
    }

    search_terms -= stopwords

    scored_articles = []

    for article in articles:
        title = article.get("title", "")
        content = article.get("content", "")
        full_text = f"{title} {content}"

        score = 0

        for term in search_terms:
            if term in full_text:
                score += 1
                if term in title:
                    score += 2

        if score > 0:
            scored_articles.append((score, article))

    scored_articles.sort(key=lambda x: -x[0])

    selected = []
    total_chars = 0

    for score, article in scored_articles[:10]:
        article_text = (
            f"[{article.get('number', '')} {article.get('title', '')}]\n"
            f"{article.get('content', '')}"
        )

        if total_chars + len(article_text) > 8000:
            break

        selected.append(article_text)
        total_chars += len(article_text)

    if not selected and articles:
        for article in articles[:5]:
            article_text = (
                f"[{article.get('number', '')} {article.get('title', '')}]\n"
                f"{article.get('content', '')}"
            )

            selected.append(article_text)
            total_chars += len(article_text)

            if total_chars > 5000:
                break

    return "\n\n".join(selected)


def _parse_articles_from_xml(xml_text: str) -> list:
    articles = []

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

        if not articles:
            for elem in root.iter():
                tag = elem.tag
                text = (elem.text or "").strip()

                if not text:
                    continue

                if any(k in tag for k in ["조문내용", "조내용"]):
                    match = re.match(r"(제\d+조(?:의\d+)?)", text)
                    number = match.group(1) if match else ""
                    articles.append({
                        "number": number,
                        "title": "",
                        "content": text,
                    })

        for bt in root.iter("별표단위"):
            bt_title = bt.findtext("별표제목", "")
            bt_content = bt.findtext("별표내용", "").strip()

            if bt_title:
                articles.append({
                    "number": bt_title,
                    "title": "",
                    "content": bt_content if bt_content else f"(첨부파일로 제공 - {bt_title})",
                })

    except ET.ParseError as e:
        print(f"[law-chatbot] XML 파싱 오류: {e}")

    return articles


def _parse_search_xml(xml_text: str, target: str) -> list:
    results = []

    try:
        root = ET.fromstring(xml_text)
        total = root.findtext("totalCnt", "0")

        for item in (
            list(root.findall("law"))
            + list(root.findall("ordin"))
            + list(root.findall("admrul"))
            + list(root.findall("expc"))
        ):
            r = {
                "type": target,
                "total_count": int(total),
            }

            if target == "ordin":
                r["id"] = item.findtext("자치법규일련번호", item.findtext("법령일련번호", ""))
                r["name"] = item.findtext("자치법규명", item.findtext("법령명한글", ""))
                r["category"] = item.findtext(
                    "자치법규종류",
                    item.findtext("자치법규구분", item.findtext("법령구분명", "")),
                )
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
        print(f"[law-chatbot] XML 파싱 오류: {e}")

    return results


async def _generate_answer(
    client,
    question: str,
    vector_results: list,
    api_results: list,
    detail_texts: list,
    chat_history: list = None,
) -> dict:
    context_parts = []

    if vector_results:
        context_parts.append("[충주시 자치법규 벡터스토어 검색 결과]")

        for i, r in enumerate(vector_results, 1):
            meta = r.get("metadata", {})
            score = r.get("score", 0)

            context_parts.append(
                f"({i}) {meta.get('law_name', '')} {meta.get('article', '')} "
                f"(유사도: {score:.2f})\n{r.get('content', '')}\n"
            )

    if api_results:
        context_parts.append("[MCP/API 법령·자치법규 검색 결과]")

        for i, r in enumerate(api_results[:10], 1):
            ref_type = r.get("type", "")
            label = {
                "law": "국가법령",
                "ordin": "자치법규",
                "admrul": "행정규칙",
            }.get(ref_type, "법령")

            context_parts.append(
                f"({i}) [{label}/{r.get('category', '')}] {r.get('name', '')} "
                f"(시행: {r.get('enforcement_date', '')}, 출처: {r.get('source', '')})"
            )

    if detail_texts:
        context_parts.append("\n[법령 본문 - 관련 조문]")
        for dt in detail_texts:
            context_parts.append(f"=== {dt['name']} ===\n{dt['content']}\n")

    context = "\n".join(context_parts) if context_parts else "(검색 결과 없음)"

    MAX_CONTEXT_CHARS = 60000

    if len(context) > MAX_CONTEXT_CHARS:
        print(f"[law-chatbot] ⚠️ 컨텍스트 초과: {len(context)}자 → {MAX_CONTEXT_CHARS}자로 절삭")
        context = context[:MAX_CONTEXT_CHARS] + "\n\n... (이하 생략)"

    _template = prompt_service.get(
        "law_chatbot",
        "answer_system_prompt",
        default=_DEFAULT_ANSWER_SYSTEM,
    )

    system_prompt = _template.format(context=context)

    print(f"[law-chatbot] GPT 컨텍스트: {len(context)}자")

    messages = [{"role": "system", "content": system_prompt}]

    if chat_history:
        for msg in chat_history[-10:]:
            role = msg.get("role", "user")
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

    references = []

    for r in api_results[:5]:
        ref_type = r.get("type", "")

        ref = {
            "name": r.get("name", ""),
            "type": {
                "law": r.get("category", "") or "국가법령",
                "ordin": "자치법규",
                "admrul": "행정규칙",
            }.get(ref_type, r.get("category", "") or "법령"),
            "enforcement_date": r.get("enforcement_date", ""),
            "source": r.get("source", ""),
        }

        if ref_type == "ordin":
            ref["url"] = f"https://www.law.go.kr/자치법규/{r.get('name', '')}"
        elif ref_type == "admrul":
            ref["url"] = f"https://www.law.go.kr/행정규칙/{r.get('name', '')}"
        else:
            ref["url"] = f"https://www.law.go.kr/법령/{r.get('name', '')}"

        references.append(ref)

    for r in vector_results[:3]:
        meta = r.get("metadata", {})

        references.append({
            "name": meta.get("law_name", ""),
            "type": "충주시 자치법규",
            "article": meta.get("article", ""),
            "source": "vectorstore",
        })

    seen = set()
    unique_refs = []

    for ref in references:
        key = f"{ref.get('name', '')}::{ref.get('type', '')}"

        if key and key not in seen:
            seen.add(key)
            unique_refs.append(ref)

    return {
        "answer": answer_text,
        "references": unique_refs,
        "search_info": {
            "vector_count": len(vector_results),
            "api_count": len(api_results),
            "detail_count": len(detail_texts),
        },
    }


def _deduplicate_api_results(results: list) -> list:
    seen = set()
    unique = []

    for r in results:
        key = r.get("id", "") or f"{r.get('type', '')}::{r.get('name', '')}"

        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


async def _check_api_connection() -> dict:
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

                text = resp.content.decode("utf-8")
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