"""
충주시 자치법규 벡터스토어 구축 스크립트 (v2 - 인코딩 수정)

사용법:
  cd backend
  python scripts/build_law_vectorstore.py --oc YOUR_OC_CODE

결과물:
  backend/data/law_chatbot/vectorstores/index.faiss
  backend/data/law_chatbot/vectorstores/index.pkl
"""

import os
import sys
import re
import time
import json
import argparse
import pickle
from pathlib import Path

import requests
import numpy as np
import xml.etree.ElementTree as ET

# ─── 설정 ────────────────────────────────────────────
LAW_SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"
LAW_SERVICE_URL = "http://www.law.go.kr/DRF/lawService.do"

EMBEDDING_MODEL = r"C:\Users\User\Desktop\파이썬코드\rag_test\models\ko-sroberta-multitask"

OUTPUT_DIR = Path(r"C:\temp\law_vectorstore")

MAX_CHUNK_CHARS = 1500


def _decode_response(resp) -> str:
    """응답을 안전하게 UTF-8 디코딩 (관공서 네트워크 인코딩 변조 대응)"""
    return resp.content.decode("utf-8")


# ─── Step 1: 충주시 자치법규 목록 수집 ────────────────
def fetch_chungju_ordinance_list(oc: str) -> list:
    all_items = []
    page = 1

    print("\n[Step 1] 충주시 자치법규 목록 수집")
    print("-" * 50)

    while True:
        params = {
            "OC": oc,
            "target": "ordin",
            "type": "XML",
            "query": "충주시",
            "display": 100,
            "page": page,
        }

        try:
            resp = requests.get(LAW_SEARCH_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  ❌ API 요청 실패 (page {page}): {e}")
            break

        try:
            text = _decode_response(resp)
            root = ET.fromstring(text)
        except (ET.ParseError, UnicodeDecodeError) as e:
            print(f"  ❌ 파싱 실패 (page {page}): {e}")
            break

        total = int(root.findtext("totalCnt", "0"))

        if page == 1:
            print(f"  총 {total}건 발견")

        items_found = 0
        for item in list(root.findall("law")) + list(root.findall("ordin")):
            mst = (
                item.findtext("자치법규일련번호", "")
                or item.findtext("법령일련번호", "")
                or ""
            )
            name = (
                item.findtext("자치법규명", "")
                or item.findtext("법령명한글", "")
                or ""
            )
            category = (
                item.findtext("자치법규종류", "")
                or item.findtext("자치법규구분", "")
                or item.findtext("법령구분명", "")
                or ""
            )
            enforcement_date = item.findtext("시행일자", "")
            status = item.findtext("현행연혁코드", "")
            detail_link = (
                item.findtext("자치법규상세링크", "")
                or item.findtext("법령상세링크", "")
                or ""
            )

            if not mst or not name:
                continue

            region = item.findtext("지자체기관명", "") or item.findtext("자치단체명", "")
            if region and "충주" not in region:
                continue

            all_items.append({
                "mst": mst,
                "name": name,
                "category": category,
                "enforcement_date": enforcement_date,
                "status": status,
                "detail_link": detail_link,
            })
            items_found += 1

        print(f"  page {page}: {items_found}건 수집 (누적 {len(all_items)}건)")

        if page * 100 >= total or items_found == 0:
            break

        page += 1
        time.sleep(0.5)

    print(f"\n  ✅ 목록 수집 완료: 총 {len(all_items)}건")
    return all_items


# ─── Step 2: 각 법규 본문 수집 ───────────────────────
def fetch_ordinance_detail(oc: str, mst: str) -> str:
    """자치법규 1건의 본문 텍스트 추출"""
    params = {
        "OC": oc,
        "target": "ordin",
        "MST": mst,
        "type": "XML",
    }

    try:
        resp = requests.get(LAW_SERVICE_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return ""

    try:
        text = _decode_response(resp)
        root = ET.fromstring(text)
    except (ET.ParseError, UnicodeDecodeError):
        return ""

    # 조문 텍스트 추출
    parts = []

    # 방법 1: 조문 구조 탐색
    for elem in root.iter():
        tag = elem.tag or ""
        text_content = (elem.text or "").strip()
        if not text_content:
            continue

        if any(keyword in tag for keyword in [
            "조문내용", "조문제목", "항내용", "호내용", "목내용"
        ]):
            parts.append(text_content)

    # 방법 2: 조문이 못 찾아지면 모든 텍스트 노드에서 한글 추출
    if not parts:
        for elem in root.iter():
            text_content = (elem.text or "").strip()
            # 한글이 포함된 의미있는 텍스트만 (숫자/코드 제외)
            if text_content and re.search(r"[가-힣]{2,}", text_content) and len(text_content) > 10:
                parts.append(text_content)

    return "\n".join(parts)


# ─── Step 3: 조문 단위 분할 (chunking) ───────────────
def split_into_chunks(full_text: str, law_name: str) -> list:
    chunks = []

    if not full_text.strip():
        return chunks

    # "제N조" 또는 "제N조의N" 패턴으로 분할
    pattern = r"(제\d+조(?:의\d+)?)"
    parts = re.split(pattern, full_text)

    current_article = ""
    current_content = ""

    for part in parts:
        if re.match(pattern, part):
            if current_article and current_content.strip():
                chunk_text = f"{current_article} {current_content.strip()}"
                chunks.extend(
                    _maybe_split_long_chunk(chunk_text, law_name, current_article)
                )
            current_article = part
            current_content = ""
        else:
            current_content += part

    if current_article and current_content.strip():
        chunk_text = f"{current_article} {current_content.strip()}"
        chunks.extend(
            _maybe_split_long_chunk(chunk_text, law_name, current_article)
        )

    # 조문 패턴 없는 경우 (부칙 등)
    if not chunks and full_text.strip():
        for i in range(0, len(full_text), 800):
            chunk = full_text[i:i + 1000].strip()
            if chunk and len(chunk) > 20:
                chunks.append({
                    "content": chunk,
                    "article": f"(본문 {i // 800 + 1})",
                })

    return chunks


def _maybe_split_long_chunk(text: str, law_name: str, article: str) -> list:
    if len(text) <= MAX_CHUNK_CHARS:
        return [{"content": text, "article": article}]

    sub_pattern = r"([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]|\d+\.)"
    sub_parts = re.split(sub_pattern, text)

    sub_chunks = []
    current = ""

    for part in sub_parts:
        if re.match(sub_pattern, part):
            if current.strip() and len(current) > 50:
                sub_chunks.append({
                    "content": f"{article} {current.strip()}",
                    "article": article,
                })
            current = part
        else:
            current += part

    if current.strip() and len(current) > 50:
        sub_chunks.append({
            "content": f"{article} {current.strip()}",
            "article": article,
        })

    return sub_chunks if sub_chunks else [{"content": text, "article": article}]


# ─── Step 4 & 5: 임베딩 생성 + FAISS 저장 ────────────
def build_faiss_index(all_chunks: list):
    print(f"\n[Step 4] 임베딩 생성 ({EMBEDDING_MODEL})")
    print("-" * 50)

    from sentence_transformers import SentenceTransformer
    import faiss

    model = SentenceTransformer(EMBEDDING_MODEL)

    texts = [c["content"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]

    print(f"  {len(texts)}개 청크 임베딩 생성 중...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=64,
        normalize_embeddings=True,
    )
    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]
    print(f"  임베딩 차원: {dimension}")

    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    faiss_path = OUTPUT_DIR / "index.faiss"
    pkl_path = OUTPUT_DIR / "index.pkl"

    faiss.write_index(index, str(faiss_path))

    with open(pkl_path, "wb") as f:
        pickle.dump({"texts": texts, "metadatas": metadatas}, f)

    print(f"\n[Step 5] 저장 완료")
    print(f"  FAISS: {faiss_path} ({faiss_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  PKL:   {pkl_path} ({pkl_path.stat().st_size / 1024 / 1024:.1f} MB)")

    return len(texts), dimension


# ─── 메인 ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="충주시 자치법규 벡터스토어 구축")
    parser.add_argument("--oc", type=str, help="국가법령정보센터 API OC 코드")
    args = parser.parse_args()

    oc = args.oc or os.getenv("LAW_API_OC", "")
    if not oc:
        print("❌ OC 코드가 필요합니다.")
        sys.exit(1)

    print("=" * 60)
    print("  충주시 자치법규 벡터스토어 구축 (v2)")
    print("=" * 60)
    print(f"  임베딩 모델: {EMBEDDING_MODEL}")
    print(f"  출력 경로:   {OUTPUT_DIR}")

    # API 연결 테스트
    print("\n  API 연결 테스트...")
    try:
        test_resp = requests.get(
            LAW_SEARCH_URL,
            params={"OC": oc, "target": "ordin", "type": "XML", "query": "충주시", "display": 1},
            timeout=10,
        )
        test_text = _decode_response(test_resp)
        test_root = ET.fromstring(test_text)
        test_total = test_root.findtext("totalCnt", "0")

        # 태그명 확인
        first_law = test_root.find("law")
        if first_law is not None:
            name = first_law.findtext("자치법규명", "")
            print(f"  ✅ 연결 성공 ({test_total}건, 첫 번째: {name})")
        else:
            print(f"  ✅ 연결 성공 ({test_total}건)")
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        sys.exit(1)

    start_time = time.time()

    # Step 1
    ordinances = fetch_chungju_ordinance_list(oc)

    if not ordinances:
        print("❌ 수집된 자치법규가 없습니다.")
        sys.exit(1)

    # Step 2 & 3
    print(f"\n[Step 2-3] 본문 수집 + 조문 분할")
    print("-" * 50)

    all_chunks = []
    success_count = 0
    fail_count = 0
    empty_count = 0

    for i, ordin in enumerate(ordinances):
        name = ordin["name"]
        mst = ordin["mst"]

        if (i + 1) % 50 == 0 or i == 0:
            print(f"  ({i + 1}/{len(ordinances)}) {name[:30]}...")

        detail_text = fetch_ordinance_detail(oc, mst)
        if not detail_text:
            fail_count += 1
            continue

        chunks = split_into_chunks(detail_text, name)
        if not chunks:
            empty_count += 1
            continue

        for chunk in chunks:
            chunk["metadata"] = {
                "law_name": name,
                "article": chunk.pop("article", ""),
                "category": ordin["category"],
                "enforcement_date": ordin["enforcement_date"],
                "mst": mst,
                "region": "충주시",
                "type": "자치법규",
            }
            all_chunks.append(chunk)

        success_count += 1
        time.sleep(0.3)

    print(f"\n  ✅ 본문 수집 완료: 성공 {success_count}건 / 실패 {fail_count}건 / 빈 본문 {empty_count}건")
    print(f"  ✅ 총 {len(all_chunks)}개 청크 생성")

    # 샘플 출력
    if all_chunks:
        print(f"\n  --- 샘플 청크 ---")
        for c in all_chunks[:3]:
            meta = c["metadata"]
            print(f"  [{meta['law_name']}] {meta['article']}")
            print(f"    {c['content'][:100]}...")
            print()

    if not all_chunks:
        print("❌ 생성된 청크가 없습니다.")
        sys.exit(1)

    # Step 4 & 5
    total_chunks, dimension = build_faiss_index(all_chunks)

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    category_stats = {}
    for c in all_chunks:
        cat = c["metadata"].get("category", "기타")
        category_stats[cat] = category_stats.get(cat, 0) + 1

    print(f"\n{'=' * 60}")
    print(f"  ✅ 벡터스토어 구축 완료! (v2)")
    print(f"{'=' * 60}")
    print(f"  자치법규:  {success_count}건 (실패 {fail_count}건, 빈 본문 {empty_count}건)")
    print(f"  총 청크:   {total_chunks}개")
    print(f"  임베딩:    {dimension}차원")
    print(f"  소요시간:  {minutes}분 {seconds}초")
    print(f"\n  카테고리별:")
    for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}개 청크")
    print(f"\n  출력 파일:")
    print(f"    {OUTPUT_DIR / 'index.faiss'}")
    print(f"    {OUTPUT_DIR / 'index.pkl'}")


if __name__ == "__main__":
    main()