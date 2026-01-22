import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';

const services = [
  // 첫 번째 줄
  {
    icon: '📰',
    title: '충주시 뉴스',
    description: '충주시 관련 뉴스를 자동으로 수집하고 AI가 요약합니다',
    path: '/news',
    badge: null,
    disabled: false
  },
  {
    icon: '📝',
    title: '보도자료 생성기',
    description: 'GPT 기반 자동 보도자료 작성 시스템',
    path: '/press-release',
    badge: null,
    disabled: false
  },
  {
    icon: '🏅',
    title: '공적조서 생성기',
    description: 'GPT가 공무원 공적조서를 자동으로 작성합니다',
    path: '/merit-report',
    badge: null,
    disabled: false
  },
  // 두 번째 줄
  {
    icon: '📊',
    title: 'AI 통계분석 챗봇',
    description: '엑셀 데이터를 업로드하고 자연어로 분석하세요',
    path: '/data-analysis',
    badge: null,
    disabled: false
  },
  {
    icon: '🌐',
    title: '다국어 번역기',
    description: 'HWPX 문서를 DeepL + GPT로 고품질 번역',
    path: '/translator',
    badge: null,
    disabled: false
  },
  {
    icon: '⚖️',
    title: '선거법 챗봇',
    description: '대화형 선거법 질의응답 시스템',
    path: '/election-law',
    badge: null,
    disabled: false
  },
  // 세 번째 줄
  {
    icon: '🎙️',
    title: '회의 요약기',
    description: '회의 녹음/텍스트를 AI가 자동으로 요약합니다',
    path: '/meeting-summary',
    badge: null,
    disabled: false
  },
  {
    icon: '📢',
    title: '홍보문구 생성기',
    description: '카카오채널용 홍보 문구를 AI가 자동 생성',
    path: '/kakao-promo',
    badge: null,
    disabled: false
  },
  {
    icon: '📍',
    title: '주소-좌표 변환기',
    description: '카카오 API 기반 주소 ↔ 좌표 일괄 변환',
    path: '/address-geocoder',
    badge: null,
    disabled: false
  },
  // 네 번째 줄
  {
    icon: '📑',
    title: '엑셀 취합기',
    description: '여러 엑셀 파일을 하나로 병합합니다',
    path: '/excel-merger',
    badge: null,
    disabled: false
  }
];

const stats = [
  { value: '10', label: 'AI 서비스' },
  { value: '24/7', label: '실시간 운영' },
  { value: '100%', label: '무료 이용' }
];

