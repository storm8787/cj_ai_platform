import axios from 'axios';

// API 베이스 URL
const API_BASE_URL = import.meta.env.VITE_API_URL
  || 'https://cj-ai-backend.ashysky-a846c5bf.koreacentral.azurecontainerapps.io';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
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
    responseType: 'arraybuffer',
    timeout: 300000,
  }),
};

// ===== 주소-좌표 변환기 API =====
export const addressGeocoderApi = {
  addressToCoord: (data) => api.post('/api/geocoder/address-to-coord', data),
  coordToAddress: (data) => api.post('/api/geocoder/coord-to-address', data),

  fileAddressToCoord: (formData) => api.post('/api/geocoder/file/address-to-coord', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'arraybuffer',
    timeout: 180000,
  }),
  fileCoordToAddress: (formData) => api.post('/api/geocoder/file/coord-to-address', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'arraybuffer',
    timeout: 180000,
  }),

  downloadTemplate: (type) => api.get(`/api/geocoder/template/${type}`, {
    responseType: 'arraybuffer',
  }),
};

// ===== 카카오 홍보문구 생성기 API =====
export const kakaoPromoApi = {
  getCategories: () => api.get('/api/kakao-promo/categories'),
  generate: (data) => api.post('/api/kakao-promo/generate', data),
  generateWithImage: (formData) => api.post('/api/kakao-promo/generate-with-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  }),
};

// ===== 엑셀 취합기 API =====
export const excelMergerApi = {
  merge: (formData) => api.post('/api/excel-merger/merge', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'arraybuffer',
    timeout: 180000,
  }),
  preview: (formData) => api.post('/api/excel-merger/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
};

// ===== 회의요약기 API =====
export const meetingSummarizerApi = {
  getModes: () => api.get('/api/meeting/modes'),
  getSystemInfo: () => api.get('/api/meeting/system-info'),
  summarize: (data) => api.post('/api/meeting/summarize', data, {
    timeout: 180000,
  }),
  summarizeFile: (formData) => api.post('/api/meeting/summarize-file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
  }),
};

// ===== 재난상황 대시보드 API =====
export const disasterApi = {
  upload: (formData) => api.post('/api/disaster/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  analyze: (uploadId) => api.post(`/api/disaster/analyze/${uploadId}`),
  getUploadSummary: (uploadId) => api.get(`/api/disaster/upload/${uploadId}/summary`),
  getIncidents: (params) => api.get('/api/disaster/incidents', { params }),
  getIncidentDetail: (incidentId) => api.get(`/api/disaster/incidents/${incidentId}`),
  getOverview: (uploadId) => api.get('/api/disaster/dashboard/overview', {
    params: { upload_id: uploadId }
  }),
  generateDailyReport: (data) => api.post('/api/disaster/reports/daily/generate', data),
  getReports: (uploadId) => api.get('/api/disaster/reports', {
    params: { upload_id: uploadId }
  }),
};

export default api;