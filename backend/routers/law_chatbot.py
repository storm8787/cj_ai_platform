"""
법령정보 · 자치법규 챗봇 라우터 (v4)

- 충주시 자치법규: FAISS 벡터스토어 (의미 검색)
- 국가법령: law.go.kr API (실시간 검색)
- 항상 둘 다 검색 + 복수 키워드로 API 검색
- resp.content.decode('utf-8') 인코딩 대응
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
from sentence_transformers import SentenceTransformer

from config import settings

router = APIRouter(prefix="/api/law-chatbot", tags=["law-chatbot"])

# ─── 상수 ────────────────────────────────────────────
LAW_SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"
LAW_SERVICE_URL = "http://www.law.go.kr/DRF/lawService.do"

ANSWER_MODEL = "gpt-4o-mini"

VECTORSTORE_DIR = Path(settings.LAW_CHATBOT_VECTORSTORE_PATH)
EMBEDDING_MODEL_NAME = settings.EMBEDDING_MODEL

VECTOR_SCORE_THRESHOLD = 0.3

# ─── 벡터스토어 & 임베딩 모델 (지연 로딩) ─────────────
_faiss_index = None
_faiss_data = None
_embedding_model = None


def _load_vectorstore():
    global _faiss_index, _faiss_data

    if _faiss_index is not None:
        return

    faiss_path = VECTORSTORE_DIR / "index.faiss"
    pkl_path = VECTORSTORE_DIR / "index.pkl"

    if not faiss_path.exists() or not pkl_path.exists():
        print(f"[law-chatbot] ⚠️ 벡터스토어 없음: {VECTORSTORE_DIR}")
        return

    _faiss_index = faiss.read_index(str(faiss_path))

    with open(pkl_path, "rb") as f:
        _faiss_data = pickle.load(f)

    print(f"[law-chatbot] ✅ 벡터스토어 로드 완료: {_faiss_index.ntotal}개 문서")


def _load_embedding_model():
    global _embedding_model

    if _embedding_model is not None:
        return

    print(f"[law-chatbot] 임베딩 모델 로딩: {EMBEDDING_MODEL_NAME}")
    _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print(f"[law-chatbot] ✅ 임베딩 모델 로드 완료")


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


# ─── API 엔드포인트 ──────────────────────────────────

@router.post("/ask")
async def ask_question(req: AskRequest):
    """법령/자치법규 질의응답 (항상 둘 다 검색 + 복수 키워드)"""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # 1단계: GPT로 복수 검색 키워드 추출
    search_keywords = await _extract_search_keywords(client, req.question)
    print(f"[law-chatbot] 추출된 키워드: {search_keywords}")

    # 2단계: scope에 따라 검색 (기본은 둘 다)
    vector_results = []
    api_results = []

    if req.search_scope in ("all", "local"):
        vector_results = _search_vectorstore(req.question, top_k=5)

    if req.search_scope in ("all", "national"):
        # 복수 키워드로 각각 API 검색
        for keyword in search_keywords:
            results = await _search_law_api(keyword, targets=["law"])
            api_results.extend(results)

    # 자치법규도 API로 보충 검색 (all일 때)
    if req.search_scope == "all":
        for keyword in search_keywords[:2]:  # 자치법규는 상위 2개 키워드만
            ordin_results = await _search_law_api(keyword, targets=["ordin"])
            api_results.extend(ordin_results)

    # API 결과 중복 제거
    api_results = _deduplicate_api_results(api_results)

    # 3단계: 상위 결과 본문 가져오기 (최대 2건)
    detail_texts = []
    for r in api_results[:2]:
        mst = r.get("id", "")
        target = "ordin" if r.get("type") == "ordin" else "law"
        if mst:
            detail = await _fetch_law_detail(mst, target)
            if detail:
                detail_texts.append({
                    "name": r.get("name", ""),
                    "content": detail[:3000],
                })

    # 4단계: GPT 답변 생성
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
    """법령/자치법규 직접 검색"""
    results = await _call_law_search_api(
        target=req.target,
        query=req.query,
        page=req.page,
        display=req.display,
    )
    return {"results": results, "query": req.query, "target": req.target}


@router.get("/status")
async def get_status():
    """시스템 상태 확인"""
    _load_vectorstore()

    vector_status = {
        "loaded": _faiss_index is not None,
        "doc_count": _faiss_index.ntotal if _faiss_index else 0,
    }

    api_status = await _check_api_connection()

    return {
        "vectorstore": vector_status,
        "api": api_status,
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


# ─── 내부 함수: 복수 키워드 추출 (GPT) ───────────────

async def _extract_search_keywords(client, question: str) -> list:
    """GPT로 질문에서 법령 API 검색용 키워드를 여러 개 추출"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "사용자의 법령 관련 질문에서 국가법령정보센터 API 검색에 적합한 키워드를 추출하세요.\n"
                        "법령명, 핵심 법률 용어를 2~3개 추출하세요.\n"
                        "반드시 JSON 배열로만 응답하세요. 다른 텍스트 없이.\n\n"
                        "예시:\n"
                        '- "공무원 연가일수 규정 알려줘" → ["국가공무원 복무규정", "공무원 연가"]\n'
                        '- "소프트웨어사업 과업심의위원회 구성은?" → ["소프트웨어진흥법", "소프트웨어사업 과업심의"]\n'
                        '- "개인정보보호법에서 제3자 제공 요건은?" → ["개인정보보호법"]\n'
                        '- "장기재직휴가 몇일이야?" → ["공무원 복무규정", "장기재직휴가"]\n'
                        '- "건축 허가 기준" → ["건축법", "건축 허가"]\n'
                        '- "민원 처리 기간" → ["민원 처리에 관한 법률"]\n'
                    ),
                },
                {"role": "user", "content": question},
            ],
            temperature=0.1,
            max_tokens=100,
        )
        raw = response.choices[0].message.content.strip()

        # JSON 파싱
        # ```json 감싸기 제거
        raw = raw.replace("```json", "").replace("```", "").strip()
        keywords = json.loads(raw)

        if isinstance(keywords, list) and len(keywords) > 0:
            return keywords[:3]  # 최대 3개

    except Exception as e:
        print(f"[law-chatbot] 키워드 추출 실패: {e}")

    # 폴백: 불용어 제거 후 원문 반환
    return [_simple_keyword_extract(question)]


