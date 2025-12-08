// src/pages/Index.tsx
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ToolCard } from "@/components/ToolCard";
import type { LucideIcon } from "lucide-react";
import {
  FileText,
  Award,
  BarChart3,
  Megaphone,
  FileEdit,
  MessageSquare,
  Sheet,
  MapPin,
  Languages,
  TrendingUp,
} from "lucide-react";

const Index = () => {
  const tools = [
    {
      icon: FileText,
      title: "보도자료 생성기",
      description: "AI 기반으로 전문적인 보도자료를 빠르게 작성합니다",
    },
    {
      icon: Award,
      title: "공적조서 생성기",
      description: "공무원 업적을 체계적으로 정리하여 공적조서를 생성합니다",
    },
    {
      icon: BarChart3,
      title: "빅데이터 분석기",
      description: "축제 및 행사 데이터를 분석하여 인사이트를 제공합니다",
    },
    {
      icon: Megaphone,
      title: "홍보문구 생성기",
      description: "카카오톡, SNS용 홍보 문구를 효과적으로 작성합니다",
    },
    {
      icon: FileEdit,
      title: "업무보고 생성기",
      description: "업무 보고서를 AI가 자동으로 작성해드립니다",
    },
    {
      icon: TrendingUp,
      title: "AI 통계분석 챗봇",
      description: "데이터를 업로드하여 대화형으로 분석합니다",
    },
    {
      icon: MessageSquare,
      title: "회의 요약기",
      description: "회의 내용을 요약하여 핵심만 정리합니다",
    },
    {
      icon: Sheet,
      title: "엑셀 취합기",
      description: "여러 엑셀 파일을 하나로 통합합니다",
    },
    {
      icon: MapPin,
      title: "주소-좌표 변환기",
      description: "주소를 위도/경도 좌표로 변환합니다",
    },
    {
      icon: Languages,
      title: "다국어 번역기",
      description: "문서를 여러 언어로 자동 번역합니다",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Hero */}
      <header
        id="home"
        className="bg-gradient-hero text-primary-foreground py-20 px-6"
      >
        <div className="max-w-6xl mx-auto">
          <div className="max-w-2xl space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary-foreground/10 rounded-full text-sm font-medium">
              <span className="w-2 h-2 bg-primary-foreground rounded-full animate-pulse" />
              충주시 AI 플랫폼
            </div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-[0.02em] leading-tight">
              더 가까이,
              <br />
              충주시 AI 연구
            </h1>
            <p className="text-lg text-primary-foreground/85 leading-relaxed">
              인공지능 기술로 행정업무를 혁신합니다.
              <br className="hidden sm:block" />
              충주시의 더 나은 미래를 위한 AI 도구를 만나보세요.
            </p>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-6xl mx-auto px-6 py-16">
        {/* 소개 */}
        <section id="about" className="mb-16">
          <div className="text-center max-w-2xl mx-auto space-y-4 mb-12">
            <h2 className="text-2xl md:text-3xl font-bold text-foreground tracking-tight">
              AI 기반 행정업무 지원 플랫폼
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              충주시 공무원들의 업무 효율성을 높이기 위해 개발된 AI 도구 모음입니다.<br/>
              보도자료 작성부터 데이터 분석까지, 필요한 모든 도구를 제공합니다.
            </p>
          </div>

          {/* 도구 카드 */}
          <div
            id="tools"
            className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch"
          >
            {tools.map((tool, index) => (
              <div
                key={index}
                className="h-full animate-fade-in"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <ToolCard
                  icon={tool.icon}
                  title={tool.title}
                  description={tool.description}
                />
              </div>
            ))}
          </div>
        </section>

        
      </main>

      <Footer />
    </div>
  );
};

export default Index;
