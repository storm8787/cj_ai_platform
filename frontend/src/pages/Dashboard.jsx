import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles, Sun, Moon, CloudSun } from 'lucide-react';
import { useState, useEffect } from 'react';

// 카테고리 정의
const categories = [
  { id: 'all', name: '전체', icon: '🏠' },
  { id: 'document', name: '문서 작성', icon: '📝' },
  { id: 'data', name: '데이터 처리', icon: '📊' },
  { id: 'translate', name: '번역/요약', icon: '🌐' },
  { id: 'chatbot', name: '업무 챗봇', icon: '💬' },
];

// 서비스 목록 (기존 순서 유지 + 카테고리 추가)
const services = [
  // 기존 순서 1~12 + 신규 추가
  {
    icon: '📰',
    title: '충주시 뉴스',
    description: '충주시 관련 뉴스를 자동으로 수집하고 AI가 요약합니다',
    path: '/news',
    category: 'translate',
  },
  {
    icon: '📝',
    title: '보도자료 생성기',
    description: 'GPT 기반 자동 보도자료 작성 시스템',
    path: '/press-release',
    category: 'document',
  },
  {
    icon: '🏅',
    title: '공적조서 생성기',
    description: 'GPT가 공무원 공적조서를 자동으로 작성합니다',
    path: '/merit-report',
    category: 'document',
  },
  {
    icon: '📊',
    title: 'AI 통계분석 챗봇',
    description: '엑셀 데이터를 업로드하고 자연어로 분석하세요',
    path: '/data-analysis',
    category: 'data',
  },
  {
    icon: '🌐',
    title: '다국어 번역기',
    description: 'HWPX 문서를 DeepL + GPT로 고품질 번역',
    path: '/translator',
    category: 'translate',
  },
  {
    icon: '⚖️',
    title: '선거법 챗봇',
    description: '대화형 선거법 질의응답 시스템',
    path: '/election-law',
    category: 'chatbot',
  },
  {
    icon: '🎙️',
    title: '회의 요약기',
    description: '회의 녹음/텍스트를 AI가 자동으로 요약합니다',
    path: '/meeting-summary',
    category: 'translate',
  },
  {
    icon: '📢',
    title: '홍보문구 생성기',
    description: '카카오채널용 홍보 문구를 AI가 자동 생성',
    path: '/kakao-promo',
    category: 'document',
  },
  {
    icon: '📄',
    title: '업무보고 생성기',
    description: '공무원 스타일의 업무보고서를 AI가 자동 생성',
    path: '/report-writer',
    category: 'document',
  },
  {
    icon: '📍',
    title: '주소-좌표 변환기',
    description: '카카오 API 기반 주소 ↔ 좌표 일괄 변환',
    path: '/address-geocoder',
    category: 'data',
  },
  {
    icon: '📑',
    title: '엑셀 취합기',
    description: '여러 엑셀 파일을 하나로 병합합니다',
    path: '/excel-merger',
    category: 'data',
  },
  {
    icon: '✅',
    title: '공공데이터 검증기',
    description: '공공데이터 제공표준 적합성 검증',
    path: '/data-validator',
    category: 'data',
  },
  // 신규 추가: 출장보고 생성기
  {
    icon: '📋',
    title: '출장보고 생성기',
    description: '사진만 업로드하면 AI가 보고서를 자동 생성합니다',
    path: '/trip-report',
    category: 'document',
  },
];

// 카테고리별 순서 정의 (각 카테고리 클릭 시 이 순서로 표시)
const categoryOrder = {
  document: ['/press-release', '/merit-report', '/kakao-promo', '/report-writer', '/trip-report'],  // trip-report 추가
  data: ['/data-analysis', '/data-validator', '/address-geocoder', '/excel-merger'],
  translate: ['/news', '/translator', '/meeting-summary'],
  chatbot: ['/election-law'],
};

