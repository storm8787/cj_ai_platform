import os
from typing import Optional, Tuple, List
import pandas as pd
import numpy as np
import faiss
import pickle
from pathlib import Path

from utils.openai_client import get_openai_client


class PressReleaseService:
    def __init__(self):
        self.client = get_openai_client()
        self.vectorstore_path = "data/press_release/vectorstore"
        self.index = None
        self.documents = []
        self.texts = []
        
        # 벡터스토어 로드
        self._load_vectorstore()
    
    def _load_vectorstore(self):
        """벡터스토어 로드"""
        faiss_file = Path(self.vectorstore_path) / "press_release_faiss.index"
        metadata_file = Path(self.vectorstore_path) / "documents_metadata.pkl"
        
        if faiss_file.exists() and metadata_file.exists():
            try:
                # FAISS 인덱스 로드
                self.index = faiss.read_index(str(faiss_file))
                
                # 메타데이터 로드
                with open(metadata_file, "rb") as f:
                    metadata = pickle.load(f)
                
                # 문서 데이터 추출
                raw_docs = metadata.get("documents", [])
                for doc in raw_docs:
                    if isinstance(doc, dict):
                        doc_content = doc.get("page_content", "")
                    elif hasattr(doc, 'page_content'):
                        doc_content = doc.page_content
                    else:
                        doc_content = str(doc)
                    
                    self.documents.append(doc)
                    self.texts.append(doc_content)
                
                print(f"✅ 벡터스토어 로드 완료: {len(self.documents)}개 문서")
            except Exception as e:
                print(f"⚠️ 벡터스토어 로드 실패: {e}")
                self.index = None
        else:
            print("⚠️ 벡터스토어 파일이 없습니다.")
    
    def _find_similar_docs_with_details(self, query: str, top_k: int = 3) -> Tuple[List[str], List[dict]]:
        """유사 문서 검색 + 상세 정보 반환"""
        if self.index is None or not self.documents:
            return [], []
        
        try:
            from sentence_transformers import SentenceTransformer
            
            # 로컬 모델 경로 사용
            model_path = r"C:\Users\User\Desktop\파이썬코드\rag_test\models\ko-sroberta-multitask"
            
            # 임베딩 모델 로드
            model = SentenceTransformer(model_path)
            
            # 쿼리 임베딩
            query_embedding = model.encode([query], normalize_embeddings=True)
            
            # FAISS 검색
            distances, indices = self.index.search(query_embedding.astype('float32'), top_k)
            
            selected_docs = []
            references = []
            
            for i, (idx, score) in enumerate(zip(indices[0], distances[0])):
                if idx < len(self.texts):
                    doc_content = self.texts[idx]
                    selected_docs.append(doc_content)
                    
                    ref_info = {
                        "순번": i + 1,
                        "유사도점수": f"{float(score):.4f}",
                        "문서ID": f"AI_벡터검색_{idx}",
                        "내용미리보기": doc_content[:100] + "..." if len(doc_content) > 100 else doc_content,
                        "전체내용": doc_content
                    }
                    references.append(ref_info)
            
            return selected_docs, references
        
        except Exception as e:
            print(f"AI 검색 실패: {e}, TF-IDF 백업 사용")
            return self._find_similar_docs_tfidf(query, top_k)
    
    def _find_similar_docs_tfidf(self, query: str, top_k: int = 3) -> Tuple[List[str], List[dict]]:
        """TF-IDF 백업 검색"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            if not self.texts:
                return [], []
            
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(self.texts)
            query_vec = vectorizer.transform([query])
            similarity_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
            top_indices = similarity_scores.argsort()[::-1][:top_k]
            
            selected_docs = []
            references = []
            
            for i, idx in enumerate(top_indices):
                doc_content = self.texts[idx]
                selected_docs.append(doc_content)
                
                ref_info = {
                    "순번": i + 1,
                    "유사도점수": f"{similarity_scores[idx]:.4f}",
                    "문서ID": f"TF-IDF_문서_{idx}",
                    "내용미리보기": doc_content[:100] + "..." if len(doc_content) > 100 else doc_content,
                    "전체내용": doc_content
                }
                references.append(ref_info)
            
            return selected_docs, references
        
        except Exception as e:
            print(f"TF-IDF 검색 실패: {e}")
            return [], []
    
    async def generate_press_release_with_references(
        self,
        title: str,
        department: str,
        manager: str,
        paragraph_count: str,
        length: str,
        key_points: str,
        additional_request: str
    ) -> Tuple[str, List[dict]]:
        """보도자료 생성 + 참조 문서 정보 반환"""
        
        # 1. 유사 문서 검색
        similar_docs, references = self._find_similar_docs_with_details(title, top_k=3)
        
        # 2. 프롬프트 구성
        system_prompt = "너는 지방정부 보도자료 작성 전문가야. 아래 유사 사례를 참고해, 행정기관 스타일로 공공 보도자료를 작성해줘."
        
        examples_combined = "\n\n---\n\n".join(similar_docs) if similar_docs else "참고 자료 없음"
        
        # 내용 포인트 파싱
        points_list = [line.strip() for line in key_points.strip().split("\n") if line.strip()]
        joined_points = "\n- ".join(points_list)
        
        # 길이 지시
        length_guide = {
            "짧게": 600,
            "중간": 800,
            "길게": 1000
        }.get(length, 800)
        
        # 문단 지시
        paragraph_guide = {
            "4개이상": "전체 글은 4개 이상의 문단으로 구성해주세요.\n",
            "3개": "전체 글은 3개 문단으로 구성해주세요.\n",
            "2개": "전체 글은 2개 문단으로 구성해주세요.\n",
            "1개": "전체 글은 1개 문단으로 구성해주세요.\n"
        }.get(paragraph_count, "")
        
        # 추가 지시사항
        additional_instructions = (
            f"보도자료에는 상단의 보도일자, 담당자 정보, 연락처는 포함하지 말고 본문만 작성해주세요.\n"
            f"담당자 인용문이 나올 경우, 담당자 이름은 '{manager}'이고, 직책은 '{department}장'으로 표기해주세요.\n"
            f"담당자 인용문이 나올 경우, '{manager}' 한칸띄고 '{department}장'으로 표기해주세요. ex: 김태균 자치행정과장\n"
            f"전체 문체는 보도자료 스타일의 간접화법을 사용해주세요. 예: '~했다', '~라고 밝혔다' 등.\n"
            f"{paragraph_guide}"
            f"보도자료는 반드시 '[제목] 본문제목'으로 시작한 후, 한 줄 아래에 부제목 형태의 요약 문장을 넣어주세요. 부제목은 '-' 기호로 시작하세요.\n"
            f"전체 보도자료 분량은 약 {length_guide}자 내외로 작성해주세요. 필요 시 최대 토큰 수를 늘려도 괜찮습니다.\n"
            f"전체 보도자료는 반드시 {length_guide}자 보다는 길게(+300가능) 작성해주세요."
        )
        
        user_query_prompt = (
            f"입력한 제목 후보: {title}\n\n"
            f"아래 내용 포인트를 반영하여 보도자료에 어울리는 제목을 새로 작성하고, "
            f"그 제목을 '[제목]'에 반영해줘. 입력한 제목은 참고만 하고 그대로 쓰지 않아도 돼.\n\n"
            f"내용 포인트:\n- {joined_points}\n\n"
            f"요청사항:\n- {additional_request}\n\n"
            f"{additional_instructions}"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""아래는 참고용 보도자료 예시입니다:

{examples_combined}

위 스타일을 참고하여 아래 요청사항에 맞는 새로운 보도자료를 작성해줘:

{user_query_prompt}
"""}
        ]
        
        # 3. GPT 호출
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.5,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        
        return content, references
    
    async def analyze_reference_data(self, df: pd.DataFrame) -> str:
        """참고자료 데이터 분석"""
        
        # 기본 통계 생성
        summary = f"데이터 요약:\n"
        summary += f"- 총 행 수: {len(df)}\n"
        summary += f"- 총 열 수: {len(df.columns)}\n"
        summary += f"- 컬럼: {', '.join(df.columns.tolist())}\n\n"
        
        # 숫자 컬럼 통계
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            summary += "주요 통계:\n"
            for col in numeric_cols:
                summary += f"- {col}: 평균 {df[col].mean():.2f}, 최대 {df[col].max():.2f}\n"
        
        # GPT로 인사이트 생성
        prompt = f"""다음 데이터 분석 결과를 바탕으로 보도자료에 활용할 수 있는 인사이트를 3가지 제시해주세요:

{summary}

데이터 샘플:
{df.head().to_string()}

인사이트:"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1000
        )
        
        return summary + "\n" + response.choices[0].message.content