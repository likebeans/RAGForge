import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Database,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  FileText,
  BookOpen,
  MoreVertical,
  MessageSquare,
  TrendingUp,
  Clock,
  ChevronRight
} from 'lucide-react'
import apiClient from '../services/api'

export default function KnowledgeOverview() {
  const navigate = useNavigate()
  const [knowledgeBases, setKnowledgeBases] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  
  // 创建知识库对话框
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [newKbName, setNewKbName] = useState('')
  const [newKbDesc, setNewKbDesc] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  
  // 删除确认
  const [deleteTarget, setDeleteTarget] = useState(null)

  // 统计数据
  const [stats, setStats] = useState({
    totalKbs: 0,
    totalDocs: 0,
    recentActivity: 0
  })

  useEffect(() => {
    loadKnowledgeBases()
  }, [])

  const loadKnowledgeBases = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.listKnowledgeBases()
      const kbs = result.items || []
      setKnowledgeBases(kbs)
      
      // 计算统计
      const totalDocs = kbs.reduce((sum, kb) => sum + (kb.document_count || 0), 0)
      setStats({
        totalKbs: kbs.length,
        totalDocs,
        recentActivity: kbs.length > 0 ? Math.min(kbs.length * 3, 15) : 0
      })
    } catch (err) {
      setError('加载知识库失败: ' + err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const createKnowledgeBase = async () => {
    if (!newKbName.trim()) {
      setError('请输入知识库名称')
      return
    }
    setIsCreating(true)
    try {
      await apiClient.createKnowledgeBase(newKbName.trim(), newKbDesc.trim())
      setShowCreateDialog(false)
      setNewKbName('')
      setNewKbDesc('')
      await loadKnowledgeBases()
    } catch (err) {
      setError('创建知识库失败: ' + err.message)
    } finally {
      setIsCreating(false)
    }
  }

  const deleteKnowledgeBase = async (id) => {
    try {
      await apiClient.deleteKnowledgeBase(id)
      setDeleteTarget(null)
      await loadKnowledgeBases()
    } catch (err) {
      setError('删除知识库失败: ' + err.message)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="p-6">
      {/* 页头 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">知识库总览</h1>
          <p className="text-gray-500 mt-1">管理和监控所有知识库的状态</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadKnowledgeBases}
            disabled={isLoading}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setShowCreateDialog(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-4 h-4" />
            新建知识库
          </button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">知识库总数</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.totalKbs}</p>
            </div>
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
              <Database className="w-6 h-6 text-primary-600" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">文档总数</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.totalDocs}</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">近期活动</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.recentActivity}</p>
            </div>
            <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-amber-600" />
            </div>
          </div>
        </div>
      </div>

      {/* 知识库列表 */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">所有知识库</h2>
        </div>
        
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : knowledgeBases.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <BookOpen className="w-12 h-12 text-gray-300 mb-4" />
            <p className="text-gray-500 mb-2">还没有知识库</p>
            <p className="text-sm text-gray-400">点击上方按钮创建第一个知识库</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {knowledgeBases.map(kb => (
              <div
                key={kb.id}
                className="px-6 py-4 hover:bg-gray-50 cursor-pointer flex items-center justify-between group"
                onClick={() => navigate(`/knowledge/docs?kb=${kb.id}`)}
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
                    <Database className="w-6 h-6 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{kb.name}</h3>
                    <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <FileText className="w-3.5 h-3.5" />
                        {kb.document_count || 0} 个文档
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {formatDate(kb.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteTarget(kb)
                    }}
                    className="opacity-0 group-hover:opacity-100 p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-gray-500" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="fixed bottom-4 right-4 max-w-md p-4 bg-red-50 border border-red-200 rounded-lg shadow-lg">
          <p className="text-sm text-red-700">{error}</p>
          <button onClick={() => setError(null)} className="absolute top-2 right-2 text-red-400 hover:text-red-600">×</button>
        </div>
      )}

      {/* 创建知识库对话框 */}
      {showCreateDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">新建知识库</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  知识库名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newKbName}
                  onChange={(e) => setNewKbName(e.target.value)}
                  placeholder="例如：产品文档"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  value={newKbDesc}
                  onChange={(e) => setNewKbDesc(e.target.value)}
                  placeholder="简要描述知识库的用途..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateDialog(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                取消
              </button>
              <button
                onClick={createKnowledgeBase}
                disabled={isCreating || !newKbName.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {isCreating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 删除确认对话框 */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">确认删除</h3>
            <p className="text-gray-600 mb-6">
              确定要删除知识库 <span className="font-medium">"{deleteTarget.name}"</span> 吗？
              此操作不可恢复。
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                取消
              </button>
              <button
                onClick={() => deleteKnowledgeBase(deleteTarget.id)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
