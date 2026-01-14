import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

const tools = [
  {
    icon: "📰",
    title: "충주시 뉴스",
    description: "충주시 관련 뉴스를 자동 수집하고 AI가 요약합니다",
    path: "/news",
  },
  {
    icon: "📝",
    title: "보도자료 생성기",
    description: "GPT 기반 자동 보도자료 작성 시스템",
    path: "/press-release",
  },
  {
    icon: "⚖️",
    title: "선거법 챗봇",
    description: "선거법 관련 질의 응답을 빠르고 정확하게 지원합니다",
    path: "/election-law",
  },
];

export default function Dashboard() {
  const scrollToTools = () => {
    const el = document.getElementById("tools");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="space-y-10">
      {/* Hero */}
      <section className="hero-surface rounded-3xl p-8 sm:p-10">
        <div className="max-w-3xl">
          <p className="badge mb-5">CJ · Smart Admin</p>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            충주를 위한 AI 행정 서비스
          </h1>

          <p className="mt-4 text-base sm:text-lg text-white/75 whitespace-pre-line">
            인공지능 기술을 활용한 스마트 행정 서비스로{"\n"}
            더 빠르고 정확한 시민 서비스를 제공합니다.
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={scrollToTools}
              className="btn-primary inline-flex items-center gap-2"
            >
              서비스 시작 <ArrowRight className="h-4 w-4" />
            </button>

            <p className="text-sm text-white/60">
              아래 카드에서 원하는 서비스를 선택할 수 있습니다.
            </p>
          </div>
        </div>
      </section>

      {/* Tools Grid (카드형 대시보드 유지) */}
      <section id="tools" className="scroll-mt-10">
        <div className="mb-5">
          <h2 className="text-xl sm:text-2xl font-bold text-white">
            서비스 목록
          </h2>
          <p className="mt-1 text-sm text-white/60">
            필요한 AI 업무 도구를 선택하여 바로 시작하세요.
          </p>
        </div>

        <div className="grid gap-4 sm:gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {tools.map((tool) => (
            <Link
              key={tool.title}
              to={tool.path}
              className="tool-card group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="icon-chip">{tool.icon}</div>
                <div className="opacity-60 group-hover:opacity-100 transition-opacity">
                  <ArrowRight className="h-5 w-5 text-white" />
                </div>
              </div>

              <h3 className="mt-5 text-lg font-bold text-white">
                {tool.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-white/70">
                {tool.description}
              </p>

              <div className="mt-6 text-sm font-semibold text-white/80 group-hover:text-white">
                바로 시작하기
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Contact (가로길이 짧음 해결: full-width 카드로) */}
      <section className="contact-surface rounded-3xl p-8 sm:p-10 w-full">
        <div className="flex flex-col lg:flex-row gap-8 lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <h2 className="text-2xl font-extrabold text-white">
              문의 및 지원
            </h2>
            <p className="mt-3 text-white/70 leading-relaxed">
              AI 도구 사용 중 문의사항이나 기술 지원이 필요하시면 아래 채널로 연락해 주세요.
              업무 환경에 맞춰 빠르게 지원하겠습니다.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <a
              href="mailto:storm8787@korea.kr"
              className="btn-ghost"
            >
              이메일 문의
            </a>
            <a
              href="tel:043-000-0000"
              className="btn-ghost"
            >
              전화 문의
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
