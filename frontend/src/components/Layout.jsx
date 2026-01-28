import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import {
  ChevronDown,
  Home,
  Info,
  Cpu,
  MessageSquare,
  LogOut,
  User,
  LayoutGrid,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

// AI 서비스 목록
const aiServices = [
  { icon: '📰', title: '충주시 뉴스', path: '/news' },
  { icon: '📝', title: '보도자료 생성기', path: '/press-release' },
  { icon: '🏅', title: '공적조서 생성기', path: '/merit-report' },
  { icon: '📊', title: 'AI 통계분석 챗봇', path: '/data-analysis' },
  { icon: '🌐', title: '다국어 번역기', path: '/translator' },
  { icon: '⚖️', title: '선거법 챗봇', path: '/election-law' },
  { icon: '🎙️', title: '회의 요약기', path: '/meeting-summary' },
  { icon: '📢', title: '홍보문구 생성기', path: '/kakao-promo' },
  { icon: '📄', title: '업무보고 생성기', path: '/report-writer' },
  { icon: '📍', title: '주소-좌표 변환기', path: '/address-geocoder' },
  { icon: '📑', title: '엑셀 취합기', path: '/excel-merger' },
];

// 소통공간 메뉴
const communityMenus = [
  { icon: '📢', title: '공지사항', path: '/board/notice' },
  { icon: '❓', title: '묻고답하기', path: '/board/qna' },
  { icon: '📁', title: '자료실', path: '/board/archive' },
];

// 사이드바 아코디언 메뉴
function SidebarGroup({ label, icon: Icon, items, openKey, setOpenKey, groupKey }) {
  const navigate = useNavigate();
  const isOpen = openKey === groupKey;

  const handleGo = (path) => {
    setOpenKey(null);
    navigate(path);
  };

  return (
    <div className="px-2">
      <button
        onClick={() => setOpenKey(isOpen ? null : groupKey)}
        className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg transition-all ${
          isOpen ? 'bg-slate-800 text-cyan-300' : 'text-slate-300 hover:bg-slate-800/50 hover:text-white'
        }`}
      >
        <div className="flex items-center gap-2">
          <Icon size={18} />
          <span className="text-sm font-medium">{label}</span>
        </div>
        <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="mt-1 mb-2 pl-2">
          {items.map((item, idx) => (
            <button
              key={idx}
              onClick={() => handleGo(item.path)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <span className="text-base">{item.icon}</span>
              <span>{item.title}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Layout({ children }) {
  const location = useLocation();
  const [openKey, setOpenKey] = useState(null);
  const { user, logout } = useAuth();

  useEffect(() => {
    setOpenKey(null);
  }, [location.pathname]);

  const handleLogout = async () => {
    await logout();
  };

  const isActive = (path) => location.pathname === path;

  return (
    <div className="min-h-screen bg-slate-950 flex">
      {/* Left Sidebar */}
      <aside className="w-72 shrink-0 border-r border-slate-800 bg-slate-950/95 backdrop-blur-xl">
        {/* Brand */}
        <div className="p-4 border-b border-slate-800">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-11 h-11 bg-cyan-500 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform shadow-lg shadow-cyan-500/30">
              <span className="text-2xl">🏛️</span>
            </div>
            <div>
              <div className="text-base font-bold text-white">충주시 AI 플랫폼</div>
              <div className="text-xs text-cyan-300">Chungju AI Platform</div>
            </div>
          </Link>
        </div>

        {/* User card (top) */}
        <div className="p-4 border-b border-slate-800">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center">
              <User size={18} className="text-slate-300" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold text-white">사용자</div>
              <div className="text-xs text-slate-400 truncate">
                {user?.email || '로그인 정보 없음'}
              </div>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-red-300 hover:border-red-500/40 hover:bg-slate-900/60 transition-all"
          >
            <LogOut size={16} />
            <span className="text-sm font-medium">로그아웃</span>
          </button>
        </div>

        {/* Menus (bottom) */}
        <div className="py-3">
          <div className="px-4 pb-2 text-xs font-semibold text-slate-500">메뉴</div>

          <div className="px-2">
            <Link
              to="/"
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-all ${
                isActive('/') ? 'bg-slate-800 text-cyan-300' : 'text-slate-300 hover:bg-slate-800/50 hover:text-white'
              }`}
            >
              <Home size={18} />
              <span className="text-sm font-medium">홈으로</span>
            </Link>

            <Link
              to="/about"
              className={`mt-1 w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-all ${
                isActive('/about') ? 'bg-slate-800 text-cyan-300' : 'text-slate-300 hover:bg-slate-800/50 hover:text-white'
              }`}
            >
              <Info size={18} />
              <span className="text-sm font-medium">시스템 소개</span>
            </Link>
          </div>

          <div className="mt-3">
            <SidebarGroup
              label="AI 서비스"
              icon={Cpu}
              items={aiServices}
              openKey={openKey}
              setOpenKey={setOpenKey}
              groupKey="services"
            />
            <SidebarGroup
              label="소통공간"
              icon={MessageSquare}
              items={communityMenus}
              openKey={openKey}
              setOpenKey={setOpenKey}
              groupKey="community"
            />
          </div>

          {/* Optional quick link */}
          <div className="mt-4 px-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3">
              <div className="flex items-center gap-2 text-slate-300">
                <LayoutGrid size={16} />
                <span className="text-sm font-semibold">바로가기</span>
              </div>
              <div className="mt-2 text-xs text-slate-400">
                자주 쓰는 서비스를 사이드바에서 바로 선택할 수 있습니다.
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Right Content */}
      <div className="flex-1 min-w-0">
        <main>{children}</main>

        {/* Footer */}
        <footer className="bg-slate-950 text-slate-400 border-t border-slate-800 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="text-center text-sm">
              <p>© 2026 충주시 AI 플랫폼 · All rights reserved.</p>
              <p className="mt-1">AI 기반 스마트 업무도구로 더 나은 행정서비스를 만들어갑니다</p>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