export default function Dashboard() {
  // 스크롤 함수
  const scrollToServices = () => {
    document.getElementById('services')?.scrollIntoView({ 
      behavior: 'smooth',
      block: 'start'
    });
  };

  return (
    <div className="min-h-screen">
      {/* Hero Section - Darker Navy Background */}
      <section className="relative bg-slate-950 text-white py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-500/10 border border-cyan-500/20 rounded-full mb-6">
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
            <span className="text-cyan-300 text-sm font-medium">공공 AI 서비스</span>
          </div>

          {/* Main Title */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-4">
            <span className="text-white">AI 기반</span>
            <br />
            <span className="text-cyan-400">행정 업무 지원 플랫폼</span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-slate-300 mb-8 leading-relaxed max-w-2xl mx-auto">
            충주시 행정 업무를 지원하는
            <br />
            AI 기반 업무 자동화 서비스입니다.
          </p>

          {/* CTA Button - Single Button */}
          <div className="flex justify-center mb-16">
            <button
              onClick={scrollToServices}
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-cyan-500 hover:bg-cyan-600 text-white font-semibold rounded-lg transition-all shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40"
            >
              <Sparkles size={20} />
              서비스 알아보기
              <ArrowRight size={20} />
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 max-w-2xl mx-auto">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-3xl sm:text-4xl font-bold text-cyan-400 mb-2">
                  {stat.value}
                </div>
                <div className="text-sm text-slate-400">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Services Section - Light Background */}
      <section id="services" className="py-16 bg-slate-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Section Header */}
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
              AI 서비스
            </h2>
            <p className="text-lg text-slate-600">
              충주시가 제공하는 인공지능 기반 행정 서비스를 이용해 보세요
            </p>
          </div>

          {/* Service Cards */}
          <div className="grid md:grid-cols-3 gap-6">
            {services.map((service, index) => (
              service.disabled ? (
                // 준비중인 서비스 (클릭 불가)
                <div
                  key={index}
                  className="group relative bg-white rounded-2xl p-8 shadow-md border border-slate-200 opacity-70 cursor-not-allowed"
                >
                  {/* Badge */}
                  {service.badge && (
                    <div className="absolute top-4 right-4 px-3 py-1 bg-orange-100 text-orange-600 text-xs font-semibold rounded-full">
                      {service.badge}
                    </div>
                  )}

                  {/* Icon */}
                  <div className="w-16 h-16 bg-gradient-to-br from-slate-100 to-slate-200 rounded-2xl flex items-center justify-center text-3xl mb-6">
                    {service.icon}
                  </div>

                  {/* Title */}
                  <h3 className="text-xl font-bold text-slate-500 mb-3">
                    {service.title}
                  </h3>

                  {/* Description */}
                  <p className="text-slate-400 leading-relaxed mb-4">
                    {service.description}
                  </p>

                  {/* Arrow */}
                  <div className="flex items-center text-slate-400 font-semibold">
                    <span>준비중</span>
                  </div>
                </div>
              ) : (
                // 활성화된 서비스
                <Link
                  key={index}
                  to={service.path}
                  className="group relative bg-white rounded-2xl p-8 shadow-md hover:shadow-2xl transition-all duration-300 border border-slate-200 hover:border-cyan-300"
                >
                  {/* Badge */}
                  {service.badge && (
                    <div className="absolute top-4 right-4 px-3 py-1 bg-cyan-100 text-cyan-600 text-xs font-semibold rounded-full">
                      {service.badge}
                    </div>
                  )}

                  {/* Icon */}
                  <div className="w-16 h-16 bg-gradient-to-br from-cyan-100 to-blue-100 rounded-2xl flex items-center justify-center text-3xl mb-6 group-hover:scale-110 transition-transform">
                    {service.icon}
                  </div>

                  {/* Title */}
                  <h3 className="text-xl font-bold text-slate-900 mb-3 group-hover:text-cyan-600 transition-colors">
                    {service.title}
                  </h3>

                  {/* Description */}
                  <p className="text-slate-600 leading-relaxed mb-4">
                    {service.description}
                  </p>

                  {/* Arrow */}
                  <div className="flex items-center text-cyan-600 font-semibold group-hover:gap-2 transition-all">
                    <span>시작하기</span>
                    <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                  </div>
                </Link>
              )
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="text-center">
              <div className="w-16 h-16 bg-cyan-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">🚀</span>
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">빠른 처리</h3>
              <p className="text-slate-600">
                AI 기반 자동화로 업무 시간을 대폭 단축합니다
              </p>
            </div>

            {/* Feature 2 */}
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">🎯</span>
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">높은 정확도</h3>
              <p className="text-slate-600">
                충주시 데이터 학습으로 맞춤형 결과를 제공합니다
              </p>
            </div>

            {/* Feature 3 */}
            <div className="text-center">
              <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">💻</span>
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">쉬운 사용</h3>
              <p className="text-slate-600">
                직관적인 인터페이스로 누구나 쉽게 사용 가능합니다
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-slate-950 text-white px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            지금 바로 시작하세요
          </h2>
          <p className="text-lg text-slate-300 mb-8">
            AI 행정 서비스로 업무 효율을 높이고 시민 만족도를 향상시키세요
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="mailto:storm8787@korea.kr"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-cyan-500 hover:bg-cyan-600 text-white font-semibold rounded-lg transition-all"
            >
              📧 이메일 문의
            </a>
            <a
              href="tel:0438505312"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-transparent border-2 border-slate-700 hover:border-cyan-500 text-white font-semibold rounded-lg transition-all"
            >
              📞 전화 문의
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}