"""
법령정보 · 자치법규 챗봇 라우터 (v8)

v7 → v8 변경사항:
1. BM25 Hybrid Search 연결: dense + BM25 결과를 RRF로 합산
2. bm25_corpus.pkl 로드 + rank_bm25 라이브러리 사용
"""

import os
import json
import pickle
import re
from pathlib import Path
from typing import Optional, List

import faiss
import numpy as np
import httpx
import xml.etree.ElementTree as ET
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
#from sentence_transformers import SentenceTransformer
from FlagEmbedding import BGEM3FlagModel

from config import settings
from services.prompt_service import prompt_service

# BM25 Hybrid Search
try:
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False
    print("[law-chatbot] ⚠️ rank_bm25 미설치, dense 검색만 사용")

router = APIRouter(prefix="/api/law-chatbot", tags=["law-chatbot"])

# ─── 상수 ────────────────────────────────────────────
LAW_SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"
LAW_SERVICE_URL = "http://www.law.go.kr/DRF/lawService.do"

ANSWER_MODEL = "gpt-4o"
KEYWORD_MODEL = "gpt-4o"
UTILITY_MODEL = "gpt-4o-mini"  # 단순 판단/변환용 (비용 절약)

VECTORSTORE_DIR = Path(settings.LAW_CHATBOT_VECTORSTORE_PATH)
EMBEDDING_MODEL_NAME = settings.EMBEDDING_MODEL

# 유사도: 절대 threshold + 상대 threshold
VECTOR_SCORE_MIN = 0.30        # 이 이하는 무조건 제외
VECTOR_SCORE_RELATIVE = 0.85   # 최고 유사도의 85% 이하는 제외

MAX_RETRY = 2  # 재검색 최대 횟수

# ─── 벡터스토어 & 임베딩 모델 (지연 로딩) ─────────────
_faiss_index = None
_faiss_data = None
_embedding_model = None
_bm25_index = None
_bm25_corpus = None


# ─── 프롬프트 기본값 (DB에 없을 때 사용) ───
_DEFAULT_EXTRACT_KEYWORDS = """당신은 법령 검색 전문가입니다. 사용자의 질문에서 국가법령정보센터 API 검색에 적합한 키워드를 추출하세요.

[규칙]
1. 법령명이나 핵심 법률 용어를 2~3개 추출
2. 실무 상황이면 관련 법령명을 추론 (예: 출장+초과근무 → 공무원 복무규정)
3. 가능하면 정확한 법령명을 포함 (예: '지방공무원 복무규정', '국가공무원 복무규정')
4. 반드시 JSON 배열로만 응답. 다른 텍스트 없이.

[예시]
"관외출장 갔는데 초과근무 되나?" → ["지방공무원 복무규정", "초과근무"]
"정근수당 받을 수 있나?" → ["공무원보수규정", "정근수당"]
"육아휴직 복직 후 수당" → ["공무원보수규정", "육아휴직"]
"연차 안 쓰면 수당 나오나?" → ["공무원보수규정", "연가보상비"]
"10년차 공무원 연가일수" → ["지방공무원 복무규정", "국가공무원 복무규정"]
"소프트웨어사업 과업심의" → ["소프트웨어진흥법", "소프트웨어사업"]
"건축 허가 기준" → ["건축법"]
"개인정보 제3자 제공" → ["개인정보보호법"]"""

_DEFAULT_ALTERNATIVE_KEYWORDS = """사용자의 법령 관련 질문에 대해 국가법령정보센터 API 검색용 키워드를 생성하세요.
이전에 시도한 키워드로는 검색 결과가 없었습니다.
다른 법령명이나 다른 표현의 키워드를 2~3개 제안하세요.
반드시 JSON 배열로만 응답하세요.

전략:
- 상위법/시행령/시행규칙 등 관련 법령명을 시도
- 더 넓은 범위의 법령명을 시도 (예: '소프트웨어진흥법' 실패 → '소프트웨어' 또는 '전자정부법')
- 동의어나 유사 표현을 시도"""

