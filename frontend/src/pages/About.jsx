import { 
  Cpu, Server, Shield, Zap, Users, Building2, 
  CheckCircle, ArrowRight, Mail, Phone, MapPin,
  Database, Cloud, Bot, FileText
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

// AI 서비스 목록
const services = [
  { icon: '📰', title: '충주시 뉴스', description: '실시간 뉴스 수집 및 AI 요약', path: '/news' },
  { icon: '📝', title: '보도자료 생성기', description: '8,000건 학습 기반 자동 작성', path: '/press-release' },
  { icon: '🏅', title: '공적조서 생성기', description: '포상 공적조서 자동 생성', path: '/merit-report' },
  { icon: '📊', title: 'AI 통계분석', description: '엑셀 데이터 자연어 분석', path: '/data-analysis' },
  { icon: '🌐', title: '다국어 번역기', description: 'DeepL+GPT 고품질 번역', path: '/translator' },
  { icon: '⚖️', title: '선거법 챗봇', description: '공직선거법 질의응답', path: '/election-law' },
  { icon: '🎙️', title: '회의 요약기', description: '회의록 자동 요약', path: '/meeting-summary' },
  { icon: '📢', title: '홍보문구 생성기', description: '카카오채널 홍보문구', path: '/kakao-promo' },
  { icon: '📄', title: '업무보고 생성기', description: '공무원 업무보고서 작성', path: '/report-writer' },
  { icon: '📍', title: '주소-좌표 변환', description: '일괄 주소/좌표 변환', path: '/address-geocoder' },
  { icon: '📑', title: '엑셀 취합기', description: '다중 엑셀 파일 병합', path: '/excel-merger' },
];

// 기술 스택
const techStack = [
  { category: '프론트엔드', items: ['React 18', 'Vite', 'TailwindCSS', 'React Router'], icon: <Cpu className="text-cyan-400" /> },
  { category: '백엔드', items: ['FastAPI', 'Python 3.11', 'Uvicorn', 'Pydantic'], icon: <Server className="text-blue-400" /> },
  { category: 'AI/ML', items: ['GPT-4o', 'FAISS', 'LangChain', 'Sentence Transformers'], icon: <Bot className="text-purple-400" /> },
  { category: '클라우드', items: ['Azure Container Apps', 'Azure Static Web Apps', 'Supabase'], icon: <Cloud className="text-green-400" /> },
];

// 주요 특징
const features = [
  {
    icon: <Zap className="text-yellow-400" size={32} />,
    title: '빠른 처리 속도',
    description: 'AI 기반 자동화로 기존 30분 걸리던 작업을 3분 내로 완료'
  },
  {
    icon: <Shield className="text-green-400" size={32} />,
    title: '보안 및 신뢰성',
    description: 'Azure 클라우드 기반 안정적인 서비스 운영 및 데이터 보호'
  },
  {
    icon: <Database className="text-blue-400" size={32} />,
    title: '충주시 맞춤 학습',
    description: '8,000건 이상의 충주시 보도자료로 학습된 맞춤형 AI'
  },
  {
    icon: <Users className="text-purple-400" size={32} />,
    title: '사용자 친화적',
    description: '직관적인 인터페이스로 누구나 쉽게 사용 가능'
  },
];

export default function About() {
  const navigate = useNavigate();

  // 서비스 둘러보기 클릭 시 메인 페이지 AI 서비스 섹션으로 이동
  const handleGoToServices = () => {
    navigate('/');
    // 약간의 딜레이 후 스크롤 (페이지 로드 대기)
    setTimeout(() => {
      const servicesSection = document.getElementById('services');
      if (servicesSection) {
        servicesSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
  };

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative bg-slate-950 text-white py-20 px-4 overflow-hidden">
        {/* Background Effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 via-transparent to-purple-500/10"></div>
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full filter blur-3xl"></div>
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full filter blur-3xl"></div>
        
        <div className="relative z-10 max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-500/10 border border-cyan-500/20 rounded-full mb-6">
            <Building2 size={18} className="text-cyan-400" />
            <span className="text-cyan-300 text-sm font-medium">충주시청 디지털전환</span>
          </div>
          
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6">
            <span className="text-white">충주시 AI 플랫폼</span>
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
              시스템 소개
            </span>
          </h1>
          
          <p className="text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto leading-relaxed">
            인공지능 기반 행정 업무 자동화 플랫폼으로<br />
            더 빠르고, 더 정확하고, 더 효율적인 행정 서비스를 제공합니다.
          </p>
        </div>
      </section>

      {/* 플랫폼 개요 */}
      <section className="py-16 bg-white">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">플랫폼 개요</h2>
            <p className="text-slate-600 max-w-2xl mx-auto">
              충주시 AI 플랫폼은 행정 업무의 디지털 전환을 선도하는 통합 AI 서비스입니다.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-slate-50 rounded-2xl p-8">
              <h3 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
                <FileText className="text-cyan-500" />
                프로젝트 정보
              </h3>
              <ul className="space-y-3 text-slate-600">
                <li className="flex items-start gap-3">
                  <CheckCircle className="text-green-500 flex-shrink-0 mt-0.5" size={20} />
                  <span><strong>프로젝트명:</strong> 충주시 AI 플랫폼 (Chungju AI Platform)</span>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="text-green-500 flex-shrink-0 mt-0.5" size={20} />
                  <span><strong>운영기관:</strong> 충주시청 자치행정과</span>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="text-green-500 flex-shrink-0 mt-0.5" size={20} />
                  <span><strong>서비스 시작:</strong> 2024년 1월</span>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="text-green-500 flex-shrink-0 mt-0.5" size={20} />
                  <span><strong>AI 서비스:</strong> 총 11개 기능 제공</span>
                </li>
              </ul>
            </div>

            <div className="bg-slate-50 rounded-2xl p-8">
              <h3 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
                <Zap className="text-yellow-500" />
                핵심 목표
              </h3>
              <ul className="space-y-3 text-slate-600">
                <li className="flex items-start gap-3">
                  <CheckCircle className="text-green-500 flex-shrink-0 mt-0.5" size={20} />
                  <span>반복적인 문서 작업 자동화 (보도자료, 공적조서, 회의록)</span>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="text-green-500 flex-shrink-0 mt-0.5" size={20} />
                  <span>데이터 분석 및 번역 작업 간소화</span>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="text-green-500 flex-shrink-0 mt-0.5" size={20} />
                  <span>주소/좌표 변환, 엑셀 취합 등 실무 유틸리티 제공</span>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="text-green-500 flex-shrink-0 mt-0.5" size={20} />
                  <span>GPT 기반 챗봇으로 정보 제공 서비스 강화</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* 주요 특징 */}
      <section className="py-16 bg-slate-50">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">주요 특징</h2>
            <p className="text-slate-600">왜 충주시 AI 플랫폼인가?</p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <div 
                key={index} 
                className="bg-white rounded-2xl p-6 shadow-sm hover:shadow-lg transition-all border border-slate-100"
              >
                <div className="w-14 h-14 bg-slate-50 rounded-xl flex items-center justify-center mb-4">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-2">{feature.title}</h3>
                <p className="text-slate-600 text-sm">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* AI 서비스 목록 */}
      <section className="py-16 bg-white">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">AI 서비스</h2>
            <p className="text-slate-600">총 11개의 AI 기반 행정 서비스를 제공합니다</p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {services.map((service, index) => (
              <Link
                key={index}
                to={service.path}
                className="flex items-center gap-4 p-4 bg-slate-50 rounded-xl hover:bg-cyan-50 hover:border-cyan-200 border border-transparent transition-all group"
              >
                <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center text-2xl shadow-sm group-hover:scale-110 transition-transform">
                  {service.icon}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-slate-900 group-hover:text-cyan-600 transition-colors">
                    {service.title}
                  </h3>
                  <p className="text-sm text-slate-500">{service.description}</p>
                </div>
                <ArrowRight className="text-slate-300 group-hover:text-cyan-500 group-hover:translate-x-1 transition-all" size={20} />
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* 기술 스택 */}
      <section className="py-16 bg-slate-900 text-white">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">기술 스택</h2>
            <p className="text-slate-400">최신 기술로 구축된 안정적인 플랫폼</p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {techStack.map((stack, index) => (
              <div key={index} className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
                <div className="flex items-center gap-3 mb-4">
                  {stack.icon}
                  <h3 className="font-bold text-white">{stack.category}</h3>
                </div>
                <ul className="space-y-2">
                  {stack.items.map((item, idx) => (
                    <li key={idx} className="text-slate-400 text-sm flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full"></div>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>     

      {/* 문의처 */}
      <section className="py-16 bg-slate-50">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">문의처</h2>
            <p className="text-slate-600">서비스 이용 및 기술 지원 문의</p>
          </div>

          <div className="grid sm:grid-cols-3 gap-6">
            <div className="bg-white rounded-2xl p-6 text-center shadow-sm border border-slate-100">
              <div className="w-14 h-14 bg-cyan-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Building2 className="text-cyan-600" size={28} />
              </div>
              <h3 className="font-bold text-slate-900 mb-2">담당부서</h3>
              <p className="text-slate-600">충주시청 자치행정과</p>
            </div>

            <div className="bg-white rounded-2xl p-6 text-center shadow-sm border border-slate-100">
              <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Phone className="text-blue-600" size={28} />
              </div>
              <h3 className="font-bold text-slate-900 mb-2">전화</h3>
              <a href="tel:0438505312" className="text-blue-600 hover:underline">043-850-5312</a>
            </div>

            <div className="bg-white rounded-2xl p-6 text-center shadow-sm border border-slate-100">
              <div className="w-14 h-14 bg-green-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Mail className="text-green-600" size={28} />
              </div>
              <h3 className="font-bold text-slate-900 mb-2">이메일</h3>
              <a href="mailto:storm8787@korea.kr" className="text-green-600 hover:underline">storm8787@korea.kr</a>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-slate-950 text-white">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">지금 바로 시작하세요</h2>
          <p className="text-slate-300 mb-8">
            AI 기반 행정 서비스로 업무 효율을 높이고 시민 만족도를 향상시키세요
          </p>
          <button
            onClick={handleGoToServices}
            className="inline-flex items-center gap-2 px-8 py-4 bg-cyan-500 hover:bg-cyan-600 text-white font-semibold rounded-xl transition-all shadow-lg shadow-cyan-500/25 cursor-pointer"
          >
            서비스 둘러보기
            <ArrowRight size={20} />
          </button>
        </div>
      </section>
    </div>
  );
}