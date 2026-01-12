"""벡터스토어 검색 서비스"""
import os
import pickle
from typing import List, Dict, Optional
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
                _metadata = pickle.load(f)
            
            print(f"✅ 보도자료 벡터스토어 로드: {_faiss_index.ntotal}개 문서")
            self.press_release_loaded = True
            return True
            
        except Exception as e:
            print(f"❌ 보도자료 벡터스토어 로드 실패: {e}")
            return False
    
    def _load_election_law_vectorstore(self, target: str = "all"):
        """선거법 벡터스토어 로드"""
        global _election_indexes, _election_metadata
        
        if target in _election_indexes:
            return True
        
        try:
            import faiss
            
            # 파일명 매핑
            file_map = {
                "all": ("election_law_faiss.index", "documents_metadata.pkl"),
                "law": ("election_law_law_faiss.index", "documents_metadata_law.pkl"),
                "panli": ("election_law_panli_faiss.index", "documents_metadata_panli.pkl"),
                "written": ("election_law_written_faiss.index", "documents_metadata_written.pkl"),
                "internet": ("election_law_internet_faiss.index", "documents_metadata_internet.pkl"),
                "guidance": ("election_law_guidance_faiss.index", "documents_metadata_guidance.pkl"),
            }
            
            if target not in file_map:
                target = "all"
            
            index_file, metadata_file = file_map[target]
            index_path = os.path.join(settings.ELECTION_VECTORSTORE_PATH, index_file)
            metadata_path = os.path.join(settings.ELECTION_VECTORSTORE_PATH, metadata_file)
            
            if not os.path.exists(index_path):
                print(f"⚠️ 인덱스 파일 없음: {index_path}")
                return False
            
            _election_indexes[target] = faiss.read_index(index_path)
            
            with open(metadata_path, "rb") as f:
                _election_metadata[target] = pickle.load(f)
            
            print(f"✅ 선거법 벡터스토어 로드 ({target}): {_election_indexes[target].ntotal}개 문서")
            self.election_law_loaded = True
            return True
            
        except Exception as e:
            print(f"❌ 선거법 벡터스토어 로드 실패 ({target}): {e}")
            return False
    
    async def search_press_release(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict]:
        """보도자료 유사 문서 검색"""
        if not self._load_press_release_vectorstore():
            return []
        
        try:
            model = get_embedding_model()
            query_embedding = model.encode([query])[0]
            query_embedding = np.array([query_embedding]).astype("float32")
            
            # FAISS 검색
            distances, indices = _faiss_index.search(query_embedding, top_k)
            
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(_metadata):
                    doc = _metadata[idx]
                    similarity = 1 / (1 + dist)  # 거리를 유사도로 변환
                    results.append({
                        "title": doc.get("title", ""),
                        "content": doc.get("content", ""),
                        "similarity": float(similarity),
                        "metadata": doc.get("metadata", {})
                    })
            
            return results
            
        except Exception as e:
            print(f"❌ 보도자료 검색 오류: {e}")
            return []
    
    async def search_election_law(
        self,
        query: str,
        target: str = "all",
        top_k: int = 5
    ) -> List[Dict]:
        """선거법 문서 검색"""
        if not self._load_election_law_vectorstore(target):
            return []
        
        try:
            model = get_embedding_model()
            query_embedding = model.encode([query])[0]
            query_embedding = np.array([query_embedding]).astype("float32")
            
            # FAISS 검색
            index = _election_indexes[target]
            metadata = _election_metadata[target]
            
            distances, indices = index.search(query_embedding, top_k)
            
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(metadata):
                    doc = metadata[idx]
                    similarity = 1 / (1 + dist)
                    
                    # 최소 유사도 필터링
                    if similarity >= 0.35:
                        results.append({
                            "content": doc.get("content", ""),
                            "similarity": float(similarity),
                            "type": doc.get("type", target),
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
