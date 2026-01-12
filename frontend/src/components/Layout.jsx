import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Home, FileText, Scale, Newspaper, 
  Menu, X, ChevronRight 
} from 'lucide-react';

const menuItems = [
  { path: '/', icon: Home, label: '대시보드' },
  { path: '/press-release', icon: FileText, label: '보도자료 생성' },
  { path: '/election-law', icon: Scale, label: '선거법 챗봇' },
  { path: '/news', icon: Newspaper, label: '뉴스 뷰어' },
];

function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="min-h-screen flex">
      {/* 모바일 오버레이 */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 사이드바 */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-30
        w-64 bg-white border-r border-gray-200
        transform transition-transform duration-300 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* 로고 */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">CJ</span>
            </div>
            <span className="font-bold text-gray-900">AI 플랫폼</span>
          </Link>
          <button 
            className="lg:hidden p-1 hover:bg-gray-100 rounded"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        {/* 메뉴 */}
        <nav className="p-4 space-y-1">
          {menuItems.map(({ path, icon: Icon, label }) => {
            const isActive = location.pathname === path;
            return (
              <Link
                key={path}
                to={path}
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg
                  transition-all duration-200
                  ${isActive 
                    ? 'bg-primary-50 text-primary-700 font-medium' 
                    : 'text-gray-600 hover:bg-gray-100'
                  }
                `}
              >
                <Icon size={20} />
                <span>{label}</span>
                {isActive && <ChevronRight size={16} className="ml-auto" />}
              </Link>
            );
          })}
        </nav>

        {/* 하단 정보 */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            <p>충주시청 AI 플랫폼</p>
            <p className="mt-1">Azure Static Web Apps</p>
          </div>
        </div>
      </aside>

      {/* 메인 컨텐츠 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 헤더 */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-4 lg:px-6">
          <button 
            className="lg:hidden p-2 hover:bg-gray-100 rounded-lg mr-2"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={20} />
          </button>
          
          <h1 className="text-lg font-semibold text-gray-900">
            {menuItems.find(item => item.path === location.pathname)?.label || '충주시 AI 플랫폼'}
          </h1>
        </header>

        {/* 페이지 컨텐츠 */}
        <main className="flex-1 p-4 lg:p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

export default Layout;
