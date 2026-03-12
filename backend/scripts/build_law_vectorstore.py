"""
충주시 자치법규 벡터스토어 구축 스크립트 (v3)

v2 → v3 변경사항:
1. 임베딩 모델: ko-sroberta → BAAI/bge-m3 (1024차원, dense+sparse)
2. BM25 sparse 벡터도 함께 저장 (Hybrid Search용)
3. 컨텍스트 보강 청크: 법령명+조문제목을 prefix로 추가
4. 조문 제목(조제목) 추출 추가
5. 별표 제목도 청크에 포함

사용법:
  cd backend
  pip install FlagEmbedding
  python scripts/build_law_vectorstore.py --oc YOUR_OC_CODE

결과물:
  C:\\temp\\law_vectorstore\\index.faiss      (dense 벡터)
  C:\\temp\\law_vectorstore\\index.pkl         (텍스트 + 메타데이터)
  C:\\temp\\law_vectorstore\\bm25_corpus.pkl   (BM25 토큰화 코퍼스)
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

EMBEDDING_MODEL = r"C:\Users\User\Desktop\파이썬코드\rag_test\models\bge-m3"

OUTPUT_DIR = Path(r"C:\temp\law_vectorstore_v3")

MAX_CHUNK_CHARS = 1500


def _decode_response(resp) -> str:
    return resp.content.decode("utf-8")


# ─── Step 1: 충주시 자치법규 목록 수집 ────────────────
def fetch_chungju_ordinance_list(oc: str) -> list:
    all_items = []
    page = 1

    print("\n[Step 1] 충주시 자치법규 목록 수집")
    print("-" * 50)

    while True:
        params = {
            "OC": oc, "target": "ordin", "type": "XML",
            "query": "충주시", "display": 100, "page": page,
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
            mst = item.findtext("자치법규일련번호", "") or item.findtext("법령일련번호", "")
            name = item.findtext("자치법규명", "") or item.findtext("법령명한글", "")
            category = (item.findtext("자치법규종류", "")
                       or item.findtext("자치법규구분", "")
                       or item.findtext("법령구분명", ""))
            enforcement_date = item.findtext("시행일자", "")
            status = item.findtext("현행연혁코드", "")

            if not mst or not name:
                continue

            region = item.findtext("지자체기관명", "") or item.findtext("자치단체명", "")
            if region and "충주" not in region:
                continue

            all_items.append({
                "mst": mst, "name": name, "category": category,
                "enforcement_date": enforcement_date, "status": status,
            })
            items_found += 1

        print(f"  page {page}: {items_found}건 수집 (누적 {len(all_items)}건)")

        if page * 100 >= total or items_found == 0:
            break
        page += 1
        time.sleep(0.5)

    print(f"\n  ✅ 목록 수집 완료: 총 {len(all_items)}건")
    return all_items


# ─── Step 2: 본문 수집 (조문 단위 + 조제목 포함) ─────
def fetch_ordinance_articles(oc: str, mst: str) -> list:
    """자치법규 1건의 조문을 구조화하여 추출 (조제목 포함)"""
    params = {"OC": oc, "target": "ordin", "MST": mst, "type": "XML"}

    try:
        resp = requests.get(LAW_SERVICE_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    try:
        text = _decode_response(resp)
        root = ET.fromstring(text)
    except (ET.ParseError, UnicodeDecodeError):
        return []

    articles = []

    # 조문 단위 파싱
    for jo in root.iter("조문"):
        number = ""
        title = ""
        content_parts = []

        for child in jo.iter():
            tag = child.tag
            text_val = (child.text or "").strip()
            if not text_val:
                continue
            if tag in ("조문번호", "조문여부"):
                continue
            elif tag in ("조내용", "조문내용"):
                content_parts.append(text_val)
                match = re.match(r"(제\d+조(?:의\d+)?)", text_val)
                if match:
                    number = match.group(1)
            elif tag in ("조제목", "조문제목"):
                title = text_val
            elif tag in ("항내용", "호내용", "목내용"):
                content_parts.append(text_val)

        if content_parts:
            articles.append({
                "number": number,
                "title": title,
                "content": "\n".join(content_parts),
            })

    # 조문 태그 없으면 폴백
    if not articles:
        for elem in root.iter():
            tag = elem.tag
            text_val = (elem.text or "").strip()
            if not text_val:
                continue
            if any(k in tag for k in ["조문내용", "조내용"]):
                match = re.match(r"(제\d+조(?:의\d+)?)", text_val)
                number = match.group(1) if match else ""
                articles.append({"number": number, "title": "", "content": text_val})

    # 별표 추출
    for bt in root.iter("별표단위"):
        bt_title = bt.findtext("별표제목", "")
        bt_content = bt.findtext("별표내용", "").strip()
        if bt_title:
            articles.append({
                "number": bt_title,
                "title": "",
                "content": bt_content if bt_content else f"(첨부파일로 제공 - {bt_title})",
            })

    return articles


# ─── Step 3: 컨텍스트 보강 청크 생성 ─────────────────
def create_contextual_chunks(articles: list, law_name: str, ordin_meta: dict) -> list:
    """
    각 조문에 법령명+조문제목을 prefix로 추가하여 컨텍스트 보강
    v2: "제10조 (휴가) 공무원의 휴가는..."
    v3: "[충주시 지방공무원 복무 조례 > 제10조 휴가] 공무원의 휴가는..."
    """
    chunks = []

    for article in articles:
        number = article.get("number", "")
        title = article.get("title", "")
        content = article.get("content", "")

        if not content.strip():
            continue

        # 컨텍스트 prefix 생성
        if title:
            prefix = f"[{law_name} > {number} {title}]"
        elif number:
            prefix = f"[{law_name} > {number}]"
        else:
            prefix = f"[{law_name}]"

        full_text = f"{prefix}\n{content}"

        # 긴 청크 분할
        if len(full_text) <= MAX_CHUNK_CHARS:
            chunks.append({
                "content": full_text,
                "metadata": {
                    "law_name": law_name,
                    "article": number,
                    "article_title": title,
                    "category": ordin_meta.get("category", ""),
                    "enforcement_date": ordin_meta.get("enforcement_date", ""),
                    "mst": ordin_meta.get("mst", ""),
                    "region": "충주시",
                    "type": "자치법규",
                },
            })
        else:
            # 항(①②③) 단위로 분할
            sub_chunks = _split_by_paragraph(content, prefix, number)
            for sc in sub_chunks:
                chunks.append({
                    "content": sc,
                    "metadata": {
                        "law_name": law_name,
                        "article": number,
                        "article_title": title,
                        "category": ordin_meta.get("category", ""),
                        "enforcement_date": ordin_meta.get("enforcement_date", ""),
                        "mst": ordin_meta.get("mst", ""),
                        "region": "충주시",
                        "type": "자치법규",
                    },
                })

    return chunks


def _split_by_paragraph(content: str, prefix: str, article: str) -> list:
    """항(①②③) 단위로 분할"""
    sub_pattern = r"([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])"
    parts = re.split(sub_pattern, content)

    sub_chunks = []
    current = ""

    for part in parts:
        if re.match(sub_pattern, part):
            if current.strip() and len(current) > 50:
                sub_chunks.append(f"{prefix}\n{current.strip()}")
            current = part
        else:
            current += part

    if current.strip() and len(current) > 50:
        sub_chunks.append(f"{prefix}\n{current.strip()}")

    if not sub_chunks:
        # 분할 실패 시 고정 길이 분할
        for i in range(0, len(content), 1200):
            chunk = content[i:i + 1400].strip()
            if chunk and len(chunk) > 30:
                sub_chunks.append(f"{prefix}\n{chunk}")

    return sub_chunks


# ─── Step 4: bge-m3 임베딩 + BM25 인덱스 생성 ────────
def build_indices(all_chunks: list):
    print(f"\n[Step 4] bge-m3 임베딩 생성")
    print("-" * 50)
    print(f"  모델: {EMBEDDING_MODEL}")

    from FlagEmbedding import BGEM3FlagModel

    model = BGEM3FlagModel(EMBEDDING_MODEL, use_fp16=True)

    texts = [c["content"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]

    print(f"  {len(texts)}개 청크 임베딩 생성 중... (시간이 걸릴 수 있습니다)")

    # bge-m3는 dense + sparse 동시 생성
    output = model.encode(
        texts,
        batch_size=32,
        max_length=512,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,  # ColBERT은 메모리 많이 먹어서 제외
    )

    dense_embeddings = output["dense_vecs"]
    sparse_weights = output["lexical_weights"]

    dense_embeddings = np.array(dense_embeddings).astype("float32")
    # normalize for cosine similarity
    norms = np.linalg.norm(dense_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    dense_embeddings = dense_embeddings / norms

    dimension = dense_embeddings.shape[1]
    print(f"  Dense 임베딩: {dimension}차원")
    print(f"  Sparse 벡터: {len(sparse_weights)}개")

    # ── FAISS 인덱스 생성 (Dense) ──
    import faiss
    index = faiss.IndexFlatIP(dimension)
    index.add(dense_embeddings)

    # ── 저장 ──
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    faiss_path = OUTPUT_DIR / "index.faiss"
    pkl_path = OUTPUT_DIR / "index.pkl"
    bm25_path = OUTPUT_DIR / "bm25_corpus.pkl"

    faiss.write_index(index, str(faiss_path))

    with open(pkl_path, "wb") as f:
        pickle.dump({"texts": texts, "metadatas": metadatas}, f)

    # BM25용 토큰화 코퍼스 저장
    # sparse_weights는 [{token_id: weight, ...}, ...] 형태
    # 별도로 텍스트 기반 BM25도 저장 (rank_bm25 호환)
    tokenized_corpus = [_tokenize_korean(t) for t in texts]
    with open(bm25_path, "wb") as f:
        pickle.dump({
            "tokenized_corpus": tokenized_corpus,
            "sparse_weights": sparse_weights,
        }, f)

    print(f"\n[Step 5] 저장 완료")
    print(f"  FAISS:  {faiss_path} ({faiss_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  PKL:    {pkl_path} ({pkl_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  BM25:   {bm25_path} ({bm25_path.stat().st_size / 1024 / 1024:.1f} MB)")

    return len(texts), dimension


def _tokenize_korean(text: str) -> list:
    """한국어 텍스트를 단순 토큰화 (공백 + 조사 제거)"""
    # 한글, 영문, 숫자만 남기고 공백 분리
    text = re.sub(r"[^\w가-힣]", " ", text)
    tokens = text.split()
    # 1글자 제거 + 소문자
    tokens = [t.lower() for t in tokens if len(t) > 1]
    return tokens


# ─── 메인 ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="충주시 자치법규 벡터스토어 구축 (v3)")
    parser.add_argument("--oc", type=str, help="국가법령정보센터 API OC 코드")
    args = parser.parse_args()

    oc = args.oc or os.getenv("LAW_API_OC", "")
    if not oc:
        print("❌ OC 코드가 필요합니다.")
        sys.exit(1)

    print("=" * 60)
    print("  충주시 자치법규 벡터스토어 구축 (v3 - bge-m3)")
    print("=" * 60)
    print(f"  임베딩 모델: {EMBEDDING_MODEL}")
    print(f"  출력 경로:   {OUTPUT_DIR}")
    print(f"  개선사항:")
    print(f"    - bge-m3 (1024차원, dense+sparse)")
    print(f"    - BM25 Hybrid Search용 인덱스")
    print(f"    - 컨텍스트 보강 청크 (법령명+조문제목 prefix)")
    print(f"    - 별표 제목 포함")

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
        first_law = test_root.find("law")
        name = first_law.findtext("자치법규명", "") if first_law is not None else ""
        print(f"  ✅ 연결 성공 ({test_total}건{', 첫 번째: ' + name if name else ''})")
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        sys.exit(1)

    start_time = time.time()

    # Step 1: 목록 수집
    ordinances = fetch_chungju_ordinance_list(oc)
    if not ordinances:
        print("❌ 수집된 자치법규가 없습니다.")
        sys.exit(1)

    # Step 2 & 3: 본문 수집 + 컨텍스트 보강 청크 생성
    print(f"\n[Step 2-3] 본문 수집 + 컨텍스트 보강 청크 생성")
    print("-" * 50)

    all_chunks = []
    success_count = 0
    fail_count = 0
    empty_count = 0
    table_count = 0

    for i, ordin in enumerate(ordinances):
        name = ordin["name"]
        mst = ordin["mst"]

        if (i + 1) % 50 == 0 or i == 0:
            print(f"  ({i + 1}/{len(ordinances)}) {name[:30]}...")

        articles = fetch_ordinance_articles(oc, mst)
        if not articles:
            fail_count += 1
            continue

        # 별표 개수 카운트
        for a in articles:
            if a.get("number", "").startswith("[별표"):
                table_count += 1

        chunks = create_contextual_chunks(articles, name, ordin)
        if not chunks:
            empty_count += 1
            continue

        all_chunks.extend(chunks)
        success_count += 1
        time.sleep(0.3)

    print(f"\n  ✅ 본문 수집 완료:")
    print(f"     성공 {success_count}건 / 실패 {fail_count}건 / 빈 본문 {empty_count}건")
    print(f"     별표/서식 {table_count}건 포함")
    print(f"     총 {len(all_chunks)}개 청크 생성")

    # 샘플 출력
    if all_chunks:
        print(f"\n  --- 샘플 청크 (컨텍스트 보강 확인) ---")
        for c in all_chunks[:3]:
            meta = c["metadata"]
            print(f"  [{meta['law_name']}] {meta['article']} {meta.get('article_title', '')}")
            print(f"    {c['content'][:120]}...")
            print()

    if not all_chunks:
        print("❌ 생성된 청크가 없습니다.")
        sys.exit(1)

    # Step 4 & 5: bge-m3 임베딩 + BM25
    total_chunks, dimension = build_indices(all_chunks)

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    category_stats = {}
    for c in all_chunks:
        cat = c["metadata"].get("category", "기타")
        category_stats[cat] = category_stats.get(cat, 0) + 1

    print(f"\n{'=' * 60}")
    print(f"  ✅ 벡터스토어 구축 완료! (v3 - bge-m3)")
    print(f"{'=' * 60}")
    print(f"  자치법규:  {success_count}건")
    print(f"  별표/서식: {table_count}건")
    print(f"  총 청크:   {total_chunks}개")
    print(f"  임베딩:    {dimension}차원 (bge-m3)")
    print(f"  BM25:      토큰화 코퍼스 저장")
    print(f"  소요시간:  {minutes}분 {seconds}초")
    print(f"\n  카테고리별:")
    for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}개 청크")
    print(f"\n  출력 파일:")
    print(f"    {OUTPUT_DIR / 'index.faiss'}")
    print(f"    {OUTPUT_DIR / 'index.pkl'}")
    print(f"    {OUTPUT_DIR / 'bm25_corpus.pkl'}")
    print(f"\n  ⚠️ 구축 완료 후:")
    print(f"    1. {OUTPUT_DIR} 파일을 backend/data/law_chatbot/vectorstores/에 복사")
    print(f"    2. law_chatbot.py에서 EMBEDDING_MODEL을 bge-m3 경로로 변경")
    print(f"    3. GitHub 푸시 + Azure 배포")


if __name__ == "__main__":
    main()