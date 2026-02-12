import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Home, Info, Cpu, MessageSquare, LogOut } from 'lucide-react';
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
  { icon: '🤖', title: '공공데이터 검증기', path: '/data-validator' },
];

// 소통공간 메뉴
const communityMenus = [
  { icon: '📢', title: '공지사항', path: '/board/notice' },
  { icon: '❓', title: '묻고답하기', path: '/board/qna' },
  { icon: '📁', title: '자료실', path: '/board/archive' },
];

// 드롭다운 컴포넌트
function DropdownMenu({ label, icon: Icon, items, isOpen, onOpen, onClose, active}) {
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  // 마우스 진입 시 열기
  const handleMouseEnter = () => {
    onOpen();
  };

  // 마우스 이탈 시 닫기 (딜레이 없음)
  const handleMouseLeave = () => {
    onClose();
  };

  // 메뉴 아이템 클릭 - navigate 사용
  const handleItemClick = (path) => {
    console.log('클릭!', path);
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
      <button className={`nav-link ${(isOpen || active) ? 'nav-link-active' : ''}`}>
        <Icon size={18} />
        <span>{label}</span>
        <ChevronDown 
          size={16} 
          className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>

      {/* 드롭다운 메뉴 - z-index 9999로 최상위 */}
      <div 
        className={`dropdown-menu ${isOpen ? 'dropdown-menu-open' : ''}`}
        style={{ zIndex: 9999 }}
      >
        <div className="dropdown-content py-2">
          {items.map((item, index) => (
            <div
              key={index}
              onClick={() => handleItemClick(item.path)}
              className="dropdown-item"
            >
                <span className="text-lg">{item.icon}</span>
                <span>{item.title}</span>
              </div>
            ))}
          </div>
        </div>
      
    </div>
  );
}

export default function Layout({ children }) {
  const location = useLocation();
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
  };

  // 페이지 이동 시 메뉴 닫기
  useEffect(() => {
    setOpenMenu(null);
  }, [location.pathname]);

  // ✅ 여기!!! (return 바로 위)
  const isServicesActive = aiServices.some(
    (s) => location.pathname === s.path
  );

  const isCommunityActive = communityMenus.some(
    (s) => location.pathname === s.path
  );

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="glass-header sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
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

            {/* 네비게이션 메뉴 */}
            <nav className="hidden md:flex items-center gap-1">
              {/* 홈으로 */}
              <Link
                to="/"
                className={`nav-link ${location.pathname === '/' ? 'nav-link-active' : ''}`}
                >
                <Home size={18} />
                <span>홈으로</span>
                </Link>

              {/* 시스템 소개 */}
              <Link
                to="/about"
                className={`nav-link ${location.pathname === '/about' ? 'nav-link-active' : ''}`}
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
                active={isServicesActive}
              />

              {/* 소통공간 드롭다운 */}
              <DropdownMenu
                label="소통공간"
                icon={MessageSquare}
                items={communityMenus}
                isOpen={openMenu === 'community'}
                onOpen={() => handleOpen('community')}
                onClose={handleClose}
                active={isCommunityActive}
              />
            </nav>

            {/* 사용자 정보 & 로그아웃 */}
            <div className="hidden md:flex items-center gap-3">
              {user && (
                <span className="text-sm text-slate-400">
                  {user.email}
                </span>
              )}
              <button onClick={handleLogout} className="btn-logout">

                <LogOut size={16} />
                <span>로그아웃</span>
              </button>
            </div>

            {/* 모바일 메뉴 버튼 */}
            <button className="md:hidden text-slate-300 hover:text-white">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>
        {children}
      </main>

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