import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import NewsViewer from './pages/NewsViewer';
import PressRelease from './pages/PressRelease';
import MeritReport from './pages/MeritReport';
import DataAnalysis from './pages/DataAnalysis';
import Translator from './pages/Translator';
import ElectionLaw from './pages/ElectionLaw';
import MeetingSummarizer from './pages/MeetingSummarizer';
import KakaoPromo from './pages/KakaoPromo';
import ReportWriter from './pages/ReportWriter';
import AddressGeocoder from './pages/AddressGeocoder';
import ExcelMerger from './pages/ExcelMerger';
import About from './pages/About';
import NotFound from './pages/NotFound';

// 보호된 라우트 컴포넌트
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  // 로딩 중일 때 스피너 표시
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-400">로딩 중...</p>
        </div>
      </div>
    );
  }

  // 인증 안 되면 로그인 페이지로
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

// 이미 로그인한 사용자는 메인으로
function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function AppRoutes() {
  return (
    <Routes>
      {/* 로그인 페이지 (비인증 사용자만) */}
      <Route 
        path="/login" 
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        } 
      />

      {/* 보호된 라우트들 (인증 필요) */}
      <Route 
        path="/*" 
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/news" element={<NewsViewer />} />
                <Route path="/press-release" element={<PressRelease />} />
                <Route path="/merit-report" element={<MeritReport />} />
                <Route path="/data-analysis" element={<DataAnalysis />} />
                <Route path="/translator" element={<Translator />} />
                <Route path="/election-law" element={<ElectionLaw />} />
                <Route path="/meeting-summary" element={<MeetingSummarizer />} />
                <Route path="/kakao-promo" element={<KakaoPromo />} />
                <Route path="/report-writer" element={<ReportWriter />} />
                <Route path="/address-geocoder" element={<AddressGeocoder />} />
                <Route path="/excel-merger" element={<ExcelMerger />} />
                <Route path="/about" element={<About />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        } 
      />
    </Routes>
  );
}

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
}