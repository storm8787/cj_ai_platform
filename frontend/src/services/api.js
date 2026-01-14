import axios from 'axios';

// Azure Container Apps 백엔드 URL
// 로컬 개발: http://localhost:8000
// 프로덕션: Azure Container Apps URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cj-ai-backend.ashysky-a846c5bf.koreacentral.azurecontainerapps.io';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60초 타임아웃 (AI 응답 대기)
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// 응답 인터셉터
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ===== 헬스 체크 =====
export const checkHealth = () => api.get('/api/health');

// ===== 보도자료 API =====
export const pressReleaseApi = {
  // 유사 문서 검색
  searchSimilar: (data) => api.post('/api/press-release/search-similar', data),
  
  // 보도자료 생성
  generate: (data) => api.post('/api/press-release/generate', data),
  
  // 벡터스토어 상태
  getStatus: () => api.get('/api/press-release/status'),
};

// ===== 선거법 챗봇 API =====
export const electionLawApi = {
  // 질문 답변
  askQuestion: (data) => api.post('/api/election-law/ask', data),
  
  // 검색 대상 목록
  getTargets: () => api.get('/api/election-law/targets'),
  
  // 벡터스토어 상태
  getStatus: () => api.get('/api/election-law/status'),
};

// ===== 뉴스 API =====
export const newsApi = {
  // /api/news → /api/news/list 로 수정
  getList: () => api.get('/api/news/list'),
  
  refresh: () => api.post('/api/news/refresh'),
  
  summarize: (data) => api.post('/api/news/summarize'),
};

export default api;
