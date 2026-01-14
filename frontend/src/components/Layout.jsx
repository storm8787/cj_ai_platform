import { Link, useLocation } from 'react-router-dom';

export default function Layout({ children }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header - Simplified without navigation */}
      <header className="bg-slate-950 shadow-2xl border-b border-slate-800">
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