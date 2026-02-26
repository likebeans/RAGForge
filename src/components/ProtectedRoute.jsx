/**
 * 路由保护组件
 * 未登录用户重定向到登录页
 */

import { Navigate, useLocation } from 'react-router-dom'
import { authService } from '../services/auth'

export default function ProtectedRoute({ children }) {
  const location = useLocation()
  const isAuth = authService.isAuthenticated()
  
  if (!isAuth) {
    console.log('[ProtectedRoute] Redirecting to login. Location:', location.pathname)
    console.log('[ProtectedRoute] Auth state:', { token: authService.getToken(), user: authService.getUser() })
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  
  return children
}
