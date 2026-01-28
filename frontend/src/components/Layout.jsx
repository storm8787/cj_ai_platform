import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Home, Info, Cpu, MessageSquare, LogOut, User } from 'lucide-react';
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

// 드롭다운 메뉴 컴포넌트
function DropdownMenu({ label, icon: Icon, items, isOpen, onOpen, onClose }) {
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  // 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  const handleMouseEnter = () => {
    onOpen();
  };

  const handleMouseLeave = () => {
    onClose();
  };

  const handleItemClick = (e, path) => {
    e.preventDefault();
    e.stopPropagation();
    onClose();
    navigate(path);
  };

  return (
    <div
      className="relative"
      ref={dropdownRef}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <button
        className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
          isOpen ? 'text-cyan-400 bg-slate-800' : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
        }`}
      >
        <Icon size={18} />
        <span>{label}</span>
        <ChevronDown
          size={16}
          className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* 드롭다운 메뉴 - z-index 9999로 최상위 */}
      {isOpen && (
        <div className="absolute top-full left-0 w-56 pt-2" style={{ zIndex: 9999 }}>
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden">
            {items.map((item, index) => (
              <button
                key={index}
                onClick={(e) => handleItemClick(e, item.path)}
                className="w-full px-4 py-3 text-left flex items-center gap-3 hover:bg-slate-800 transition-colors group"
              >
                <span className="text-lg">{item.icon}</span>
                <span className="text-sm text-slate-300 group-hover:text-white">{item.title}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Layout({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [openMenu, setOpenMenu] = useState(null);
  const { user, logout } = useAuth();

  const handleOpen = (menu) => {
    setOpenMenu(menu);
  };

  const handleClose = () => {
    setOpenMenu(null);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // 페이지 이동 시 메뉴 닫기
  useEffect(() => {
    setOpenMenu(null);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="bg-slate-950 shadow-2xl border-b border-slate-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* ✅ 여기서부터 “왼쪽 프레임(위 사용자 / 아래 메뉴)” 구조로 변경 */}
          <div className="py-4">
            <div className="flex items-start justify-between gap-6">
              {/* (왼쪽) 로고 + 사용자정보(위) + 메뉴(아래) */}
              <div className="flex flex-col gap-3">
                {/* 로고 */}
                <Link to="/" className="flex items-center space-x-3 group">
                  <div className="w-12 h-12 bg-cyan-500 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform shadow-lg shadow-cyan-500/30">
                    <span className="text-2xl">🏛️</span>
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-white">충주시 AI 플랫폼</h1>
                    <p className="text-xs text-cyan-300">Chungju AI Platform</p>
                  </div>
                </Link>

                {/* ✅ 사용자 정보 프레임 (왼쪽 위) */}
                <div className="flex items-center gap-3 bg-slate-900/60 border border-slate-800 rounded-xl px-3 py-2 w-fit">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                    <User size={16} className="text-slate-300" />
                  </div>
                  <div className="flex flex-col leading-tight">
                    <span className="text-xs text-slate-400">사용자</span>
                    <span className="text-sm text-slate-200">
                      {user?.email || '로그인 정보 없음'}
                    </span>
                  </div>

                  <div className="h-6 w-px bg-slate-800 mx-1" />

                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-1.5 px-2 py-1 text-sm font-medium text-slate-300 hover:text-red-300 rounded-lg hover:bg-slate-800/50 transition-all"
                  >
                    <LogOut size={16} />
                    <span>로그아웃</span>
                  </button>
                </div>

                {/* ✅ 메뉴 프레임 (왼쪽 아래) */}
                <nav className="hidden md:flex items-center gap-1">
                  {/* 홈으로 */}
                  <Link
                    to="/"
                    className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                      location.pathname === '/'
                        ? 'text-cyan-400 bg-slate-800'
                        : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
                    }`}
                  >
                    <Home size={18} />
                    <span>홈으로</span>
                  </Link>

                  {/* 시스템 소개 */}
                  <Link
                    to="/about"
                    className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                      location.pathname === '/about'
                        ? 'text-cyan-400 bg-slate-800'
                        : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
                    }`}
                  >
                    <Info size={18} />
                    <span>시스템 소개</span>
                  </Link>

                  {/* AI 서비스 드롭다운 */}
                  <DropdownMenu
                    label="AI 서비스"
                    icon={Cpu}
                    items={aiServices}
                    isOpen={openMenu === 'services'}
                    onOpen={() => handleOpen('services')}
                    onClose={handleClose}
                  />

                  {/* 소통공간 드롭다운 */}
                  <DropdownMenu
                    label="소통공간"
                    icon={MessageSquare}
                    items={communityMenus}
                    isOpen={openMenu === 'community'}
                    onOpen={() => handleOpen('community')}
                    onClose={handleClose}
                  />
                </nav>
              </div>

              {/* 모바일 메뉴 버튼(기존 유지) */}
              <button className="md:hidden text-slate-300 hover:text-white">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </button>
            </div>
          </div>
          {/* ✅ 변경 끝 */}
        </div>
      </header>

      {/* Main Content */}
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
  );
}
