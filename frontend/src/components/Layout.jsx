export default function Layout({ children }) {
  return (
    <div className="min-h-screen app-bg">
      <main className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-10">
        {children}
      </main>

      <footer className="mt-16 border-t border-white/10">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-8 text-center">
          <p className="text-sm text-white/70">
            © 2026 충주시 · AI 행정 서비스
          </p>
          <p className="mt-1 text-xs text-white/50">
            인공지능 기반 스마트 행정 서비스로 더 빠르고 정확한 시민 서비스를 제공합니다.
          </p>
        </div>
      </footer>
    </div>
  );
}
