import axios from 'axios';

// API 베이스 URL
const API_BASE_URL = import.meta.env.VITE_API_URL 
  || 'https://cj-ai-backend.ashysky-a846c5bf.koreacentral.azurecontainerapps.io';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120초 타임아웃 (번역 등 긴 작업용)
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

// ===== 뉴스 API =====
export const newsApi = {
  getList: () => api.get('/api/news/list'),
  refresh: () => api.post('/api/news/refresh'),
  summarize: (data) => api.post('/api/news/summarize', data),
};

// ===== 보도자료 API =====
export const pressReleaseApi = {
  searchSimilar: (data) => api.post('/api/press-release/search-similar', data),
  generate: (data) => api.post('/api/press-release/generate', data),
  getStatus: () => api.get('/api/press-release/status'),
};

// ===== 선거법 챗봇 API =====
export const electionLawApi = {
  askQuestion: (data) => api.post('/api/election-law/ask', data),
  getTargets: () => api.get('/api/election-law/targets'),
  getStatus: () => api.get('/api/election-law/status'),
};

// ===== 공적조서 생성기 API =====
export const meritReportApi = {
  generate: (data) => api.post('/api/merit-report/generate', data),
};

// ===== AI 통계분석 챗봇 API =====
export const dataAnalysisApi = {
  upload: (formData) => api.post('/api/data-analysis/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  analyze: (data) => api.post('/api/data-analysis/analyze', data),
  deleteFile: (fileId) => api.delete(`/api/data-analysis/file/${fileId}`),
};

// ===== 다국어 번역기 API =====
export const translatorApi = {
  getLanguages: () => api.get('/api/translator/languages'),
  translate: (formData) => api.post('/api/translator/translate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'arraybuffer', // 파일 다운로드용
    timeout: 300000, // 5분 타임아웃
  }),
};

export default api;
