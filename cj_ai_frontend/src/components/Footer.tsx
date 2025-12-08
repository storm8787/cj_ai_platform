import { Mail, Phone, MapPin } from "lucide-react";
import logo from "@/assets/logo.png";

export const Footer = () => {
  return (
    <footer className="bg-card border-t border-border">
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_1.5fr_1fr] gap-12">
          {/* Logo & Description */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <img 
                src={logo} 
                alt="충주시 로고" 
                className="h-10 w-10 object-contain"
              />
              <div className="flex flex-col">
                <span className="text-base font-semibold text-foreground">
                  충주시 AI 연구
                </span>
                <span className="text-[11px] text-muted-foreground tracking-wide">
                  CHUNGJU AI RESEARCH
                </span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              AI 기술로 행정업무를 혁신하는<br />
              충주시 공무원 전용 플랫폼
            </p>
          </div>

          {/* Quick Links */}
          <div className="hidden md:block">
            
          </div>

          {/* Contact Info */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-foreground">연락처</h3>
            <ul className="space-y-3">
              <li className="flex items-start gap-3">
                <MapPin className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                <span className="text-sm text-muted-foreground">
                  충청북도 충주시 으뜸로 21
                </span>
              </li>
              <li className="flex items-center gap-3">
                <Phone className="w-4 h-4 text-muted-foreground shrink-0" />
                <span className="text-sm text-muted-foreground">
                  043-850-5312
                </span>
              </li>
              <li className="flex items-center gap-3">
                <Mail className="w-4 h-4 text-muted-foreground shrink-0" />
                <span className="text-sm text-muted-foreground">
                  storm8787@korea.kr
                </span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-10 pt-6 border-t border-border">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            <p className="text-xs text-muted-foreground">
              © 2025 충주시청. All rights reserved.
            </p>
            
          </div>
        </div>
      </div>
    </footer>
  );
};
