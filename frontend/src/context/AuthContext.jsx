import { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // 페이지 로드 시 토큰 검증
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      setLoading(false);
      setIsAuthenticated(false);
      return;
    }

    try {
      const response = await api.get('/api/auth/verify', {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.data.valid) {
        setUser(response.data.user);
        setIsAuthenticated(true);
      } else {
        // 토큰 만료 시 refresh 시도
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          await refreshAccessToken(refreshToken);
        } else {
          logout();
        }
      }
    } catch (error) {
      console.error('인증 확인 실패:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await api.post('/api/auth/login', { email, password });
      
      if (response.data.success) {
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('refresh_token', response.data.refresh_token);
        setUser(response.data.user);
        setIsAuthenticated(true);
        return { success: true };
      } else {
        return { success: false, message: response.data.message };
      }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '로그인 중 오류가 발생했습니다.' 
      };
    }
  };

  const signup = async (email, password) => {
    try {
      const response = await api.post('/api/auth/signup', { email, password });
      
      if (response.data.success) {
        // 이메일 확인이 필요한 경우
        if (!response.data.access_token) {
          return { 
            success: true, 
            needEmailConfirm: true,
            message: response.data.message 
          };
        }
        
        // 바로 로그인 처리
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('refresh_token', response.data.refresh_token);
        setUser(response.data.user);
        setIsAuthenticated(true);
        return { success: true };
      } else {
        return { success: false, message: response.data.message };
      }
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || '회원가입 중 오류가 발생했습니다.' 
      };
    }
  };

  const logout = async () => {
    const token = localStorage.getItem('access_token');
    
    try {
      if (token) {
        await api.post('/api/auth/logout', null, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }
    } catch (error) {
      console.error('로그아웃 API 오류:', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  const refreshAccessToken = async (refreshToken) => {
    try {
      const response = await api.post('/api/auth/refresh', { refresh_token: refreshToken });
      
      if (response.data.success) {
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('refresh_token', response.data.refresh_token);
        setUser(response.data.user);
        setIsAuthenticated(true);
        return true;
      }
    } catch (error) {
      console.error('토큰 갱신 실패:', error);
    }
    
    logout();
    return false;
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    signup,
    logout,
    checkAuth
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}