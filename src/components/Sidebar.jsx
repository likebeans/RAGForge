import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  FilePlus,
  Database,
  BarChart3,
  FileStack,
  Upload,
  Users,
  ScrollText,
  Cpu,
  Settings,
  ChevronDown,
  ChevronRight,
  FlaskConical,
  Briefcase
} from 'lucide-react'

const menuItems = [
  {
    id: 'dashboard',
    label: '工作台',
    icon: LayoutDashboard,
    path: '/dashboard'
  },
  {
    id: 'chat',
    label: 'AI 对话',
    icon: MessageSquare,
    path: '/chat'
  },
  {
    id: 'data',
    label: '数据管理',
    icon: Database,
    path: '/data'
  },
  {
    id: 'reports',
    label: '报告中心',
    icon: FileText,
    children: [
      { id: 'report-list', label: '报告列表', icon: FileStack, path: '/reports' },
      {
        id: 'report-generation',
        label: '报告生成',
        icon: FilePlus,
        children: [
          { id: 'report-new', label: '新建报告', icon: FilePlus, path: '/reports/new' },
          { id: 'report-assistant', label: '报告生成助手', icon: MessageSquare, path: '/reports/assistant' }
        ]
      }
    ]
  },
  {
    id: 'knowledge',
    label: '知识库',
    icon: Database,
    children: [
      { id: 'kb-overview', label: '总览', icon: BarChart3, path: '/knowledge' },
      { id: 'kb-docs', label: '文档', icon: FileStack, path: '/knowledge/docs' },
      { id: 'kb-upload', label: '上传', icon: Upload, path: '/knowledge/upload' }
    ]
  },
  {
    id: 'admin',
    label: '管理',
    icon: Users,
    children: [
      { id: 'api-keys', label: 'API Key 管理', icon: Settings, path: '/admin/api-keys' },
      { id: 'users', label: '用户与角色', icon: Users, path: '/admin/users' },
      { id: 'audit', label: '审计日志', icon: ScrollText, path: '/admin/audit' },
      { id: 'models', label: '模型与策略', icon: Cpu, path: '/admin/models' }
    ]
  },
  {
    id: 'settings',
    label: '设置',
    icon: Settings,
    path: '/settings'
  }
]

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [expanded, setExpanded] = useState(['reports', 'knowledge', 'admin'])

  const toggleExpand = (id) => {
    setExpanded(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    )
  }

  const isActive = (path) => location.pathname === path

  const renderMenuItem = (item, level = 0) => {
    const hasChildren = item.children && item.children.length > 0
    const isExpanded = expanded.includes(item.id)
    const Icon = item.icon

    return (
      <div key={item.id}>
        <button
          onClick={() => {
            if (hasChildren) {
              toggleExpand(item.id)
            } else if (item.path) {
              navigate(item.path)
            }
          }}
          className={`w-full flex items-center justify-between px-4 py-2.5 text-sm rounded-lg transition-colors ${
            level === 0 ? '' : level === 1 ? 'pl-8' : 'pl-12'
          } ${
            isActive(item.path)
              ? 'bg-primary-50 text-primary-600 font-medium'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <div className="flex items-center gap-3">
            <Icon className="w-5 h-5" />
            <span>{item.label}</span>
          </div>
          {hasChildren && (
            isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
          )}
        </button>
        {hasChildren && isExpanded && (
          <div className="mt-1 space-y-1">
            {item.children.map(child => renderMenuItem(child, level + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-200 flex flex-col z-30">
      {/* Logo */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-gray-200">
        <div className="w-9 h-9 bg-primary-500 rounded-lg flex items-center justify-center">
          <FlaskConical className="w-5 h-5 text-white" />
        </div>
        <span className="text-lg font-bold text-primary-600">R&D AI Studio</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-1">
        {menuItems.map(item => renderMenuItem(item))}
      </nav>
    </aside>
  )
}
