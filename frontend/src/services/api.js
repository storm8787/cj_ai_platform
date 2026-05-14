import axios from 'axios';

// API 베이스 URL
const API_BASE_URL = import.meta.env.VITE_API_URL
  || 'https://cj-ai-backend.ashysky-a846c5bf.koreacentral.azurecontainerapps.io';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 기본 120초 타임아웃
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터 — Authorization 헤더 자동 주입
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token && !config.headers['Authorization']) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// 응답 인터셉터 — 에러 처리
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // arraybuffer 응답에서 JSON 에러 디코딩 (번역기 등 파일 다운로드 엔드포인트 대응)
    if (error.response?.data instanceof ArrayBuffer) {
      try {
        const decoded = JSON.parse(new TextDecoder().decode(error.response.data));
        error.response.data = decoded;
      } catch (_) {
        // 디코딩 실패 시 원본 유지
      }
    }

    const status = error.response?.status;
    const detail = error.response?.data?.detail;

    // 429 — 일일 사용량 초과
    if (status === 429) {
      const msg = detail ||
        '일일 AI 사용 한도에 도달했습니다. 일반 사용자는 하루 최대 50회까지 AI 기능을 사용할 수 있습니다. 내일 다시 이용해 주세요.';
      // 전역 커스텀 이벤트로 알림 (각 페이지의 catch에서도 detail로 접근 가능)
      window.dispatchEvent(new CustomEvent('api:quota-exceeded', { detail: { message: msg } }));
    }

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
    timeout: 300000, // 5분
  }),
};

// ===== 주소-좌표 변환기 API =====
export const addressGeocoderApi = {
  // 단일 변환
  addressToCoord: (data) => api.post('/api/geocoder/address-to-coord', data),
  coordToAddress: (data) => api.post('/api/geocoder/coord-to-address', data),

  // 파일 변환
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

  // 템플릿 다운로드
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

// ===== 공공데이터 검증기 API =====
export const dataValidatorApi = {
  getStandards: (params) => api.get('/api/data-validator/standards', { params }),
  getStandardDetail: (code) => api.get(`/api/data-validator/standards/${code}`),
  validate: (formData) => api.post('/api/data-validator/validate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  }),
  validateCustom: (data) => api.post('/api/data-validator/validate-custom', data, {
    timeout: 300000,
  }),
};

// ===== 출장보고 생성기 API =====
export const tripReportApi = {
  getReportTypes: () => api.get('/api/trip-report/report-types'),
  analyzeImages: (formData) => api.post('/api/trip-report/analyze-images', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  }),
  generateReport: (formData) => api.post('/api/trip-report/generate-report', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  }),
};

// ===== 법령·자치법규 챗봇 API =====
export const lawChatbotApi = {
  ask: (data) => api.post('/api/law-chatbot/ask', data, {
    timeout: 180000,
  }),
  search: (data) => api.post('/api/law-chatbot/search', data, {
    timeout: 180000,
  }),
  getStatus: () => api.get('/api/law-chatbot/status'),
  getCategories: () => api.get('/api/law-chatbot/categories'),
};

// ===== 사업 타임라인 API =====
export const timelinePlannerApi = {
  suggest: (data) => api.post('/api/timeline/suggest', data, {
    timeout: 180000,
  }),
  getDetailTasks: (data) => api.post('/api/timeline/detail-tasks', data, {
    timeout: 180000,
  }),
  exportTimeline: (data) => api.post('/api/timeline/export', data, {
    responseType: 'arraybuffer',
    timeout: 300000,
  }),
  getProjectTypes: () => api.get('/api/timeline/project-types'),
  getContractTypes: () => api.get('/api/timeline/contract-types'),
  getCategories: () => api.get('/api/timeline/categories'),
  getStatus: () => api.get('/api/timeline/status'),
};

// ===== 프롬프트 관리자 API =====
export const promptManagerApi = {
  getPrompts: (params) => api.get('/api/prompts', { params }),
  getPrompt: (id) => api.get(`/api/prompts/${id}`),
  createPrompt: (data) => api.post('/api/prompts', data),
  updatePrompt: (id, data) => api.put(`/api/prompts/${id}`, data),
  deletePrompt: (id) => api.delete(`/api/prompts/${id}`),
  refreshCache: () => api.post('/api/prompts/refresh-cache'),
  getFeatures: () => api.get('/api/prompts/meta/features'),
};

// ===== HWPX 변환기 API =====
export const hwpxConverterApi = {
  convert: (formData) => api.post('/api/hwpx-converter/convert', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  }),
  convertDownload: (formData) => api.post('/api/hwpx-converter/convert-download', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'arraybuffer',
    timeout: 300000,
  }),
  getStatus: () => api.get('/api/hwpx-converter/status'),
};

// ===== 인증 API =====
export const authApi = {
  signup: (data) => api.post('/api/auth/signup', data),
  verifyOtp: (data) => api.post('/api/auth/verify-otp', data),
  resendOtp: (data) => api.post('/api/auth/resend-otp', data),
  login: (data) => api.post('/api/auth/login', data),
  logout: () => api.post('/api/auth/logout'),
  verify: () => api.get('/api/auth/verify'),
  me: () => api.get('/api/auth/me'),
  refresh: () => api.post('/api/auth/refresh'),
};

// ===== 게시판 API =====
export const boardApi = {
  getList: (boardType, params) => api.get(`/api/board/list/${boardType}`, { params }),
  getDetail: (boardId) => api.get(`/api/board/detail/${boardId}`),
  create: (data) => api.post('/api/board/create', data),
  createWithFile: (formData) => api.post('/api/board/create-with-file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
  }),
  update: (boardId, data) => api.put(`/api/board/update/${boardId}`, data),
  delete: (boardId) => api.delete(`/api/board/delete/${boardId}`),
  answer: (boardId, data) => api.post(`/api/board/answer/${boardId}`, data),
  deleteAnswer: (answerId) => api.delete(`/api/board/answer/${answerId}`),
};

// ===== 재난상황 대시보드 API =====
export const disasterApi = {
  upload: (formData) => api.post('/api/disaster/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
  }),
  getUploads: () => api.get('/api/disaster/uploads'),
  analyze: (uploadId) => api.post(`/api/disaster/analyze/${uploadId}`, {}, {
    timeout: 300000,
  }),
  getUploadSummary: (uploadId) => api.get(`/api/disaster/upload/${uploadId}/summary`),
  getIncidents: (params) => api.get('/api/disaster/incidents', { params }),
  getIncidentDetail: (incidentId) => api.get(`/api/disaster/incidents/${incidentId}`),
  getOverview: (uploadId) => api.get('/api/disaster/dashboard/overview', {
    params: { upload_id: uploadId }
  }),
  generateDailyReport: (data) => api.post('/api/disaster/reports/daily/generate', data, {
    timeout: 180000,
  }),
  getReports: (uploadId) => api.get('/api/disaster/reports', {
    params: { upload_id: uploadId }
  }),
};

export default api;