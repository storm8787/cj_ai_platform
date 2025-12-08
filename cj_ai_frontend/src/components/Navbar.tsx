import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import logo from "@/assets/logo.png";

export const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const menuItems = [
    { name: "홈", href: "#home" },
    { name: "AI 도구", href: "#tools" },
    { name: "소개", href: "#about" },
    { name: "문의", href: "#contact" },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-card/98 backdrop-blur-sm border-b border-border">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo Section */}
          <div className="flex items-center gap-3">
            <img 
              src={logo} 
              alt="충주시 로고" 
              className="h-9 w-9 object-contain"
            />
            <div className="flex flex-col">
              <span className="text-base font-semibold text-foreground tracking-tight">
                충주시 AI 연구
              </span>
              <span className="text-[11px] text-muted-foreground tracking-wide">
                CHUNGJU AI RESEARCH
              </span>
            </div>
          </div>

          {/* Desktop Menu */}
          <div className="hidden md:flex items-center gap-1">
            {menuItems.map((item) => (
              <a
                key={item.name}
                href={item.href}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                {item.name}
              </a>
            ))}
            <Button size="sm" className="ml-4">
              시작하기
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden p-2 rounded-md text-foreground hover:bg-secondary transition-colors"
            aria-label="메뉴 열기"
          >
            {isMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-border">
            <div className="flex flex-col gap-1">
              {menuItems.map((item) => (
                <a
                  key={item.name}
                  href={item.href}
                  onClick={() => setIsMenuOpen(false)}
                  className="px-4 py-3 text-sm font-medium text-foreground hover:bg-secondary rounded-md transition-colors"
                >
                  {item.name}
                </a>
              ))}
              <div className="pt-3 px-4">
                <Button className="w-full">
                  시작하기
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};
