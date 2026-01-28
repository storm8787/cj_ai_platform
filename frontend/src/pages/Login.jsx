import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Mail, Lock, Eye, EyeOff, LogIn, UserPlus, AlertCircle, CheckCircle } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const { login, signup } = useAuth();
  
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // 유효성 검사
    if (!email || !password) {
      setError('이메일과 비밀번호를 입력해주세요.');
      return;
    }

    if (!isLoginMode) {
      if (password.length < 6) {
        setError('비밀번호는 6자 이상이어야 합니다.');
        return;
      }
      if (password !== confirmPassword) {
        setError('비밀번호가 일치하지 않습니다.');
        return;
      }
    }

    setLoading(true);

    try {
      if (isLoginMode) {
        // 로그인
        const result = await login(email, password);
        if (result.success) {
          navigate('/');
        } else {
          setError(result.message);
        }
      } else {
        // 회원가입
        const result = await signup(email, password);
        if (result.success) {
          if (result.needEmailConfirm) {
            setSuccess(result.message);
            setIsLoginMode(true);
          } else {
            navigate('/');
          }
        } else {
          setError(result.message);
        }
      }
    } catch (err) {
      setError('오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsLoginMode(!isLoginMode);
    setError('');
    setSuccess('');
    setConfirmPassword('');
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      {/* 배경 효과 */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl"></div>
      </div>

      <div className="relative w-full max-w-md">
        {/* 로고 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-cyan-500 rounded-2xl mb-4 shadow-lg shadow-cyan-500/30">
            <span className="text-3xl">🏛️</span>
          </div>
          <h1 className="text-2xl font-bold text-white">충주시 AI 플랫폼</h1>
          <p className="text-slate-400 mt-2">AI 기반 행정 업무 지원 서비스</p>
        </div>

        {/* 로그인/회원가입 폼 */}
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-white mb-6 text-center">
            {isLoginMode ? '로그인' : '회원가입'}
          </h2>

          {/* 에러 메시지 */}
          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400">
              <AlertCircle size={18} />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {/* 성공 메시지 */}
          {success && (
            <div className="mb-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg flex items-center gap-2 text-green-400">
              <CheckCircle size={18} />
              <span className="text-sm">{success}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 이메일 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                이메일
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="example@chungju.go.kr"
                  className="w-full pl-10 pr-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                />
              </div>
            </div>

            {/* 비밀번호 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                비밀번호
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-12 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* 비밀번호 확인 (회원가입 시) */}
            {!isLoginMode && (
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  비밀번호 확인
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>
            )}

            {/* 제출 버튼 */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-medium rounded-lg hover:from-cyan-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-slate-900 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  {isLoginMode ? <LogIn size={18} /> : <UserPlus size={18} />}
                  {isLoginMode ? '로그인' : '회원가입'}
                </>
              )}
            </button>
          </form>

          {/* 모드 전환 */}
          <div className="mt-6 text-center">
            <button
              onClick={toggleMode}
              className="text-sm text-slate-400 hover:text-cyan-400 transition-colors"
            >
              {isLoginMode ? (
                <>계정이 없으신가요? <span className="text-cyan-400">회원가입</span></>
              ) : (
                <>이미 계정이 있으신가요? <span className="text-cyan-400">로그인</span></>
              )}
            </button>
          </div>
        </div>

        {/* 푸터 */}
        <p className="text-center text-slate-500 text-sm mt-6">
          © 2026 충주시 AI 플랫폼
        </p>
      </div>
    </div>
  );
}