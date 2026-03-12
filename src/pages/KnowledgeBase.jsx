import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Database,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  FileText,
  Upload,
  X,
  CheckCircle,
  AlertCircle,
  BookOpen,
  MoreVertical,
  FolderOpen
} from 'lucide-react'
import backendClient from '../services/backend'

export default function KnowledgeBase() {
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
  
  // 当前选中的知识库（查看详情）
  const [selectedKb, setSelectedKb] = useState(null)
  const [documents, setDocuments] = useState([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  
  // 上传文件
  const [uploadingFiles, setUploadingFiles] = useState([])

  useEffect(() => {
    loadKnowledgeBases()
  }, [])

  const loadKnowledgeBases = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await backendClient.listKnowledgeBases()
      setKnowledgeBases(result.items || [])
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
      await backendClient.createKnowledgeBase(newKbName.trim(), newKbDesc.trim())
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
      await backendClient.deleteKnowledgeBase(id)
      setDeleteTarget(null)
      if (selectedKb?.id === id) {
        setSelectedKb(null)
        setDocuments([])
      }
      await loadKnowledgeBases()
    } catch (err) {
      setError('删除知识库失败: ' + err.message)
    }
  }

  const selectKnowledgeBase = async (kb) => {
    setSelectedKb(kb)
    setLoadingDocs(true)
    try {
      const result = await backendClient.listDocuments(kb.id)
      setDocuments(result.items || [])
    } catch (err) {
      setError('加载文档列表失败: ' + err.message)
    } finally {
      setLoadingDocs(false)
    }
  }

  const handleFileUpload = async (files) => {
    if (!selectedKb) return
    
    const newFiles = Array.from(files).map(file => ({
      id: Date.now() + Math.random(),
      name: file.name,
      file,
      status: 'uploading',
      progress: 0,
    }))
    
    setUploadingFiles(prev => [...prev, ...newFiles])
    
    for (const fileItem of newFiles) {
      try {
        await backendClient.uploadDocument(selectedKb.id, fileItem.file)
        setUploadingFiles(prev =>
          prev.map(f => f.id === fileItem.id ? { ...f, status: 'success' } : f)
        )
        // 刷新文档列表
        const result = await backendClient.listDocuments(selectedKb.id)
        setDocuments(result.items || [])
      } catch (err) {
        setUploadingFiles(prev =>
          prev.map(f => f.id === fileItem.id ? { ...f, status: 'error', error: err.message } : f)
        )
      }
    }
    
    // 3秒后清除已完成的上传
    setTimeout(() => {
      setUploadingFiles(prev => prev.filter(f => f.status === 'uploading'))
    }, 3000)
  }

  const deleteDocument = async (docId) => {
    try {
      await backendClient.deleteDocument(docId)
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

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* 左侧知识库列表 */}
      <div className="w-80 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">知识库</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={loadKnowledgeBases}
                disabled={isLoading}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={() => setShowCreateDialog(true)}
                className="flex items-center gap-1 px-3 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700"
              >
                <Plus className="w-4 h-4" />
                新建
              </button>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : knowledgeBases.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center px-4">
              <BookOpen className="w-12 h-12 text-gray-300 mb-4" />
              <p className="text-gray-500 mb-2">还没有知识库</p>
              <p className="text-sm text-gray-400">点击上方按钮创建第一个知识库</p>
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {knowledgeBases.map(kb => (
                <div
                  key={kb.id}
                  onClick={() => selectKnowledgeBase(kb)}
                  className={`group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedKb?.id === kb.id
                      ? 'bg-primary-50 border border-primary-200'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    selectedKb?.id === kb.id ? 'bg-primary-100' : 'bg-gray-100'
                  }`}>
                    <Database className={`w-5 h-5 ${
                      selectedKb?.id === kb.id ? 'text-primary-600' : 'text-gray-500'
                    }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{kb.name}</p>
                    <p className="text-xs text-gray-500">
                      {kb.document_count || 0} 个文档
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteTarget(kb)
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 右侧文档列表 */}
      <div className="flex-1 bg-gray-50 flex flex-col">
        {selectedKb ? (
          <>
            {/* 头部 */}
            <div className="p-6 bg-white border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">{selectedKb.name}</h1>
                  {selectedKb.description && (
                    <p className="text-sm text-gray-500 mt-1">{selectedKb.description}</p>
                  )}
                </div>
                <label className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 cursor-pointer">
                  <Upload className="w-4 h-4" />
                  <span className="text-sm">上传文档</span>
                  <input
                    type="file"
                    multiple
                    accept=".md,.txt,.pdf,.docx"
                    className="hidden"
                    onChange={(e) => handleFileUpload(e.target.files)}
                  />
                </label>
              </div>
            </div>

            {/* 上传进度 */}
            {uploadingFiles.length > 0 && (
              <div className="p-4 bg-blue-50 border-b border-blue-100">
                <div className="space-y-2">
                  {uploadingFiles.map(file => (
                    <div key={file.id} className="flex items-center gap-3 text-sm">
                      {file.status === 'uploading' && (
                        <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                      )}
                      {file.status === 'success' && (
                        <CheckCircle className="w-4 h-4 text-green-600" />
                      )}
                      {file.status === 'error' && (
                        <AlertCircle className="w-4 h-4 text-red-600" />
                      )}
                      <span className={file.status === 'error' ? 'text-red-600' : 'text-gray-700'}>
                        {file.name}
                      </span>
                      {file.status === 'error' && (
                        <span className="text-red-500 text-xs">{file.error}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 文档列表 */}
            <div className="flex-1 overflow-y-auto p-6">
              {loadingDocs ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                </div>
              ) : documents.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <FolderOpen className="w-16 h-16 text-gray-300 mb-4" />
                  <p className="text-gray-500 mb-2">暂无文档</p>
                  <p className="text-sm text-gray-400">上传文档后可在此处查看和管理</p>
                </div>
              ) : (
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">文档名称</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">分块数</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {documents.map(doc => (
                        <tr key={doc.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-3">
                              <FileText className="w-5 h-5 text-gray-400" />
                              <span className="text-sm font-medium text-gray-900 truncate max-w-[300px]">
                                {doc.title}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">{doc.chunk_count || 0}</td>
                          <td className="px-4 py-3">{getStatusBadge(doc.processing_status)}</td>
                          <td className="px-4 py-3 text-sm text-gray-500">{formatDate(doc.created_at)}</td>
                          <td className="px-4 py-3 text-right">
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
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Database className="w-16 h-16 text-gray-300 mb-4" />
            <p className="text-gray-500 mb-2">选择一个知识库</p>
            <p className="text-sm text-gray-400">在左侧选择或创建知识库以查看文档</p>
          </div>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="fixed bottom-4 right-4 max-w-md p-4 bg-red-50 border border-red-200 rounded-lg shadow-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-red-700">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">
            <X className="w-4 h-4" />
          </button>
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
              此操作不可恢复，知识库中的所有文档也将被删除。
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