_DEFAULT_ANSWER_SYSTEM = """당신은 충주시청 공무원을 위한 법령·자치법규 전문 AI 어시스턴트입니다.

[역할]
공무원이 실무에서 바로 활용할 수 있도록 정확하고 구체적인 법령 정보를 제공합니다.

[답변 전략 - 3단계]

1단계: [검색된 참고자료]에 답이 있는 경우
→ 반드시 조문 번호를 정확히 인용하며 구체적으로 답변하세요.
→ 법령명은 정식 명칭 그대로 사용하세요 (임의로 변경 금지).
→ 수치(일수, 금액, 기간 등)가 있으면 반드시 구체적으로 제시하세요.

2단계: 검색 결과에 충분한 답이 없지만, 본인의 법률 지식으로 답할 수 있는 경우
→ 답변하되, 답변 끝에 반드시 다음을 표시:
💡 이 내용은 AI의 일반 법률 지식을 기반으로 한 답변입니다. 정확한 조문 확인은 국가법령정보센터(law.go.kr)에서 확인하시기 바랍니다.

3단계: 둘 다 모르는 경우
→ "해당 내용에 대한 정확한 정보를 찾지 못했습니다. 법제팀 또는 국가법령정보센터에서 확인하시기 바랍니다."

[답변 형식]
1. 결론을 먼저 한 문장으로 제시
2. 근거 조문 인용 (📌 법령명 + 조문번호 + 핵심 내용)
3. 실무 적용 시 유의사항이 있으면 ⚠️로 안내
4. 답변 마지막에 📋 참고 법령 목록

[절대 금지 규칙]
- 검색 결과에 있더라도 질문 대상과 다른 법령은 절대 인용하지 마세요.
  예: 일반 공무원에 대한 질문에 "청원경찰 복무 규칙"을 인용하면 안 됩니다.
  예: 충주시 공무원에 대한 질문에 "충주시 택견원 설치 조례"를 인용하면 안 됩니다.
- 법령명을 임의로 변경하거나 축약하지 마세요.
  예: "지방공무원 복무규정" → "충주시 지방공무원 복무 규칙" (X)
- 확인할 수 없는 조문 번호를 만들어내지 마세요.
- 표(별표)의 수치를 해석할 때 구간을 정확히 매칭하세요.
  예: "10년차"는 "6년 이상" 구간에 해당 → 해당 구간의 수치를 적용

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

    # BM25 인덱스 로드
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


# ─── Pydantic 모델 ───────────────────────────────────
class AskRequest(BaseModel):
    question: str
    search_scope: str = "all"
    chat_history: Optional[List[dict]] = None


class SearchRequest(BaseModel):
    query: str
    target: str = "law"
    page: int = 1
    display: int = 20


# ─── 메인 엔드포인트 ─────────────────────────────────

@router.post("/ask")
async def ask_question(req: AskRequest):
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # ── 1단계: 키워드 추출 ──
    search_keywords = await _extract_search_keywords(client, req.question)
    print(f"[law-chatbot] 키워드: {search_keywords}")

    # ── 2단계: Agentic 검색 (재검색 루프 포함) ──
    vector_results, api_results = await _agentic_search(
        client=client,
        question=req.question,
        initial_keywords=search_keywords,
        search_scope=req.search_scope,
    )

    # ── 3단계: 관련 조문 추출 ──
    detail_texts = []
    for r in api_results[:3]:
        mst = r.get("id", "")
        target = "ordin" if r.get("type") == "ordin" else "law"
        if mst:
            relevant = await _fetch_relevant_articles(
                mst, target, req.question, search_keywords
            )
            if relevant:
                detail_texts.append({"name": r.get("name", ""), "content": relevant})

    print(f"[law-chatbot] 최종 결과: vector={len(vector_results)}, api={len(api_results)}, detail={len(detail_texts)}")

    # ── 4단계: GPT 답변 생성 ──
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
        target=req.target, query=req.query,
        page=req.page, display=req.display,
    )
    return {"results": results, "query": req.query, "target": req.target}


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
            {"id": "all", "name": "전체 (법령 + 자치법규)", "icon": "📚"},
            {"id": "national", "name": "국가법령", "icon": "🏛️"},
            {"id": "local", "name": "충주시 자치법규", "icon": "🏘️"},
        ]
    }


# ══════════════════════════════════════════════════════
# Agentic 재검색 루프 (v7 핵심)
# ══════════════════════════════════════════════════════

async def _agentic_search(
    client, question: str, initial_keywords: list, search_scope: str,
) -> tuple:
    """
    검색 → 결과 평가 → 부족하면 키워드 변경 후 재검색 (최대 MAX_RETRY회)
    """
    all_vector_results = []
    all_api_results = []
    tried_keywords = set()

    current_keywords = initial_keywords

    for attempt in range(MAX_RETRY + 1):
        # ── 벡터스토어 검색 (첫 시도만) ──
        if attempt == 0 and search_scope in ("all", "local"):
            vector_results = _search_vectorstore(question, top_k=7)
            all_vector_results = vector_results

        # ── API 검색 ──
        if search_scope in ("all", "national"):
            for kw in current_keywords:
                if kw in tried_keywords:
                    continue
                tried_keywords.add(kw)
                results = await _search_law_api(kw, targets=["law"])
                all_api_results.extend(results)

        if search_scope == "all":
            for kw in current_keywords[:2]:
                ordin_kw = kw
                if ordin_kw in tried_keywords:
                    continue
                tried_keywords.add(ordin_kw)
                ordin_results = await _search_law_api(kw, targets=["ordin"])
                all_api_results.extend(ordin_results)

        all_api_results = _deduplicate_api_results(all_api_results)

        # ── 결과 충분성 판단 ──
        has_good_vector = (
            all_vector_results
            and all_vector_results[0]["score"] > 0.5
        )
        has_api_results = len(all_api_results) > 0

        if has_good_vector or has_api_results:
            print(f"[law-chatbot] 검색 성공 (attempt {attempt + 1})")
            break

        if attempt < MAX_RETRY:
            # ── GPT에게 대안 키워드 요청 ──
            current_keywords = await _generate_alternative_keywords(
                client, question, list(tried_keywords)
            )
            print(f"[law-chatbot] 재검색 (attempt {attempt + 2}): {current_keywords}")

    # 동적 threshold로 벡터 결과 필터링
    all_vector_results = _apply_dynamic_threshold(all_vector_results)

    return all_vector_results, all_api_results


async def _generate_alternative_keywords(
    client, question: str, tried_keywords: list
) -> list:
    """이전 검색이 실패했을 때 다른 키워드를 생성"""
    system_content = prompt_service.get(
        "law_chatbot", "alternative_keywords",
        default=_DEFAULT_ALTERNATIVE_KEYWORDS
    )
    
    try:
        response = await client.chat.completions.create(
            model=UTILITY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_content,
                },
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


# ══════════════════════════════════════════════════════
# 키워드 추출
# ══════════════════════════════════════════════════════

async def _extract_search_keywords(client, question: str) -> list:
    system_content = prompt_service.get(
        "law_chatbot", "extract_keywords",
        default=_DEFAULT_EXTRACT_KEYWORDS
    )
    
    try:
        response = await client.chat.completions.create(
            model=KEYWORD_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_content,
                },
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
    stopwords = {"알려줘", "알려주세요", "뭐야", "어떻게", "무엇", "어떤",
                 "규정은", "내용은", "관련", "대해", "있나요", "있어",
                 "인가요", "해줘", "해주세요", "어떻게돼", "몇일이야",
                 "기준이", "기준", "구성은", "좀", "그", "이", "저",
                 "것", "수", "등", "및", "의", "에", "은", "는",
                 "가", "를", "을", "에서", "으로", "로"}
    words = question.strip().split()
    keywords = [w for w in words if w not in stopwords and len(w) > 1]
    return " ".join(keywords) if keywords else question


# ══════════════════════════════════════════════════════
# 벡터스토어 검색 + 동적 threshold
# ══════════════════════════════════════════════════════

def _search_vectorstore(query: str, top_k: int = 7) -> list:
    """Hybrid Search: dense(FAISS) + BM25 결과를 RRF로 합산"""
    _load_vectorstore()
    _load_embedding_model()
    if _faiss_index is None or _faiss_data is None or _embedding_model is None:
        return []

    # ── Dense 검색 (FAISS) ──
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

    dense_k = top_k * 3  # RRF 합산을 위해 더 많이 가져옴
    scores, indices = _faiss_index.search(query_vec, dense_k)

    dense_results = {}
    for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
        if idx < 0 or idx >= len(_faiss_data["texts"]):
            continue
        if score < VECTOR_SCORE_MIN:
            continue
        dense_results[int(idx)] = {"rank": rank, "score": float(score)}

    # ── BM25 검색 ──
    bm25_results = {}
    if _bm25_index is not None:
        query_tokens = _tokenize_korean(query)
        if query_tokens:
            bm25_scores = _bm25_index.get_scores(query_tokens)
            bm25_top_indices = np.argsort(bm25_scores)[::-1][:dense_k]
            for rank, idx in enumerate(bm25_top_indices):
                if bm25_scores[idx] > 0:
                    bm25_results[int(idx)] = {"rank": rank, "score": float(bm25_scores[idx])}

    # ── RRF 합산 ──
    k = 60  # RRF 상수
    rrf_scores = {}
    all_indices = set(dense_results.keys()) | set(bm25_results.keys())

    for idx in all_indices:
        rrf = 0.0
        if idx in dense_results:
            rrf += 1.0 / (k + dense_results[idx]["rank"] + 1)
        if idx in bm25_results:
            rrf += 1.0 / (k + bm25_results[idx]["rank"] + 1)
        rrf_scores[idx] = rrf

    # RRF 점수 높은 순 정렬
    sorted_indices = sorted(rrf_scores.items(), key=lambda x: -x[1])

    results = []
    for idx, rrf_score in sorted_indices[:top_k]:
        # dense score가 있으면 그걸 표시, 없으면 RRF 점수
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
        dense_only = sum(1 for r in results if r["sources"]["dense"] and not r["sources"]["bm25"])
        bm25_only = sum(1 for r in results if r["sources"]["bm25"] and not r["sources"]["dense"])
        both = sum(1 for r in results if r["sources"]["dense"] and r["sources"]["bm25"])
        print(f"[law-chatbot] Hybrid 검색: dense만={dense_only}, bm25만={bm25_only}, 둘다={both}")

    return results


def _tokenize_korean(text: str) -> list:
    """한국어 텍스트를 단순 토큰화"""
    text = re.sub(r"[^\w가-힣]", " ", text)
    tokens = text.split()
    tokens = [t.lower() for t in tokens if len(t) > 1]
    return tokens


def _apply_dynamic_threshold(results: list) -> list:
    """최고 유사도 대비 상대적으로 낮은 결과 제거"""
    if not results:
        return results

    max_score = results[0]["score"]
    threshold = max_score * VECTOR_SCORE_RELATIVE

    filtered = [r for r in results if r["score"] >= threshold]

    # 최대 5개까지만
    return filtered[:5]


# ══════════════════════════════════════════════════════
# 법령 API 검색
# ══════════════════════════════════════════════════════

async def _search_law_api(query: str, targets: list) -> list:
    oc = settings.LAW_API_OC
    if not oc:
        return []
    all_results = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for target in targets:
            try:
                params = {
                    "OC": oc, "target": target, "type": "XML",
                    "query": query if target != "ordin" else f"충주시 {query}",
                    "display": 10, "page": 1,
                }
                resp = await client.get(LAW_SEARCH_URL, params=params)
                if resp.status_code != 200:
                    continue
                text = resp.content.decode("utf-8")
                if text.strip().startswith("<!DOCTYPE") or text.strip().startswith("<html"):
                    continue
                items = _parse_search_xml(text, target)
                all_results.extend(items)
            except Exception as e:
                print(f"[law-chatbot] API 검색 실패 (target={target}): {e}")
    return all_results


async def _call_law_search_api(target: str, query: str, page: int, display: int) -> list:
    oc = settings.LAW_API_OC
    if not oc:
        raise HTTPException(status_code=500, detail="LAW_API_OC 환경변수 미설정")
    async with httpx.AsyncClient(timeout=15.0) as client:
        params = {
            "OC": oc, "target": target, "type": "XML",
            "query": query, "display": display, "page": page,
        }
        resp = await client.get(LAW_SEARCH_URL, params=params)
        text = resp.content.decode("utf-8")
        if text.strip().startswith("<!DOCTYPE"):
            raise HTTPException(status_code=502, detail="법령 API 인증 실패")
        return _parse_search_xml(text, target)


# ══════════════════════════════════════════════════════
# 관련 조문 추출
# ══════════════════════════════════════════════════════

async def _fetch_relevant_articles(
    mst: str, target: str, question: str, keywords: list
) -> str:
    oc = settings.LAW_API_OC
    if not oc:
        return ""
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.get(
                LAW_SERVICE_URL,
                params={"OC": oc, "target": target, "MST": mst, "type": "XML"},
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

    # 검색어 구성
    search_terms = set()
    for word in question.split():
        if len(word) >= 2:
            search_terms.add(word)
    for kw in keywords:
        for word in kw.split():
            if len(word) >= 2:
                search_terms.add(word)
    stopwords = {"어떻게", "어떤", "무엇", "알려줘", "알려주세요", "규정은",
                 "기준이", "기준은", "몇일이야", "있나요", "인가요", "해줘",
                 "어떻게돼", "뭐야", "구성은", "해야해", "받을수", "있을까",
                 "경우", "했을경우", "복직했을경우", "대상사업은"}
    search_terms -= stopwords

    # 관련도 점수
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
        article_text = f"[{article.get('number', '')} {article.get('title', '')}]\n{article.get('content', '')}"
        if total_chars + len(article_text) > 8000:
            break
        selected.append(article_text)
        total_chars += len(article_text)

    # 관련 조문 없으면 처음 5개
    if not selected and articles:
        for article in articles[:5]:
            article_text = f"[{article.get('number', '')} {article.get('title', '')}]\n{article.get('content', '')}"
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
                    "number": number, "title": title,
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
                    articles.append({"number": number, "title": "", "content": text})

        # 별표 추출
        for bt in root.iter("별표단위"):
            bt_title = bt.findtext("별표제목", "")
            bt_content = bt.findtext("별표내용", "").strip()
            if bt_title:
                articles.append({
                    "number": bt_title, "title": "",
                    "content": bt_content if bt_content else f"(첨부파일로 제공 - {bt_title})",
                })

    except ET.ParseError as e:
        print(f"[law-chatbot] XML 파싱 오류: {e}")
    return articles


# ══════════════════════════════════════════════════════
# XML 파싱 (검색 결과)
# ══════════════════════════════════════════════════════

def _parse_search_xml(xml_text: str, target: str) -> list:
    results = []
    try:
        root = ET.fromstring(xml_text)
        total = root.findtext("totalCnt", "0")
        for item in list(root.findall("law")) + list(root.findall("ordin")) + list(root.findall("expc")):
            r = {"type": target, "total_count": int(total)}
            if target == "ordin":
                r["id"] = item.findtext("자치법규일련번호", item.findtext("법령일련번호", ""))
                r["name"] = item.findtext("자치법규명", item.findtext("법령명한글", ""))
                r["category"] = item.findtext("자치법규종류", item.findtext("자치법규구분", item.findtext("법령구분명", "")))
                r["region"] = item.findtext("지자체기관명", item.findtext("자치단체명", ""))
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


# ══════════════════════════════════════════════════════
# 답변 생성 (v7 프롬프트 대폭 강화)
# ══════════════════════════════════════════════════════

async def _generate_answer(
    client, question: str,
    vector_results: list, api_results: list,
    detail_texts: list, chat_history: list = None,
) -> dict:

    context_parts = []

    if vector_results:
        context_parts.append("[충주시 자치법규 검색 결과]")
        for i, r in enumerate(vector_results, 1):
            meta = r.get("metadata", {})
            score = r.get("score", 0)
            context_parts.append(
                f"({i}) {meta.get('law_name', '')} {meta.get('article', '')} "
                f"(유사도: {score:.2f})\n{r.get('content', '')}\n"
            )

    if api_results:
        context_parts.append("[국가법령 검색 결과]")
        for i, r in enumerate(api_results[:10], 1):
            context_parts.append(
                f"({i}) [{r.get('category', '')}] {r.get('name', '')} "
                f"(시행: {r.get('enforcement_date', '')})"
            )

    if detail_texts:
        context_parts.append("\n[법령 본문 - 관련 조문]")
        for dt in detail_texts:
            context_parts.append(f"=== {dt['name']} ===\n{dt['content']}\n")

    context = "\n".join(context_parts) if context_parts else "(검색 결과 없음)"

    # ✅ 컨텍스트 길이 제한 (GPT-4o 128K 토큰 ≈ 약 80,000자 한국어)
    MAX_CONTEXT_CHARS = 60000
    if len(context) > MAX_CONTEXT_CHARS:
        print(f"[law-chatbot] ⚠️ 컨텍스트 초과: {len(context)}자 → {MAX_CONTEXT_CHARS}자로 절삭")
        context = context[:MAX_CONTEXT_CHARS] + "\n\n... (이하 생략)"

    # 시스템 프롬프트 (DB 우선, 없으면 기본값)
    _template = prompt_service.get(
        "law_chatbot", "answer_system_prompt",
        default=_DEFAULT_ANSWER_SYSTEM
    )
    system_prompt = _template.format(context=context)

    print(f"[law-chatbot] GPT 컨텍스트: {len(context)}자")

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for msg in chat_history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})

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

    # 참조 법령 목록
    references = []
    for r in api_results[:5]:
        ref = {
            "name": r.get("name", ""),
            "type": r.get("category", ""),
            "enforcement_date": r.get("enforcement_date", ""),
        }
        if r.get("type") == "ordin":
            ref["url"] = f"https://www.law.go.kr/자치법규/{r.get('name', '')}"
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
        key = ref.get("name", "")
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


# ══════════════════════════════════════════════════════
# 유틸
# ══════════════════════════════════════════════════════

def _deduplicate_api_results(results: list) -> list:
    seen = set()
    unique = []
    for r in results:
        key = r.get("id", "") or r.get("name", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


async def _check_api_connection() -> dict:
    oc = settings.LAW_API_OC
    if not oc:
        return {"connected": False, "reason": "LAW_API_OC 미설정"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                LAW_SEARCH_URL,
                params={"OC": oc, "target": "law", "type": "XML", "query": "헌법", "display": 1},
            )
            text = resp.content.decode("utf-8")
            is_xml = not text.strip().startswith("<!DOCTYPE")
            return {"connected": is_xml, "status_code": resp.status_code}
    except Exception as e:
        return {"connected": False, "reason": str(e)}