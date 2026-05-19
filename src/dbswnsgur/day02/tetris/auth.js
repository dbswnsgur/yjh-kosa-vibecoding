const API_BASE = '/api';

const Auth = {
  getAccessToken() {
    return localStorage.getItem('access_token');
  },

  getRefreshToken() {
    return localStorage.getItem('refresh_token');
  },

  getUsername() {
    return localStorage.getItem('username');
  },

  _setTokens(accessToken, refreshToken) {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  },

  clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('username');
  },

  isLoggedIn() {
    return !!this.getAccessToken();
  },

  async register(email, username, password) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '회원가입에 실패했습니다');
    return data;
  },

  async login(email, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '로그인에 실패했습니다');
    this._setTokens(data.access_token, data.refresh_token);
    localStorage.setItem('username', data.username);
    return data;
  },

  async refreshTokens() {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        this.clearTokens();
        return false;
      }
      const data = await res.json();
      this._setTokens(data.access_token, data.refresh_token);
      localStorage.setItem('username', data.username);
      return true;
    } catch {
      return false;
    }
  },

  async logout() {
    const refreshToken = this.getRefreshToken();
    if (refreshToken) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch {}
    }
    this.clearTokens();
  },

  // 백엔드 서버 가용 여부 확인 (세션 내 캐싱)
  async checkBackend() {
    const cached = sessionStorage.getItem('backend_ok');
    if (cached !== null) return cached === '1';
    try {
      const ctrl = new AbortController();
      setTimeout(() => ctrl.abort(), 3000);
      const res = await fetch(`${API_BASE}/health`, { signal: ctrl.signal });
      const ok = res.ok;
      sessionStorage.setItem('backend_ok', ok ? '1' : '0');
      return ok;
    } catch {
      sessionStorage.setItem('backend_ok', '0');
      return false;
    }
  },

  // 401 시 자동으로 토큰 갱신 후 재시도
  async fetchWithAuth(url, options = {}) {
    const req = () =>
      fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.getAccessToken()}`,
          ...options.headers,
        },
      });

    let res = await req();
    if (res.status === 401) {
      const ok = await this.refreshTokens();
      if (ok) {
        res = await req();
      } else {
        this.clearTokens();
        window.location.href = '/';
        return null;
      }
    }
    return res;
  },
};
