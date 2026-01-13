import { Link, useLocation } from 'react-router-dom';
import { Newspaper, FileText, Scale, Home } from 'lucide-react';

const navigation = [
  { name: '대시보드', path: '/', icon: Home },
  { name: '충주시 뉴스', path: '/news', icon: Newspaper },
  { name: '보도자료 생성기', path: '/press-release', icon: FileText },
  { name: '선거법 챗봇', path: '/election-law', icon: Scale },
];

export default function Layout({ children }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100">
      {/* Header */}
      <header className="bg-gradient-to-r from-blue-600 to-blue-700 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <Link to="/" className="flex items-center space-x-3 group">
              <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                <span className="text-2xl">🏛️</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">충주시 AI 플랫폼</h1>
                <p className="text-xs text-blue-100">Chungju AI Platform</p>
              </div>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex space-x-1 pb-4 overflow-x-auto">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`
                    flex items-center space-x-2 px-4 py-2 rounded-lg transition-all whitespace-nowrap
                    ${isActive 
                      ? 'bg-white text-blue-700 shadow-md font-semibold' 
                      : 'text-blue-100 hover:bg-blue-500 hover:text-white'
                    }
                  `}
                >
                  <Icon size={18} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-sm text-gray-500">
            <p>© 2026 충주시 AI 플랫폼 · All rights reserved.</p>
            <p className="mt-1">AI 기반 스마트 업무도구로 더 나은 행정서비스를 만들어갑니다</p>
          </div>
        </div>
      </footer>
    </div>
  );
}