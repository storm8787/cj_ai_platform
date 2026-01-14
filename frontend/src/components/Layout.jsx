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
    <div className="min-h-screen bg-slate-50">
      {/* Header - Dark Navy */}
      <header className="bg-gradient-to-r from-slate-900 via-blue-900 to-slate-900 shadow-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <Link to="/" className="flex items-center space-x-3 group">
              <div className="w-12 h-12 bg-cyan-500 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform shadow-lg shadow-cyan-500/30">
                <span className="text-2xl">🏛️</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">충주시 AI 플랫폼</h1>
                <p className="text-xs text-cyan-300">Chungju AI Platform</p>
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
                      ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/30 font-semibold' 
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
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
      <footer className="bg-slate-900 text-slate-400 border-t border-slate-800 mt-12">
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