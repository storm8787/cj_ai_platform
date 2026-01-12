import { Link } from 'react-router-dom';
import { Home, ArrowLeft } from 'lucide-react';

function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center animate-fadeIn">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-200 mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          페이지를 찾을 수 없습니다
        </h2>
        <p className="text-gray-600 mb-8">
          요청하신 페이지가 존재하지 않거나 이동되었습니다.
        </p>
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => window.history.back()}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowLeft size={18} />
            이전 페이지
          </button>
          <Link to="/" className="btn-primary flex items-center gap-2">
            <Home size={18} />
            홈으로
          </Link>
        </div>
      </div>
    </div>
  );
}

export default NotFound;
