"""
충주시 자치법규 벡터스토어 구축 스크립트

사용법:
  cd backend
  pip install -r requirements.txt
  python scripts/build_law_vectorstore.py --oc YOUR_OC_CODE

또는 환경변수:
  LAW_API_OC=xxx python scripts/build_law_vectorstore.py

소요시간: 약 10~20분 (자치법규 ~600건 수집 + 임베딩)
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

# 기존 선거법 챗봇과 동일한 임베딩 모델
EMBEDDING_MODEL = r"C:\Users\User\Desktop\파이썬코드\rag_test\models\ko-sroberta-multitask"

# 출력 경로 (기존 선거법 벡터스토어와 동일한 구조)
#OUTPUT_DIR = Path(__file__).parent.parent / "data" / "law_chatbot" / "vectorstores"
OUTPUT_DIR = Path(r"C:\temp\law_vectorstore")

# chunking 설정
MAX_CHUNK_CHARS = 1500  # 이 이상이면 항 단위로 분할


# ─── Step 1: 충주시 자치법규 목록 수집 ────────────────
def fetch_chungju_ordinance_list(oc: str) -> list:
    """law.go.kr API로 충주시 자치법규 목록 전량 수집"""
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
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:
            print(f"  ❌ XML 파싱 실패 (page {page}): {e}")
            break

        total = int(root.findtext("totalCnt", "0"))

        if page == 1:
            print(f"  총 {total}건 발견")

        # 자치법규 목록의 XML 태그는 API 버전에 따라 다를 수 있음
        # <law> 또는 <ordin> 태그 모두 탐색
        items_found = 0
        for item in list(root.findall("law")) + list(root.findall("ordin")):
            # 자치법규 일련번호 (태그명이 다를 수 있음)
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
                item.findtext("자치법규구분", "")
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

            # 충주시 관련만 필터 (다른 지자체 결과 제외)
            region = item.findtext("자치단체명", "")
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
        time.sleep(0.5)  # Rate limiting

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
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return ""

    # 조문 텍스트 추출 - 다양한 XML 구조 대응
    parts = []

    for elem in root.iter():
        tag = elem.tag or ""
        text = (elem.text or "").strip()
        if not text:
            continue

        # 조문 관련 태그들
        if any(keyword in tag for keyword in [
            "조문내용", "조문", "항내용", "호내용", "목내용",
            "조문제목", "조문참고자료"
        ]):
            parts.append(text)

    return "\n".join(parts)


# ─── Step 3: 조문 단위 분할 (chunking) ───────────────
def split_into_chunks(full_text: str, law_name: str) -> list:
    """법규 본문을 조문 단위로 분할"""
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
            # 이전 조문 저장
            if current_article and current_content.strip():
                chunk_text = f"{current_article} {current_content.strip()}"
                chunks.extend(
                    _maybe_split_long_chunk(chunk_text, law_name, current_article)
                )
            current_article = part
            current_content = ""
        else:
            current_content += part

    # 마지막 조문
    if current_article and current_content.strip():
        chunk_text = f"{current_article} {current_content.strip()}"
        chunks.extend(
            _maybe_split_long_chunk(chunk_text, law_name, current_article)
        )

    # 조문 패턴이 없는 경우 (부칙 등) → 800자 단위 분할
    if not chunks and full_text.strip():
        for i in range(0, len(full_text), 800):
            chunk = full_text[i:i + 1000].strip()
            if chunk:
                chunks.append({
                    "content": chunk,
                    "article": f"(본문 {i // 800 + 1})",
                })

    return chunks


def _maybe_split_long_chunk(text: str, law_name: str, article: str) -> list:
    """1500자 초과 시 항 단위로 추가 분할"""
    if len(text) <= MAX_CHUNK_CHARS:
        return [{"content": text, "article": article}]

    # 항 단위 분할: ① ② ③ ... 또는 1. 2. 3. ...
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

    # 분할 실패 시 원본 그대로
    return sub_chunks if sub_chunks else [{"content": text, "article": article}]


# ─── Step 4 & 5: 임베딩 생성 + FAISS 저장 ────────────
def build_faiss_index(all_chunks: list):
    """임베딩 생성 후 FAISS 인덱스 저장"""

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
        normalize_embeddings=True,  # 코사인 유사도용
    )
    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]
    print(f"  임베딩 차원: {dimension}")

    # FAISS 인덱스 생성 (Inner Product = 코사인 유사도, 정규화 후)
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    # 저장
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
        print("   사용법: python scripts/build_law_vectorstore.py --oc YOUR_OC_CODE")
        print("   또는:   LAW_API_OC=xxx python scripts/build_law_vectorstore.py")
        print("   발급:   https://open.law.go.kr 회원가입 → API 사용 신청")
        sys.exit(1)

    print("=" * 60)
    print("  충주시 자치법규 벡터스토어 구축")
    print("=" * 60)
    print(f"  임베딩 모델: {EMBEDDING_MODEL}")
    print(f"  출력 경로:   {OUTPUT_DIR}")
    print(f"  API OC:      {oc[:4]}{'*' * (len(oc) - 4)}")

    # API 연결 테스트
    print("\n  API 연결 테스트...")
    try:
        test_resp = requests.get(
            LAW_SEARCH_URL,
            params={"OC": oc, "target": "ordin", "type": "XML", "query": "충주시", "display": 1},
            timeout=10,
        )
        test_root = ET.fromstring(test_resp.text)
        test_total = test_root.findtext("totalCnt", "0")
        print(f"  ✅ 연결 성공 (충주시 자치법규 {test_total}건 확인)")
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        print("  OC 코드를 확인해주세요.")
        sys.exit(1)

    start_time = time.time()

    # Step 1: 목록 수집
    ordinances = fetch_chungju_ordinance_list(oc)

    if not ordinances:
        print("❌ 수집된 자치법규가 없습니다. OC 코드와 API 상태를 확인해주세요.")
        sys.exit(1)

    # Step 2 & 3: 본문 수집 + 조문 분할
    print(f"\n[Step 2-3] 본문 수집 + 조문 분할")
    print("-" * 50)

    all_chunks = []
    success_count = 0
    fail_count = 0

    for i, ordin in enumerate(ordinances):
        name = ordin["name"]
        mst = ordin["mst"]

        # 진행률 표시 (10건마다)
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  ({i + 1}/{len(ordinances)}) {name[:30]}...")

        # 본문 수집
        detail_text = fetch_ordinance_detail(oc, mst)
        if not detail_text:
            fail_count += 1
            continue

        # 조문 분할
        chunks = split_into_chunks(detail_text, name)
        if not chunks:
            fail_count += 1
            continue

        # 메타데이터 부착
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
        time.sleep(0.3)  # Rate limiting

    print(f"\n  ✅ 본문 수집 완료: 성공 {success_count}건 / 실패 {fail_count}건")
    print(f"  ✅ 총 {len(all_chunks)}개 청크 생성")

    if not all_chunks:
        print("❌ 생성된 청크가 없습니다.")
        sys.exit(1)

    # Step 4 & 5: 임베딩 + FAISS 저장
    total_chunks, dimension = build_faiss_index(all_chunks)

    # 완료 통계
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    # 카테고리별 통계
    category_stats = {}
    for c in all_chunks:
        cat = c["metadata"].get("category", "기타")
        category_stats[cat] = category_stats.get(cat, 0) + 1

    print(f"\n{'=' * 60}")
    print(f"  ✅ 벡터스토어 구축 완료!")
    print(f"{'=' * 60}")
    print(f"  자치법규:  {success_count}건 (실패 {fail_count}건)")
    print(f"  총 청크:   {total_chunks}개")
    print(f"  임베딩:    {dimension}차원")
    print(f"  소요시간:  {minutes}분 {seconds}초")
    print(f"\n  카테고리별:")
    for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}개 청크")
    print(f"\n  출력 파일:")
    print(f"    {OUTPUT_DIR / 'index.faiss'}")
    print(f"    {OUTPUT_DIR / 'index.pkl'}")
    print(f"\n  다음 단계:")
    print(f"    git add backend/data/law_chatbot/")
    print(f"    git commit -m 'feat: 충주시 자치법규 벡터스토어 추가'")
    print(f"    git push")


if __name__ == "__main__":
    main()