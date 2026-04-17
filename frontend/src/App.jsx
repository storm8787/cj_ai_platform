import { Routes, Route, Navigate } from 'react-router-dom';
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

import NoticeBoard from './pages/NoticeBoard';
import ArchiveBoard from './pages/ArchiveBoard';
import QnaBoard from './pages/QnaBoard';
import BoardDetail from './pages/BoardDetail';
import BoardWrite from './pages/BoardWrite';
import BoardEdit from './pages/BoardEdit';
import DataValidator from './pages/DataValidator';
import TripReport from './pages/TripReport';
import LawChatbot from './pages/LawChatbot';
import TimelinePlanner from "./pages/TimelinePlanner";
import PromptManager from './pages/PromptManager';
import HwpxConverter from './pages/HwpxConverter';

// Disaster Dashboard Pages
import DisasterUpload from './pages/DisasterUpload';
import DisasterDashboard from './pages/DisasterDashboard';
import DisasterIncidents from './pages/DisasterIncidents';
import DisasterDailyReport from './pages/DisasterDailyReport';


// 보호된 라우트 컴포넌트
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

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
        path="/"
        element={
          <ProtectedRoute>
            <Layout><Dashboard /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/news"
        element={
          <ProtectedRoute>
            <Layout><NewsViewer /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/press-release"
        element={
          <ProtectedRoute>
            <Layout><PressRelease /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/merit-report"
        element={
          <ProtectedRoute>
            <Layout><MeritReport /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/data-analysis"
        element={
          <ProtectedRoute>
            <Layout><DataAnalysis /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/translator"
        element={
          <ProtectedRoute>
            <Layout><Translator /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/election-law"
        element={
          <ProtectedRoute>
            <Layout><ElectionLaw /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/meeting-summary"
        element={
          <ProtectedRoute>
            <Layout><MeetingSummarizer /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/kakao-promo"
        element={
          <ProtectedRoute>
            <Layout><KakaoPromo /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/report-writer"
        element={
          <ProtectedRoute>
            <Layout><ReportWriter /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/address-geocoder"
        element={
          <ProtectedRoute>
            <Layout><AddressGeocoder /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/excel-merger"
        element={
          <ProtectedRoute>
            <Layout><ExcelMerger /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/about"
        element={
          <ProtectedRoute>
            <Layout><About /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/data-validator"
        element={
          <ProtectedRoute>
            <Layout><DataValidator /></Layout>
          </ProtectedRoute>
        }
      />

      {/* 출장보고 생성기 */}
      <Route
        path="/trip-report"
        element={
          <ProtectedRoute>
            <Layout><TripReport /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/law-chatbot"
        element={
          <ProtectedRoute>
            <Layout><LawChatbot /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/timeline"
        element={
          <ProtectedRoute>
            <Layout><TimelinePlanner /></Layout>
          </ProtectedRoute>
        }
      />

      {/* 프롬프트 관리 */}
      <Route
        path="/prompt-manager"
        element={
          <ProtectedRoute>
            <Layout><PromptManager /></Layout>
          </ProtectedRoute>
        }
      />

      {/* HWPX 변환기 */}
      <Route
        path="/hwpx-converter"
        element={
          <ProtectedRoute>
            <Layout><HwpxConverter /></Layout>
          </ProtectedRoute>
        }
      />

      {/* 재난상황 대시보드 */}
      <Route
        path="/disaster-upload"
        element={
          <ProtectedRoute>
            <Layout><DisasterUpload /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/disaster-dashboard"
        element={
          <ProtectedRoute>
            <Layout><DisasterDashboard /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/disaster-incidents"
        element={
          <ProtectedRoute>
            <Layout><DisasterIncidents /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/disaster-report"
        element={
          <ProtectedRoute>
            <Layout><DisasterDailyReport /></Layout>
          </ProtectedRoute>
        }
      />

      {/* 게시판 라우트 */}
      <Route path="/board/notice" element={<ProtectedRoute><Layout><NoticeBoard /></Layout></ProtectedRoute>} />
      <Route path="/board/archive" element={<ProtectedRoute><Layout><ArchiveBoard /></Layout></ProtectedRoute>} />
      <Route path="/board/qna" element={<ProtectedRoute><Layout><QnaBoard /></Layout></ProtectedRoute>} />
      <Route path="/board/:boardType/:id" element={<ProtectedRoute><Layout><BoardDetail /></Layout></ProtectedRoute>} />
      <Route path="/board/:boardType/write" element={<ProtectedRoute><Layout><BoardWrite /></Layout></ProtectedRoute>} />
      <Route path="/board/:boardType/edit/:id" element={<ProtectedRoute><Layout><BoardEdit /></Layout></ProtectedRoute>} />

      {/* 404 */}
      <Route
        path="*"
        element={
          <ProtectedRoute>
            <Layout><NotFound /></Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}