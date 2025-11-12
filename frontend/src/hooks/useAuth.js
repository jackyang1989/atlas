import { useEffect, useState } from 'react';
import { authAPI } from '../services/api';

export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      // 验证 token 有效性
      authAPI
        .getCurrentUser()
        .then((response) => {
          setUser(response.data);
        })
        .catch(() => {
          localStorage.removeItem('access_token');
          setUser(null);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const login = (username, password) => {
    return authAPI
      .login(username, password)
      .then((response) => {
        const { access_token, user: userData } = response.data;
        localStorage.setItem('access_token', access_token);
        setUser(userData);
        return userData;
      });
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setUser(null);
  };

  return { user, loading, login, logout };
}
