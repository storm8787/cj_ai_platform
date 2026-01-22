import { Routes, Route, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewsViewer from './pages/NewsViewer';
import PressRelease from './pages/PressRelease';
import ElectionLaw from './pages/ElectionLaw';
import MeritReport from './pages/MeritReport';
import DataAnalysis from './pages/DataAnalysis';
import Translator from './pages/Translator';
import AddressGeocoder from './pages/AddressGeocoder';
import KakaoPromo from './pages/KakaoPromo';
import ExcelMerger from './pages/ExcelMerger';
import MeetingSummarizer from './pages/MeetingSummarizer';

// 페이지별 타이틀 매핑
const pageTitles = {
  '/': '대시보드',
  '/news': '뉴스 조회',
  '/press-release': '보도자료 생성',
  '/election-law': '선거법 챗봇',
  '/merit-report': '표창장 생성',
  '/data-analysis': 'AI 통계분석',
  '/translator': '다국어 번역',
  '/address-geocoder': '주소-좌표 변환',
  '/kakao-promo': '카카오 홍보문구',
  '/excel-merger': '엑셀 취합',
  '/meeting-summary': '회의록 요약'
};

function App() {
  const location = useLocation();

  // 페이지 이동 시 타이틀 변경
  useEffect(() => {
    const pageTitle = pageTitles[location.pathname] || '충주시 AI 플랫폼';
    document.title = `${pageTitle} - 충주시 AI 플랫폼`;
  }, [location]);

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/news" element={<NewsViewer />} />
        <Route path="/press-release" element={<PressRelease />} />
        <Route path="/election-law" element={<ElectionLaw />} />
        <Route path="/merit-report" element={<MeritReport />} />
        <Route path="/data-analysis" element={<DataAnalysis />} />
        <Route path="/translator" element={<Translator />} />
        <Route path="/address-geocoder" element={<AddressGeocoder />} />
        <Route path="/kakao-promo" element={<KakaoPromo />} />
        <Route path="/excel-merger" element={<ExcelMerger />} />
        <Route path="/meeting-summary" element={<MeetingSummarizer />} />
      </Routes>
    </Layout>
  );
}

export default App;