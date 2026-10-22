import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../lib/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const getErrorMessage = (error, fallback) => {
    const detail = error?.response?.data?.detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg || 'Erro de validaÃ§Ã£o').join(' | ');
    }
    if (typeof detail === 'string') {
      return detail;
    }
    if (detail && typeof detail === 'object') {
      return detail.msg || fallback;
    }
    return fallback;
  };

  useEffect(() => {
    const token = localStorage.getItem('dashflow_token');
    if (token) {
      api.get('/auth/me')
        .then(res => setUser(res.data))
        .catch(() => {
          localStorage.removeItem('dashflow_token');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    try {
      const { data } = await api.post('/auth/login', { email, password });
      localStorage.setItem('dashflow_token', data.access_token);
      
      // Buscar dados do usuário após login
      const userRes = await api.get('/auth/me');
      setUser(userRes.data);
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: getErrorMessage(error, 'Email ou senha incorretos')
      };
    }
  };

 const register = async (name, email, password) => {
  const payload = { name, email, password };

  try {
    await api.post('/auth/register', payload, {
      headers: { 'Content-Type': 'application/json' },
    });

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: getErrorMessage(error, 'Erro ao criar conta'),
    };
  }
};



  const logout = () => {
    setUser(null);
    localStorage.removeItem('dashflow_token');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#2563EB] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
