"""벡터스토어 검색 서비스"""
import os
import pickle
from typing import List, Dict
import numpy as np

from config import settings

# 지연 로딩을 위한 전역 변수
_faiss_index = None
_embedding_model = None
_metadata = None

# 선거법 벡터스토어
_election_indexes = {}
_election_metadata = {}


def get_embedding_model():
    """임베딩 모델 로드 (싱글톤)"""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        print(f"✅ 임베딩 모델 로드: {settings.EMBEDDING_MODEL}")
    return _embedding_model


class VectorStoreService:
    """벡터스토어 검색 서비스"""

    def __init__(self):
        self.press_release_loaded = False
        self.election_law_loaded = False

    def _load_press_release_vectorstore(self):
        """보도자료 벡터스토어 로드"""
        global _faiss_index, _metadata

        if _faiss_index is not None:
            return True

        try:
            import faiss

            index_path = os.path.join(settings.VECTORSTORE_PATH, "press_release_faiss.index")
            metadata_path = os.path.join(settings.VECTORSTORE_PATH, "documents_metadata.pkl")

            if not os.path.exists(index_path):
                print(f"⚠️ 인덱스 파일 없음: {index_path}")
                return False

            _faiss_index = faiss.read_index(index_path)

            with open(metadata_path, "rb") as f:
                loaded = pickle.load(f)

            # ✅ pkl이 dict인 경우: 대부분 {"documents":[...], ...} 형태
            if isinstance(loaded, dict):
                if "documents" in loaded and isinstance(loaded["documents"], list):
                    _metadata = loaded["documents"]
                else:
                    # 혹시 dict가 doc_id -> doc 형태면 values로 리스트화
                    _metadata = list(loaded.values())
            elif isinstance(loaded, list):
                _metadata = loaded
            else:
                _metadata = []

            # (권장) 인덱스 개수랑 메타 길이 불일치 로그
            if hasattr(_faiss_index, "ntotal") and len(_metadata) != _faiss_index.ntotal:
                print(f"⚠️ 메타데이터 길이({len(_metadata)})와 인덱스 ntotal({_faiss_index.ntotal}) 불일치")

            print(f"✅ 보도자료 벡터스토어 로드: {_faiss_index.ntotal}개 문서")
            self.press_release_loaded = True
            return True

        except Exception as e:
            print(f"❌ 보도자료 벡터스토어 로드 실패: {e}")
            return False

    async def search_press_release(self, query: str, top_k: int = 3) -> List[Dict]:
        """보도자료 유사 문서 검색"""
        if not self._load_press_release_vectorstore():
            return []

        try:
            import faiss  # ✅ 여기서 사용 (정규화)

            model = get_embedding_model()
            query_embedding = model.encode([query])[0]
            query_embedding = np.array([query_embedding]).astype("float32")

            # ✅ 코사인처럼 쓰기 위한 정규화
            faiss.normalize_L2(query_embedding)

            # FAISS 검색 (IndexFlatIP면 distances가 곧 cosine score에 가까움)
            distances, indices = _faiss_index.search(query_embedding, top_k)

            results = []
            for score, idx in zip(distances[0], indices[0]):
                if idx < len(_metadata):
                    doc = _metadata[idx]
                    similarity = float(score)  # ✅ dist 환산 제거, score 그대로 사용

                    content = doc.get("page_content", "") or doc.get("content", "")
                    title = doc.get("title", "") or doc.get("metadata", {}).get("title", "")

                    if content:
                        results.append({
                            "title": title,
                            "content": content,
                            "similarity": similarity,
                            "metadata": doc.get("metadata", {})
                        })

            return results

        except Exception as e:
            print(f"❌ 보도자료 검색 오류: {e}")
            return []

    def get_press_release_status(self) -> Dict:
        """보도자료 벡터스토어 상태"""
        self._load_press_release_vectorstore()
        return {
            "loaded": self.press_release_loaded,
            "document_count": _faiss_index.ntotal if _faiss_index else 0,
            "metadata_count": len(_metadata) if _metadata else 0,
            "path": settings.VECTORSTORE_PATH
        }
    
    async def search_election_law(self, query: str, target: str = "all", top_k: int = 5) -> List[Dict]:
        """선거법 문서 검색 (코사인처럼: normalize + score 그대로)"""
        if not self._load_election_law_vectorstore(target):
            return []

        try:
            import faiss

            model = get_embedding_model()
            query_embedding = model.encode([query])[0]
            query_embedding = np.array([query_embedding]).astype("float32")

            faiss.normalize_L2(query_embedding)

            index = _election_indexes[target]
            metadata = _election_metadata[target]

            distances, indices = index.search(query_embedding, top_k)

            results = []
            for score, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(metadata):
                    continue

                doc = metadata[idx]
                similarity = float(score)  # ✅ IP score 그대로

                content = doc.get("page_content", "") or doc.get("content", "")
                doc_type = doc.get("type") or doc.get("metadata", {}).get("doc_type") or target

                # (선택) 최소 점수 컷은 운영하면서 조정
                if content and similarity >= 0.35:
                    results.append({
                        "content": content,
                        "similarity": similarity,
                        "type": doc_type,
                        "metadata": doc.get("metadata", {})
                    })

            return results

        except Exception as e:
            print(f"❌ 선거법 검색 오류: {e}")
            return []

    def get_press_release_status(self) -> Dict:
        """보도자료 벡터스토어 상태"""
        self._load_press_release_vectorstore()
        return {
            "loaded": self.press_release_loaded,
            "document_count": _faiss_index.ntotal if _faiss_index else 0,
            "metadata_count": len(_metadata) if _metadata else 0,
            "path": settings.VECTORSTORE_PATH
        }

    def get_election_law_status(self) -> Dict:
        """선거법 벡터스토어 상태"""
        status = {
            "loaded": self.election_law_loaded,
            "indexes": {},
            "path": settings.ELECTION_VECTORSTORE_PATH
        }

        for target in ["all", "law", "panli", "written", "internet", "guidance"]:
            self._load_election_law_vectorstore(target)
            if target in _election_indexes:
                status["indexes"][target] = _election_indexes[target].ntotal

        return status