import { Link } from 'react-router-dom';
import { Newspaper, FileText, Scale, ArrowRight } from 'lucide-react';

const tools = [
  {
    icon: '📰',
    title: '충주시 뉴스',
    description: '충주시 관련 뉴스를 자동으로 수집하고 AI가 요약합니다',
    path: '/news',
    color: 'from-blue-500 to-blue-600'
  },
  {
    icon: '📝',
    title: '보도자료 생성기',
    description: 'GPT 기반 자동 보도자료 작성 시스템',
    path: '/press-release',
    color: 'from-blue-600 to-blue-700'
  },
  {
    icon: '⚖️',
    title: '선거법 챗봇',
    description: '대화형 선거법 질의응답 시스템',
    path: '/election-law',
    color: 'from-blue-700 to-blue-800'
  }
];

export default function Dashboard() {
  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Section */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-2xl shadow-xl p-12 text-center text-white">
        <h1 className="text-4xl font-bold mb-3">충주시 AI 연구소</h1>
        <p className="text-xl text-blue-100 mb-6">
          인공지능으로 더 스마트한 행정서비스를 만들어갑니다
        </p>
        
        <div className="inline-flex items-center gap-4 bg-white/10 backdrop-blur-md px-6 py-3 rounded-full">
          <div className="flex gap-2">
            <div className="w-8 h-8 bg-yellow-400 rounded-full flex items-center justify-center">
              📰
            </div>
            <div className="w-8 h-8 bg-blue-400 rounded-full flex items-center justify-center">
              📝
            </div>
            <div className="w-8 h-8 bg-green-400 rounded-full flex items-center justify-center">
              ⚖️
            </div>
          </div>
          <span className="text-white font-semibold">3가지 AI 도구 서비스</span>
        </div>
      </div>

      {/* Intro Section */}
      <div className="bg-blue-50 rounded-2xl p-8 text-center border border-blue-100">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          AI 기반 스마트 업무도구
        </h2>
        <p className="text-gray-700 leading-relaxed max-w-3xl mx-auto">
          충주시는 최신 인공지능 기술을 활용하여 공무원들의 업무 효율성을 높이고,
          <br />
          시민들에게 더 나은 행정서비스를 제공하기 위한 다양한 AI 도구들을 개발했습니다.
        </p>
      </div>

      {/* Tools Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {tools.map((tool, index) => (
          <Link
            key={index}
            to={tool.path}
            className="group bg-white rounded-2xl p-6 shadow-lg hover:shadow-2xl transition-all duration-300 hover:-translate-y-2 border border-gray-100"
          >
            {/* Icon */}
            <div className={`w-16 h-16 bg-gradient-to-br ${tool.color} rounded-2xl flex items-center justify-center text-3xl mb-4 group-hover:scale-110 transition-transform shadow-md`}>
              {tool.icon}
            </div>

            {/* Title */}
            <h3 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
              {tool.title}
            </h3>

            {/* Description */}
            <p className="text-gray-600 mb-4 leading-relaxed">
              {tool.description}
            </p>

            {/* Arrow */}
            <div className="flex items-center text-blue-600 font-semibold group-hover:gap-2 transition-all">
              <span>시작하기</span>
              <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </Link>
        ))}
      </div>

      {/* Contact Section */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-2xl shadow-xl p-10 text-center text-white">
        <h2 className="text-2xl font-bold mb-3">문의 및 지원</h2>
        <p className="text-blue-100 mb-6">
          AI 도구 사용에 대한 문의사항이나 기술 지원이 필요하시면 언제든지 연락해 주세요.
        </p>
        
        <div className="flex flex-wrap justify-center gap-4">
          <a
            href="mailto:storm8787@korea.kr"
            className="inline-flex items-center gap-2 bg-white text-blue-600 px-6 py-3 rounded-full font-semibold hover:bg-blue-50 transition-all hover:scale-105 shadow-md"
          >
            📧 이메일 문의
          </a>
          <a
            href="tel:0438505312"
            className="inline-flex items-center gap-2 bg-white text-blue-600 px-6 py-3 rounded-full font-semibold hover:bg-blue-50 transition-all hover:scale-105 shadow-md"
          >
            📞 전화 문의
          </a>
        </div>
      </div>

      {/* Features List */}
      <div className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100">
        <h3 className="text-xl font-bold text-gray-900 mb-6 text-center">
          💡 주요 특징
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl">🚀</span>
            </div>
            <h4 className="font-semibold text-gray-900 mb-2">빠른 처리</h4>
            <p className="text-sm text-gray-600">
              AI 기반 자동화로 업무 시간을 대폭 단축
            </p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl">🎯</span>
            </div>
            <h4 className="font-semibold text-gray-900 mb-2">높은 정확도</h4>
            <p className="text-sm text-gray-600">
              충주시 데이터 학습으로 맞춤형 결과 제공
            </p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl">💻</span>
            </div>
            <h4 className="font-semibold text-gray-900 mb-2">쉬운 사용</h4>
            <p className="text-sm text-gray-600">
              직관적인 인터페이스로 누구나 쉽게 사용
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}