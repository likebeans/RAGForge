/**
 * 认证服务
 * 管理用户登录状态和 Token
 */

const AUTH_TOKEN_KEY = 'yaoyan_token'
const AUTH_USER_KEY = 'yaoyan_user'

class AuthService {
  constructor() {
    this.token = localStorage.getItem(AUTH_TOKEN_KEY)
    this.user = this._loadUser()
    this.listeners = []
  }

  _loadUser() {
    try {
      const stored = localStorage.getItem(AUTH_USER_KEY)
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  }

  isAuthenticated() {
    return !!this.token && !!this.user
  }

  getToken() {
    return this.token
  }

  getUser() {
    return this.user
  }

  setAuth(token, user) {
    this.token = token
    this.user = user
    localStorage.setItem(AUTH_TOKEN_KEY, token)
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
    this._notifyListeners()
  }

  clearAuth() {
    this.token = null
    this.user = null
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(AUTH_USER_KEY)
    this._notifyListeners()
  }

  subscribe(listener) {
    this.listeners.push(listener)
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener)
    }
  }

  _notifyListeners() {
    this.listeners.forEach(listener => listener(this.isAuthenticated(), this.user))
  }
}

export const authService = new AuthService()
export default authService
