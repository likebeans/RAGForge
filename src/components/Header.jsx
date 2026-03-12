import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Bell, HelpCircle, ChevronDown, Globe, LogOut, User } from 'lucide-react'
import { authService } from '../services/auth'
import { backendClient } from '../services/backend'

export default function Header() {
  const navigate = useNavigate()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const user = authService.getUser()
  const [searchText, setSearchText] = useState('')

  const handleLogout = () => {
    backendClient.logout()
    navigate('/login')
  }

  const getInitials = () => {
    if (!user?.display_name) return 'U'
    return user.display_name.slice(0, 2).toUpperCase()
  }

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      {/* 搜索框 */}
      <div className="w-full max-w-[560px] mx-auto">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="全局搜索..."
            className="w-full h-10 pl-10 pr-10 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          {searchText && (
            <button
              onClick={() => setSearchText('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 rounded p-1"
              aria-label="清除搜索"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* 右侧操作区 */}
      <div className="flex items-center gap-4">
        {/* 通知 */}
        <button className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>

        {/* 帮助 */}
        <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
          <HelpCircle className="w-5 h-5" />
        </button>

        {/* 语言切换 */}
        <button className="flex items-center gap-1 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg text-sm">
          <Globe className="w-4 h-4" />
          <span>EN</span>
          <ChevronDown className="w-4 h-4" />
        </button>

        {/* 用户菜单 */}
        <div className="relative">
          <button 
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 hover:bg-gray-100 rounded-lg p-1"
          >
            <div className="w-9 h-9 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-primary-600 font-medium text-sm">{getInitials()}</span>
            </div>
            <div className="text-left hidden sm:block">
              <p className="text-sm font-medium text-gray-700">{user?.display_name || user?.username}</p>
              <p className="text-xs text-gray-500">{user?.is_admin ? '管理员' : '用户'}</p>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
              <div className="px-4 py-2 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-700">{user?.display_name}</p>
                <p className="text-xs text-gray-500">{user?.username}</p>
              </div>
{/* [INTERNAL_ACTION: Timestamp reference via System Time]
    {{Echo:
    Action: Modified; Timestamp: 2026-03-12 09:32:18 +08:00; Reason: Hide personal settings from user menu;
    }}
    {{START MODIFICATIONS}} */}
              {/* <button
                onClick={() => { setShowUserMenu(false); navigate('/settings'); }}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                <User className="w-4 h-4" />
                个人设置
              </button> */}
{/* {{END MODIFICATIONS}} */}
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
              >
                <LogOut className="w-4 h-4" />
                退出登录
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
