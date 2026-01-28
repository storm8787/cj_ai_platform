import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { Home, Info, Settings, MessageSquare, User, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const navItemClass = ({ isActive }) =>
    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition
     ${
       isActive
         ? "bg-cyan-500/15 text-cyan-300"
         : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
     }`;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* ================= Header ================= */}
      <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          {/* Left: Logo */}
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => navigate("/")}
          >
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center">
              <Home className="text-cyan-300" />
            </div>
            <div>
              <div className="font-bold text-white">충주시 AI 플랫폼</div>
              <div className="text-xs text-slate-400">Chungju AI Platform</div>
            </div>
          </div>

          {/* Right: User + Menu (Card) */}
          <div className="flex flex-col items-end">
            <div className="bg-slate-900/40 border border-slate-800 rounded-2xl px-3 py-2 backdrop-blur-xl">
              {/* User Row */}
              <div className="flex items-center justify-end gap-2">
                <div className="w-8 h-8 rounded-lg bg-slate-800/70 flex items-center justify-center">
                  <User size={16} className="text-slate-300" />
                </div>
                <span className="text-sm text-slate-200">{user?.email}</span>
                <button
                  onClick={handleLogout}
                  className="ml-2 flex items-center gap-1.5 px-2 py-1 text-sm font-medium
                             text-slate-300 hover:text-red-300
                             rounded-lg hover:bg-slate-800/50 transition-all"
                >
                  <LogOut size={16} />
                  로그아웃
                </button>
              </div>

              {/* Divider */}
              <div className="my-2 h-px bg-slate-800" />

              {/* Menu Row */}
              <nav className="hidden md:flex items-center gap-1 justify-end">
                <NavLink to="/" className={navItemClass}>
                  <Home size={16} />
                  홈으로
                </NavLink>
                <NavLink to="/about" className={navItemClass}>
                  <Info size={16} />
                  시스템 소개
                </NavLink>
                <NavLink to="/services" className={navItemClass}>
                  <Settings size={16} />
                  AI 서비스
                </NavLink>
                <NavLink to="/community" className={navItemClass}>
                  <MessageSquare size={16} />
                  소통공간
                </NavLink>
              </nav>
            </div>
          </div>
        </div>
      </header>

      {/* ================= Main ================= */}
      <main>
        <Outlet />
      </main>
    </div>
  );
}