export default function Dashboard() {
  const [time, setTime] = useState(new Date());
  const [activeCategory, setActiveCategory] = useState('all');

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  const getGreeting = () => {
    const hour = time.getHours();
    if (hour < 6) return { text: '새벽 공기가 차갑네요', icon: <Moon className="text-indigo-400" size={24} /> };
    if (hour < 12) return { text: '좋은 아침입니다', icon: <Sun className="text-yellow-400" size={24} /> };
    if (hour < 18) return { text: '좋은 오후입니다', icon: <CloudSun className="text-orange-400" size={24} /> };
    return { text: '오늘 하루도 고생 많으셨습니다', icon: <Moon className="text-indigo-400" size={24} /> };
  };

  const scrollToServices = () => {
    document.getElementById('services')?.scrollIntoView({ 
      behavior: 'smooth',
      block: 'start'
    });
  };

  const greeting = getGreeting();

  // 필터링된 서비스 목록
  const filteredServices = activeCategory === 'all' 
    ? services 
    : categoryOrder[activeCategory]
        .map(path => services.find(s => s.path === path))
        .filter(Boolean);

  return (
    <div className="min-h-screen overflow-x-hidden">
      {/* Hero Section with Aurora Effect */}
      <section className="relative bg-slate-950 text-white py-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
        {/* Aurora Background Blobs */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/20 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob"></div>
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-32 left-1/3 w-96 h-96 bg-blue-500/20 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob animation-delay-4000"></div>

        <div className="relative z-10 max-w-4xl mx-auto text-center">
          {/* Dynamic Greeting */}
          <div className="fade-in-up flex flex-col items-center mb-6" style={{ animationDelay: '0.1s' }}>
            <div className="flex items-center gap-2 text-cyan-400 mb-2 font-medium">
              {greeting.icon}
              <span>{time.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <h2 className="text-xl sm:text-2xl text-slate-200 font-light">
              {greeting.text}, <span className="font-bold text-white">담당자님!</span> 👋
            </h2>
          </div>

          {/* Main Title */}
          <div className="fade-in-up" style={{ animationDelay: '0.2s' }}>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-4">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400">AI 기반</span>
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">행정 업무 지원 플랫폼</span>
            </h1>

            <p className="text-lg sm:text-xl text-slate-300 mb-8 leading-relaxed max-w-2xl mx-auto">
              충주시 행정 업무를 지원하는
              <br />
              AI 기반 업무 자동화 서비스입니다.
            </p>

            <button
              onClick={scrollToServices}
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-cyan-500 hover:bg-cyan-600 text-white font-semibold rounded-xl transition-all shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:-translate-y-1"
            >
              <Sparkles size={20} />
              서비스 시작하기
              <ArrowRight size={20} />
            </button>
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section id="services" className="py-16 bg-slate-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8 fade-in-up" style={{ animationDelay: '0.1s' }}>
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
              AI 서비스
            </h2>
            <p className="text-lg text-slate-600">
              충주시가 제공하는 인공지능 기반 행정 서비스를 이용해 보세요
            </p>
          </div>

          {/* Category Tabs */}
          <div className="flex flex-wrap justify-center gap-2 mb-10">
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setActiveCategory(category.id)}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium transition-all ${
                  activeCategory === category.id
                    ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/25'
                    : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                <span>{category.icon}</span>
                <span>{category.name}</span>
              </button>
            ))}
          </div>

          {/* Service Cards */}
          <div className="grid md:grid-cols-4 gap-6">
            {filteredServices.map((service, index) => (
              <Link
                key={service.path}
                to={service.path}
                className="fade-in-up group relative bg-white rounded-2xl p-8 shadow-md hover:shadow-2xl transition-all duration-300 border border-slate-200 hover:border-cyan-300 hover:-translate-y-1"
                style={{ animationDelay: `${0.1 + index * 0.03}s` }}
              >
                <div className="w-16 h-16 bg-gradient-to-br from-cyan-100 to-blue-100 rounded-2xl flex items-center justify-center text-3xl mb-6 group-hover:scale-110 transition-transform">
                  {service.icon}
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3 group-hover:text-cyan-600 transition-colors">
                  {service.title}
                </h3>
                <p className="text-slate-600 leading-relaxed mb-4">{service.description}</p>
                <div className="flex items-center text-cyan-600 font-semibold opacity-0 group-hover:opacity-100 transform -translate-x-2 group-hover:translate-x-0 transition-all duration-300">
                  <span>시작하기</span>
                  <ArrowRight size={18} className="ml-1" />
                </div>
              </Link>
            ))}
          </div>

          {/* Empty State */}
          {filteredServices.length === 0 && (
            <div className="text-center py-12 text-slate-500">
              해당 카테고리에 서비스가 없습니다.
            </div>
          )}
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center fade-in-up" style={{ animationDelay: '0.1s' }}>
              <div className="w-16 h-16 bg-cyan-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">🚀</span>
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">빠른 처리</h3>
              <p className="text-slate-600">AI 기반 자동화로 업무 시간을 대폭 단축합니다</p>
            </div>
            <div className="text-center fade-in-up" style={{ animationDelay: '0.2s' }}>
              <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">🎯</span>
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">높은 정확도</h3>
              <p className="text-slate-600">충주시 데이터 학습으로 맞춤형 결과를 제공합니다</p>
            </div>
            <div className="text-center fade-in-up" style={{ animationDelay: '0.3s' }}>
              <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">💻</span>
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">쉬운 사용</h3>
              <p className="text-slate-600">직관적인 인터페이스로 누구나 쉽게 사용 가능합니다</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-slate-950 text-white px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">지금 바로 시작하세요</h2>
          <p className="text-lg text-slate-300 mb-8">AI 행정 서비스로 업무 효율을 높이고 시민 만족도를 향상시키세요</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a href="mailto:storm8787@korea.kr" className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-cyan-500 hover:bg-cyan-600 text-white font-semibold rounded-lg transition-all">
              📧 이메일 문의
            </a>
            <a href="tel:0438505312" className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-transparent border-2 border-slate-700 hover:border-cyan-500 text-white font-semibold rounded-lg transition-all">
              📞 전화 문의
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}