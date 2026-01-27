import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  Database,
  FileText,
  Trash2,
  RefreshCw,
  Loader2,
  Search,
  ChevronDown,
  Eye,
  Clock,
  FolderOpen,
  ArrowLeft
} from 'lucide-react'
import apiClient from '../services/api'

export default function KnowledgeDocs() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const selectedKbId = searchParams.get('kb')
  
  const [knowledgeBases, setKnowledgeBases] = useState([])
  const [currentKb, setCurrentKb] = useState(null)
  const [documents, setDocuments] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [kbMenuOpen, setKbMenuOpen] = useState(false)

  useEffect(() => {
    loadKnowledgeBases()
  }, [])

  useEffect(() => {
    if (selectedKbId && knowledgeBases.length > 0) {
      const kb = knowledgeBases.find(k => k.id === selectedKbId)
      if (kb) {
        setCurrentKb(kb)
        loadDocuments(kb.id)
      }
    } else if (knowledgeBases.length > 0 && !selectedKbId) {
      // 默认选择第一个知识库
      const firstKb = knowledgeBases[0]
      setCurrentKb(firstKb)
      navigate(`/knowledge/docs?kb=${firstKb.id}`, { replace: true })
    }
  }, [selectedKbId, knowledgeBases])

  const loadKnowledgeBases = async () => {
    setIsLoading(true)
    try {
      const result = await apiClient.listKnowledgeBases()
      setKnowledgeBases(result.items || [])
    } catch (err) {
      setError('加载知识库失败: ' + err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const loadDocuments = async (kbId) => {
    setLoadingDocs(true)
    try {
      const result = await apiClient.listDocuments(kbId)
      setDocuments(result.items || [])
    } catch (err) {
      setError('加载文档失败: ' + err.message)
    } finally {
      setLoadingDocs(false)
    }
  }

  const selectKnowledgeBase = (kb) => {
    setCurrentKb(kb)
    setKbMenuOpen(false)
    navigate(`/knowledge/docs?kb=${kb.id}`)
  }

  const deleteDocument = async (docId) => {
    if (!confirm('确定要删除这个文档吗？')) return
    try {
      await apiClient.deleteDocument(docId)
      setDocuments(prev => prev.filter(d => d.id !== docId))
    } catch (err) {
      setError('删除文档失败: ' + err.message)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusBadge = (status) => {
    const statusMap = {
      completed: { text: '已完成', className: 'bg-green-100 text-green-700' },
      processing: { text: '处理中', className: 'bg-blue-100 text-blue-700' },
      pending: { text: '等待中', className: 'bg-gray-100 text-gray-700' },
      failed: { text: '失败', className: 'bg-red-100 text-red-700' },
    }
    const config = statusMap[status] || statusMap.pending
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${config.className}`}>
        {config.text}
      </span>
    )
  }

  const filteredDocs = documents.filter(doc =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="p-6">
      {/* 页头 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/knowledge')}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">文档管理</h1>
            <p className="text-gray-500 mt-1">查看和管理知识库中的文档</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/knowledge/upload')}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          上传文档
        </button>
      </div>

      {/* 知识库选择和搜索 */}
      <div className="flex items-center gap-4 mb-6">
        {/* 知识库选择器 */}
        <div className="relative">
          <button
            onClick={() => setKbMenuOpen(!kbMenuOpen)}
            className="flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 min-w-[240px]"
          >
            <Database className="w-4 h-4 text-gray-500" />
            <span className="flex-1 text-left truncate">
              {currentKb?.name || '选择知识库'}
            </span>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>
          {kbMenuOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setKbMenuOpen(false)} />
              <div className="absolute top-full left-0 mt-1 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
                {knowledgeBases.map(kb => (
                  <button
                    key={kb.id}
                    onClick={() => selectKnowledgeBase(kb)}
                    className={`w-full px-4 py-2.5 text-left hover:bg-gray-50 flex items-center gap-3 ${
                      currentKb?.id === kb.id ? 'bg-primary-50 text-primary-600' : ''
                    }`}
                  >
                    <Database className="w-4 h-4" />
                    <span className="truncate">{kb.name}</span>
                    <span className="text-xs text-gray-400 ml-auto">{kb.document_count || 0}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* 搜索框 */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索文档..."
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <button
          onClick={() => currentKb && loadDocuments(currentKb.id)}
          disabled={loadingDocs}
          className="p-2.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
        >
          <RefreshCw className={`w-5 h-5 ${loadingDocs ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* 文档列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : !currentKb ? (
        <div className="flex flex-col items-center justify-center py-12 text-center bg-white rounded-xl border border-gray-200">
          <Database className="w-12 h-12 text-gray-300 mb-4" />
          <p className="text-gray-500">请选择一个知识库</p>
        </div>
      ) : loadingDocs ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : filteredDocs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center bg-white rounded-xl border border-gray-200">
          <FolderOpen className="w-12 h-12 text-gray-300 mb-4" />
          <p className="text-gray-500 mb-2">
            {searchQuery ? '没有找到匹配的文档' : '暂无文档'}
          </p>
          <p className="text-sm text-gray-400">
            {searchQuery ? '尝试其他搜索词' : '点击上传按钮添加文档'}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">文档名称</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">分块数</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredDocs.map(doc => (
                <tr key={doc.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900 truncate max-w-[400px]">
                        {doc.title}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{doc.chunk_count || 0}</td>
                  <td className="px-6 py-4">{getStatusBadge(doc.processing_status)}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{formatDate(doc.created_at)}</td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => deleteDocument(doc.id)}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="fixed bottom-4 right-4 max-w-md p-4 bg-red-50 border border-red-200 rounded-lg shadow-lg">
          <p className="text-sm text-red-700">{error}</p>
          <button onClick={() => setError(null)} className="absolute top-2 right-2 text-red-400 hover:text-red-600">×</button>
        </div>
      )}
    </div>
  )
}