def _simple_keyword_extract(question: str) -> str:
    """단순 불용어 제거 폴백"""
    stopwords = [
        "알려줘", "알려주세요", "뭐야", "뭔가요", "어떻게", "무엇", "어떤",
        "규정", "규정은", "내용", "내용은", "관련", "대해", "대한",
        "있나요", "있어", "인가요", "인가", "할까요", "해줘", "해주세요",
        "좀", "그", "이", "저", "것", "수", "등", "및", "의", "에",
        "은", "는", "가", "를", "을", "에서", "으로", "로", "어떻게돼",
        "몇일이야", "몇일", "기준이", "기준", "어떻게", "구성은",
    ]
    words = question.strip().split()
    keywords = [w for w in words if w not in stopwords and len(w) > 1]
    return " ".join(keywords) if keywords else question


# ─── 내부 함수: API 결과 중복 제거 ───────────────────

def _deduplicate_api_results(results: list) -> list:
    seen = set()
    unique = []
    for r in results:
        key = r.get("id", "") or r.get("name", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


# ─── 내부 함수: 벡터스토어 검색 ──────────────────────

def _search_vectorstore(query: str, top_k: int = 5) -> list:
    _load_vectorstore()
    _load_embedding_model()

    if _faiss_index is None or _faiss_data is None or _embedding_model is None:
        return []

    query_vec = _embedding_model.encode([query], normalize_embeddings=True)
    query_vec = np.array(query_vec).astype("float32")

    scores, indices = _faiss_index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(_faiss_data["texts"]):
            continue
        if score < VECTOR_SCORE_THRESHOLD:
            continue

        results.append({
            "content": _faiss_data["texts"][idx],
            "metadata": _faiss_data["metadatas"][idx],
            "score": float(score),
        })

    return results


# ─── 내부 함수: 법령 API 검색 ────────────────────────

async def _search_law_api(query: str, targets: list) -> list:
    oc = settings.LAW_API_OC
    if not oc:
        print("[law-chatbot] ⚠️ LAW_API_OC 환경변수 미설정")
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
                    continue

                text = resp.content.decode("utf-8")

                if text.strip().startswith("<!DOCTYPE") or text.strip().startswith("<html"):
                    print(f"[law-chatbot] ⚠️ API 인증 실패 (target={target})")
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

        return _parse_search_xml(text, target)


async def _fetch_law_detail(mst: str, target: str = "law") -> str:
    oc = settings.LAW_API_OC
    if not oc:
        return ""

    async with httpx.AsyncClient(timeout=15.0) as client:
        params = {
            "OC": oc,
            "target": target,
            "MST": mst,
            "type": "XML",
        }

        try:
            resp = await client.get(LAW_SERVICE_URL, params=params)
            text = resp.content.decode("utf-8")

            if text.strip().startswith("<!DOCTYPE"):
                return ""

            return _extract_text_from_detail_xml(text)
        except Exception as e:
            print(f"[law-chatbot] 본문 조회 실패 (MST={mst}): {e}")
            return ""


# ─── 내부 함수: XML 파싱 ─────────────────────────────

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


def _extract_text_from_detail_xml(xml_text: str) -> str:
    try:
        root = ET.fromstring(xml_text)
        parts = []

        for elem in root.iter():
            tag = elem.tag or ""
            text = (elem.text or "").strip()
            if not text:
                continue
            if any(k in tag for k in ["조문내용", "조문제목", "항내용", "호내용", "목내용"]):
                parts.append(text)

        if not parts:
            for elem in root.iter():
                text = (elem.text or "").strip()
                if text and re.search(r"[가-힣]{2,}", text) and len(text) > 10:
                    parts.append(text)

        return "\n".join(parts) if parts else ""
    except ET.ParseError:
        return ""


# ─── 내부 함수: 답변 생성 ────────────────────────────

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
        context_parts.append("[충주시 자치법규 검색 결과 - FAISS 벡터스토어]")
        for i, r in enumerate(vector_results, 1):
            meta = r.get("metadata", {})
            score = r.get("score", 0)
            context_parts.append(
                f"({i}) {meta.get('law_name', '')} {meta.get('article', '')} "
                f"(유사도: {score:.2f})\n{r.get('content', '')}\n"
            )

    if api_results:
        context_parts.append("[국가법령정보센터 API 검색 결과]")
        for i, r in enumerate(api_results[:10], 1):
            context_parts.append(
                f"({i}) [{r.get('category', '')}] {r.get('name', '')} "
                f"(시행: {r.get('enforcement_date', '')})"
            )

    if detail_texts:
        context_parts.append("\n[법령 본문 (발췌)]")
        for dt in detail_texts:
            context_parts.append(f"--- {dt['name']} ---\n{dt['content']}\n")

    context = "\n".join(context_parts) if context_parts else "(관련 법령을 찾지 못했습니다)"

    system_prompt = f"""당신은 충주시청 공무원을 위한 법령·자치법규 전문 AI 어시스턴트입니다.

[역할]
- 국가법령과 충주시 자치법규에 대한 정확한 정보를 제공합니다.
- 관련 조문을 인용하며 근거를 밝힙니다.

[중요 규칙]
1. 반드시 아래 [검색된 참고자료]에 있는 내용만 근거로 답변하세요.
2. 참고자료에 없는 내용은 추측하지 말고 "검색 결과에서 관련 내용을 찾지 못했습니다"라고 답하세요.
3. 충주시 자치법규(FAISS 벡터스토어 결과)와 국가법령(API 결과)을 명확히 구분하여 답변하세요.
4. 어떤 정보가 충주시 자치법규에서 온 것이고, 어떤 정보가 국가법령에서 온 것인지 출처를 밝히세요.
5. 확실하지 않으면 "정확한 해석을 위해 법제팀 확인을 권장합니다" 안내하세요.
6. 법령이 개정되었을 수 있으므로 "현행 기준" 등 시점을 명시하세요.
7. 복잡한 법률 용어는 쉽게 풀어서 설명하세요.
8. 답변 마지막에 참고한 법령/조례 이름을 정리하세요.

[검색된 참고자료]
{context}
"""

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
            temperature=0.3,
        )
        answer_text = response.choices[0].message.content
    except Exception as e:
        print(f"[law-chatbot] GPT 답변 생성 실패: {e}")
        answer_text = "죄송합니다. 답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

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


# ─── 유틸 ────────────────────────────────────────────

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