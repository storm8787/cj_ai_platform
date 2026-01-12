import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Scale, Newspaper, Activity, CheckCircle, XCircle } from 'lucide-react';
import { checkHealth } from '../services/api';

const features = [
  {
    path: '/press-release',
    icon: FileText,
    title: '보도자료 생성기',
    description: 'AI가 유사 사례를 참고하여 보도자료 초안을 생성합니다.',
    color: 'bg-blue-500',
  },
  {
    path: '/election-law',
    icon: Scale,
    title: '선거법 챗봇',
    description: '선거법 관련 질문에 법령과 판례를 기반으로 답변합니다.',
    color: 'bg-purple-500',
  },
  {
    path: '/news',
    icon: Newspaper,
    title: '뉴스 뷰어',
    description: '충주시 관련 뉴스를 모아보고 AI 요약을 제공합니다.',
    color: 'bg-green-500',
  },
];

function Dashboard() {
  const [backendStatus, setBackendStatus] = useState('checking');

  useEffect(() => {
    const checkBackend = async () => {
      try {
        await checkHealth();
        setBackendStatus('online');
      } catch (error) {
        console.error('Backend health check failed:', error);
        setBackendStatus('offline');
      }
    };
    
    checkBackend();
    // 30초마다 상태 체크
    const interval = setInterval(checkBackend, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* 헤더 카드 */}
      <div className="card">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              충주시 AI 플랫폼에 오신 것을 환영합니다
            </h2>
            <p className="mt-2 text-gray-600">
              AI 기반 업무 자동화 도구를 활용하여 효율적인 업무 처리를 지원합니다.
            </p>
          </div>
          
          {/* 백엔드 상태 */}
          <div className={`
            flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium
            ${backendStatus === 'online' ? 'bg-green-100 text-green-700' : 
              backendStatus === 'offline' ? 'bg-red-100 text-red-700' : 
              'bg-gray-100 text-gray-600'}
          `}>
            {backendStatus === 'online' ? (
              <>
                <CheckCircle size={16} />
                <span>서버 정상</span>
              </>
            ) : backendStatus === 'offline' ? (
              <>
                <XCircle size={16} />
                <span>서버 오프라인</span>
              </>
            ) : (
              <>
                <Activity size={16} className="animate-pulse" />
                <span>확인 중...</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 기능 카드 그리드 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {features.map(({ path, icon: Icon, title, description, color }) => (
          <Link
            key={path}
            to={path}
            className="card hover:shadow-md transition-shadow duration-200 group"
          >
            <div className={`
              w-12 h-12 rounded-xl ${color} 
              flex items-center justify-center mb-4
              group-hover:scale-110 transition-transform duration-200
            `}>
              <Icon size={24} className="text-white" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {title}
            </h3>
            <p className="text-gray-600 text-sm">
              {description}
            </p>
          </Link>
        ))}
      </div>

      {/* 시스템 정보 */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">시스템 정보</h3>
        <div className="grid sm:grid-cols-2 gap-4 text-sm">
          <div className="flex justify-between py-2 border-b border-gray-100">
            <span className="text-gray-500">프론트엔드</span>
            <span className="text-gray-900 font-medium">Azure Static Web Apps</span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-100">
            <span className="text-gray-500">백엔드</span>
            <span className="text-gray-900 font-medium">Azure Container Apps</span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-100">
            <span className="text-gray-500">AI 모델</span>
            <span className="text-gray-900 font-medium">GPT-4o-mini</span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-100">
            <span className="text-gray-500">벡터 검색</span>
            <span className="text-gray-900 font-medium">FAISS + ko-sroberta</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
