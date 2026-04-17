import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Home, Info, Cpu, MessageSquare, LogOut, Settings } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

// AI 서비스 카테고리별 정리
const aiServiceCategories = [
  {
    id: 'document',
    name: '문서 작성',
    icon: '📝',
    services: [
      { icon: '📝', title: '보도자료 생성기', path: '/press-release' },
      { icon: '🏅', title: '공적조서 생성기', path: '/merit-report' },
      { icon: '📢', title: '홍보문구 생성기', path: '/kakao-promo' },
      { icon: '📄', title: '업무보고 생성기', path: '/report-writer' },
      { icon: '📋', title: '출장보고 생성기', path: '/trip-report' }
      //{ icon: '📃', title: 'MD 파일 변환기', path:'/hwpx-converter'}
    ]
  },
  {
    id: 'data',
    name: '데이터 처리',
    icon: '📊',
    services: [
      { icon: '📊', title: 'AI 통계분석 챗봇', path: '/data-analysis' },
      { icon: '✅', title: '공공데이터 검증기', path: '/data-validator' },
      { icon: '📍', title: '주소-좌표 변환기', path: '/address-geocoder' },
      { icon: '📑', title: '엑셀 취합기', path: '/excel-merger' },
      { icon: '📅', title: "사업 타임라인", path: "/timeline" }
    ]
  },
  {
    id: 'translate',
    name: '번역/요약',
    icon: '🌐',
    services: [
      { icon: '📰', title: '충주시 뉴스', path: '/news' },
      { icon: '🌐', title: '다국어 번역기', path: '/translator' },
      { icon: '🎙️', title: '회의 요약기', path: '/meeting-summary' },      
    ]
  },
  {
    id: 'chatbot',
    name: '업무 챗봇',
    icon: '💬',
    services: [
      { icon: '⚖️', title: '선거법 챗봇', path: '/election-law' },
      { icon: '📜', title: '법령·자치법규 챗봇', path: '/law-chatbot' },
    ]
  },
];

// 모든 AI 서비스 경로 (active 체크용)
const allAiServicePaths = aiServiceCategories.flatMap(cat => cat.services.map(s => s.path));

// 소통공간 메뉴
const communityMenus = [
  { icon: '📢', title: '공지사항', path: '/board/notice' },
  { icon: '❓', title: '묻고답하기', path: '/board/qna' },
  { icon: '📁', title: '자료실', path: '/board/archive' },
];

// 2단 드롭다운 컴포넌트 (AI 서비스용)
function NestedDropdownMenu({ label, icon: Icon, categories, isOpen, onOpen, onClose, active }) {
  const [hoveredCategory, setHoveredCategory] = useState(null);
  const navigate = useNavigate();

  const handleItemClick = (path) => {
    onClose();
    setHoveredCategory(null);
    navigate(path);
  };

  // 메뉴가 닫힐 때 hoveredCategory 초기화
  useEffect(() => {
    if (!isOpen) {
      setHoveredCategory(null);
    }
  }, [isOpen]);

  return (
    <div 
      className="relative"
      onMouseEnter={onOpen}
      onMouseLeave={onClose}
    >
      <button className={`nav-link ${(isOpen || active) ? 'nav-link-active' : ''}`}>
        <Icon size={18} />
        <span>{label}</span>
        <ChevronDown 
          size={16} 
          className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>

      {/* 1단 드롭다운: 카테고리 목록 */}
      {isOpen && (
        <div 
          className="absolute top-full left-0 pt-2"
          style={{ zIndex: 9999 }}
        >
          <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-2 min-w-[180px]">
            {categories.map((category) => (
              <div
                key={category.id}
                className="relative"
                onMouseEnter={() => setHoveredCategory(category.id)}
              >
                <div className={`flex items-center justify-between px-4 py-2.5 cursor-pointer transition-colors ${
                  hoveredCategory === category.id ? 'bg-slate-700 text-white' : 'text-slate-300 hover:bg-slate-700/50'
                }`}>
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{category.icon}</span>
                    <span>{category.name}</span>
                  </div>
                  <ChevronRight size={14} className="text-slate-400" />
                </div>

                {/* 2단 드롭다운: 서비스 목록 */}
                {hoveredCategory === category.id && (
                  <div 
                    className="absolute left-full top-0 pl-1"
                    style={{ zIndex: 10000 }}
                  >
                    <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-2 min-w-[200px]">
                      {category.services.map((service, idx) => (
                        <div
                          key={idx}
                          onClick={() => handleItemClick(service.path)}
                          className="flex items-center gap-2 px-4 py-2.5 text-slate-300 hover:bg-slate-700 hover:text-white cursor-pointer transition-colors"
                        >
                          <span className="text-lg">{service.icon}</span>
                          <span>{service.title}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// 일반 드롭다운 컴포넌트 (소통공간용)
function DropdownMenu({ label, icon: Icon, items, isOpen, onOpen, onClose, active }) {
  const navigate = useNavigate();

  const handleItemClick = (path) => {
    onClose();
    navigate(path);
  };

  return (
    <div 
      className="relative"
      onMouseEnter={onOpen}
      onMouseLeave={onClose}
    >
      <button className={`nav-link ${(isOpen || active) ? 'nav-link-active' : ''}`}>
        <Icon size={18} />
        <span>{label}</span>
        <ChevronDown 
          size={16} 
          className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>

      {/* 드롭다운 메뉴 */}
      {isOpen && (
        <div 
          className="absolute top-full left-0 pt-2"
          style={{ zIndex: 9999 }}
        >
          <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-2 min-w-[180px]">
            {items.map((item, index) => (
              <div
                key={index}
                onClick={() => handleItemClick(item.path)}
                className="flex items-center gap-2 px-4 py-2.5 text-slate-300 hover:bg-slate-700 hover:text-white cursor-pointer transition-colors"
              >
                <span className="text-lg">{item.icon}</span>
                <span>{item.title}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Layout({ children }) {
  const location = useLocation();
  const [openMenu, setOpenMenu] = useState(null);
  const { user, logout, isAdmin } = useAuth();

  // 메뉴 열기 - 다른 메뉴가 열려있으면 바로 전환
  const handleOpen = (menu) => {
    setOpenMenu(menu);
  };

  // 메뉴 닫기
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

  const isServicesActive = allAiServicePaths.includes(location.pathname);
  const isCommunityActive = communityMenus.some(s => location.pathname === s.path);

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

              {/* AI 서비스 - 2단 드롭다운 */}
              <NestedDropdownMenu
                label="AI 서비스"
                icon={Cpu}
                categories={aiServiceCategories}
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

              {/* 관리자 전용: 프롬프트 관리 */}
              {isAdmin && (
                <Link
                  to="/prompt-manager"
                  className={`nav-link ${location.pathname === '/prompt-manager' ? 'nav-link-active' : ''}`}
                >
                  <Settings size={18} />
                  <span>프롬프트 관리</span>
                </Link>
              )}
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
