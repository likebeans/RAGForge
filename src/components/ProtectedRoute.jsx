/**
 * 路由保护组件
 * 未登录用户重定向到登录页
 */

import { Navigate, useLocation } from 'react-router-dom'
import { authService } from '../services/auth'

export default function ProtectedRoute({ children }) {
  const location = useLocation()
  
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  
  return children
}
