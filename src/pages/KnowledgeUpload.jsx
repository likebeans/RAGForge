import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  Database,
  Upload,
  FileText,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  ChevronDown,
  ArrowLeft,
  File,
  FileType,
  Trash2,
  Shield,
  Lock,
  Globe,
  Users,
  UserCheck
} from 'lucide-react'
import apiClient from '../services/api'

const ACCEPTED_TYPES = {
  'text/markdown': '.md',
  'text/plain': '.txt',
  'application/pdf': '.pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
}

const SENSITIVITY_LEVELS = [
  { value: 'public', label: '公开', icon: Globe, desc: '所有人可访问', color: 'green' },
  { value: 'restricted', label: '受限', icon: Lock, desc: '需要ACL权限才能访问', color: 'amber' },
]

const IDENTITY_STORAGE_KEY = 'ragforge_identity_config'

const getIdentityConfig = () => {
  try {
    const stored = localStorage.getItem(IDENTITY_STORAGE_KEY)
    if (stored) return JSON.parse(stored)
  } catch (e) {
    console.error('Failed to load identity config:', e)
  }
  return { users: [], roles: [], groups: [] }
}

export default function KnowledgeUpload() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const preselectedKbId = searchParams.get('kb')
  
  const [knowledgeBases, setKnowledgeBases] = useState([])
  const [selectedKbId, setSelectedKbId] = useState(preselectedKbId || '')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [kbMenuOpen, setKbMenuOpen] = useState(false)
  
  // 文件上传状态
  const [files, setFiles] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  
  // ACL 设置
  const [showAclSettings, setShowAclSettings] = useState(false)
  const [aclSettings, setAclSettings] = useState({
    sensitivity_level: 'public',
    acl_allow_users: [],
    acl_allow_roles: [],
    acl_allow_groups: [],
  })
  
  // 预配置的身份信息
  const [identityConfig, setIdentityConfig] = useState({ users: [], roles: [], groups: [] })

  useEffect(() => {
    loadKnowledgeBases()
    setIdentityConfig(getIdentityConfig())
  }, [])

  useEffect(() => {
    if (preselectedKbId) {
      setSelectedKbId(preselectedKbId)
    }
  }, [preselectedKbId])

  const loadKnowledgeBases = async () => {
    setIsLoading(true)
    try {
      const result = await apiClient.listKnowledgeBases()
      setKnowledgeBases(result.items || [])
      // 如果没有预选，选择第一个
      if (!preselectedKbId && result.items?.length > 0) {
        setSelectedKbId(result.items[0].id)
      }
    } catch (err) {
      setError('加载知识库失败: ' + err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFiles = Array.from(e.dataTransfer.files)
    addFiles(droppedFiles)
  }, [])

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files)
    addFiles(selectedFiles)
    e.target.value = '' // Reset input
  }

  const addFiles = (newFiles) => {
    const validFiles = newFiles.filter(file => {
      const ext = '.' + file.name.split('.').pop().toLowerCase()
      return ['.md', '.txt', '.pdf', '.docx'].includes(ext)
    })
    
    const fileItems = validFiles.map(file => ({
      id: Date.now() + Math.random(),
      file,
      name: file.name,
      size: file.size,
      status: 'pending', // pending, uploading, success, error
      progress: 0,
      error: null
    }))
    
    setFiles(prev => [...prev, ...fileItems])
  }

  const removeFile = (id) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  const uploadFiles = async () => {
    if (!selectedKbId) {
      setError('请先选择知识库')
      return
    }
    if (files.length === 0) {
      setError('请先添加文件')
      return
    }

    setIsUploading(true)
    
    // 构建 ACL 选项
    const aclOptions = showAclSettings ? {
      sensitivity_level: aclSettings.sensitivity_level,
      acl_allow_users: aclSettings.acl_allow_users,
      acl_allow_roles: aclSettings.acl_allow_roles,
      acl_allow_groups: aclSettings.acl_allow_groups,
    } : {}
    
    for (const fileItem of files.filter(f => f.status === 'pending')) {
      // 更新状态为上传中
      setFiles(prev => prev.map(f => 
        f.id === fileItem.id ? { ...f, status: 'uploading' } : f
      ))
      
      try {
        await apiClient.uploadDocumentWithACL(selectedKbId, fileItem.file, aclOptions)
        setFiles(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, status: 'success' } : f
        ))
      } catch (err) {
        setFiles(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, status: 'error', error: err.message } : f
        ))
      }
    }
    
    setIsUploading(false)
  }
  
  const addAclItem = (field, value) => {
    if (!value.trim()) return
    if (aclSettings[field].includes(value.trim())) return
    setAclSettings(prev => ({
      ...prev,
      [field]: [...prev[field], value.trim()]
    }))
  }

  const removeAclItem = (field, index) => {
    setAclSettings(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }))
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const getFileIcon = (filename) => {
    const ext = filename.split('.').pop().toLowerCase()
    const iconMap = {
      md: FileText,
      txt: FileText,
      pdf: FileType,
      docx: File
    }
    const Icon = iconMap[ext] || File
    return <Icon className="w-5 h-5" />
  }

  const selectedKb = knowledgeBases.find(kb => kb.id === selectedKbId)
  const pendingFiles = files.filter(f => f.status === 'pending')
  const completedFiles = files.filter(f => f.status === 'success')
  const errorFiles = files.filter(f => f.status === 'error')

  return (
    <div className="p-6">
      {/* 页头 */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate('/knowledge')}
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">上传文档</h1>
          <p className="text-gray-500 mt-1">将文档上传到知识库进行向量化处理</p>
        </div>
      </div>

      <div className="max-w-3xl">
        {/* 知识库选择 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            选择目标知识库
          </label>
          <div className="relative">
            <button
              onClick={() => setKbMenuOpen(!kbMenuOpen)}
              disabled={isLoading}
              className="w-full flex items-center gap-2 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 text-left"
            >
              <Database className="w-5 h-5 text-gray-500" />
              <span className="flex-1 truncate">
                {selectedKb?.name || '选择知识库...'}
              </span>
              <ChevronDown className="w-4 h-4 text-gray-400" />
            </button>
            {kbMenuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setKbMenuOpen(false)} />
                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
                  {knowledgeBases.map(kb => (
                    <button
                      key={kb.id}
                      onClick={() => {
                        setSelectedKbId(kb.id)
                        setKbMenuOpen(false)
                      }}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center gap-3 ${
                        selectedKbId === kb.id ? 'bg-primary-50 text-primary-600' : ''
                      }`}
                    >
                      <Database className="w-4 h-4" />
                      <div className="flex-1">
                        <p className="font-medium">{kb.name}</p>
                        {kb.description && (
                          <p className="text-xs text-gray-400 truncate">{kb.description}</p>
                        )}
                      </div>
                      <span className="text-xs text-gray-400">{kb.document_count || 0} 文档</span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* ACL 访问控制设置 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showAclSettings}
              onChange={(e) => setShowAclSettings(e.target.checked)}
              className="w-4 h-4 text-primary-600 rounded"
            />
            <Shield className="w-5 h-5 text-gray-500" />
            <span className="font-medium text-gray-700">设置文档访问控制（ACL）</span>
          </label>
          <p className="text-xs text-gray-400 ml-6 mt-1">
            配置后所有上传的文档将应用相同的访问控制规则
          </p>
          
          {showAclSettings && (
            <div className="mt-4 pl-6 space-y-4">
              {/* 敏感度级别 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">敏感度级别</label>
                <div className="flex gap-3">
                  {SENSITIVITY_LEVELS.map(level => {
                    const Icon = level.icon
                    const isSelected = aclSettings.sensitivity_level === level.value
                    return (
                      <button
                        key={level.value}
                        type="button"
                        onClick={() => setAclSettings(prev => ({ ...prev, sensitivity_level: level.value }))}
                        className={`flex-1 p-3 rounded-lg border-2 transition-colors ${
                          isSelected
                            ? level.color === 'green'
                              ? 'border-green-500 bg-green-50'
                              : 'border-amber-500 bg-amber-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Icon className={`w-5 h-5 ${
                            isSelected
                              ? level.color === 'green' ? 'text-green-600' : 'text-amber-600'
                              : 'text-gray-400'
                          }`} />
                          <span className={`font-medium ${isSelected ? 'text-gray-900' : 'text-gray-600'}`}>
                            {level.label}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1 text-left">{level.desc}</p>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* 受限时显示 ACL 配置 */}
              {aclSettings.sensitivity_level === 'restricted' && (
                <div className="space-y-4 pt-2 border-t border-gray-100">
                  <p className="text-sm text-amber-600 flex items-center gap-2">
                    <Lock className="w-4 h-4" />
                    受限文档需要配置访问白名单
                  </p>
                  
                  {/* 允许用户 */}
                  <div>
                    <label className="flex items-center gap-1 text-sm font-medium text-gray-700 mb-2">
                      <UserCheck className="w-4 h-4" />
                      允许访问的用户
                    </label>
                    {identityConfig.users.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {identityConfig.users.map(user => {
                          const isSelected = aclSettings.acl_allow_users.includes(user.id)
                          return (
                            <button
                              key={user.id}
                              type="button"
                              onClick={() => {
                                if (isSelected) {
                                  setAclSettings(prev => ({
                                    ...prev,
                                    acl_allow_users: prev.acl_allow_users.filter(u => u !== user.id)
                                  }))
                                } else {
                                  setAclSettings(prev => ({
                                    ...prev,
                                    acl_allow_users: [...prev.acl_allow_users, user.id]
                                  }))
                                }
                              }}
                              className={`px-3 py-1.5 rounded-lg border text-sm transition-colors ${
                                isSelected
                                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                                  : 'border-gray-200 hover:border-gray-300'
                              }`}
                            >
                              {user.name || user.id}
                            </button>
                          )
                        })}
                      </div>
                    ) : (
                      <div className="text-sm text-gray-400 p-3 bg-gray-50 rounded-lg">
                        暂无预配置用户，请先在 <a href="/admin/users" className="text-primary-600 hover:underline">用户与角色</a> 中添加
                      </div>
                    )}
                  </div>
                  
                  {/* 允许角色 */}
                  <div>
                    <label className="flex items-center gap-1 text-sm font-medium text-gray-700 mb-2">
                      <Shield className="w-4 h-4" />
                      允许访问的角色
                    </label>
                    {identityConfig.roles.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {identityConfig.roles.map(role => {
                          const isSelected = aclSettings.acl_allow_roles.includes(role)
                          return (
                            <button
                              key={role}
                              type="button"
                              onClick={() => {
                                if (isSelected) {
                                  setAclSettings(prev => ({
                                    ...prev,
                                    acl_allow_roles: prev.acl_allow_roles.filter(r => r !== role)
                                  }))
                                } else {
                                  setAclSettings(prev => ({
                                    ...prev,
                                    acl_allow_roles: [...prev.acl_allow_roles, role]
                                  }))
                                }
                              }}
                              className={`px-3 py-1.5 rounded-lg border text-sm transition-colors ${
                                isSelected
                                  ? 'border-purple-500 bg-purple-50 text-purple-700'
                                  : 'border-gray-200 hover:border-gray-300'
                              }`}
                            >
                              {role}
                            </button>
                          )
                        })}
                      </div>
                    ) : (
                      <div className="text-sm text-gray-400 p-3 bg-gray-50 rounded-lg">
                        暂无预配置角色，请先在 <a href="/admin/users" className="text-primary-600 hover:underline">用户与角色</a> 中添加
                      </div>
                    )}
                  </div>
                  
                  {/* 允许部门/组 */}
                  <div>
                    <label className="flex items-center gap-1 text-sm font-medium text-gray-700 mb-2">
                      <Users className="w-4 h-4" />
                      允许访问的部门/组
                    </label>
                    {identityConfig.groups.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {identityConfig.groups.map(group => {
                          const isSelected = aclSettings.acl_allow_groups.includes(group)
                          return (
                            <button
                              key={group}
                              type="button"
                              onClick={() => {
                                if (isSelected) {
                                  setAclSettings(prev => ({
                                    ...prev,
                                    acl_allow_groups: prev.acl_allow_groups.filter(g => g !== group)
                                  }))
                                } else {
                                  setAclSettings(prev => ({
                                    ...prev,
                                    acl_allow_groups: [...prev.acl_allow_groups, group]
                                  }))
                                }
                              }}
                              className={`px-3 py-1.5 rounded-lg border text-sm transition-colors ${
                                isSelected
                                  ? 'border-green-500 bg-green-50 text-green-700'
                                  : 'border-gray-200 hover:border-gray-300'
                              }`}
                            >
                              {group}
                            </button>
                          )
                        })}
                      </div>
                    ) : (
                      <div className="text-sm text-gray-400 p-3 bg-gray-50 rounded-lg">
                        暂无预配置部门，请先在 <a href="/admin/users" className="text-primary-600 hover:underline">用户与角色</a> 中添加
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 拖拽上传区域 */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`bg-white rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
            isDragging
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <div className="flex flex-col items-center">
            <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
              isDragging ? 'bg-primary-100' : 'bg-gray-100'
            }`}>
              <Upload className={`w-8 h-8 ${isDragging ? 'text-primary-600' : 'text-gray-400'}`} />
            </div>
            <p className="text-lg font-medium text-gray-900 mb-2">
              拖拽文件到此处上传
            </p>
            <p className="text-sm text-gray-500 mb-4">
              支持 .md, .txt, .pdf, .docx 格式
            </p>
            <label className="cursor-pointer">
              <span className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 inline-block">
                选择文件
              </span>
              <input
                type="file"
                multiple
                accept=".md,.txt,.pdf,.docx"
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>
          </div>
        </div>

        {/* 文件列表 */}
        {files.length > 0 && (
          <div className="mt-6 bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-medium text-gray-900">
                待上传文件 ({files.length})
              </h3>
              {pendingFiles.length > 0 && (
                <button
                  onClick={uploadFiles}
                  disabled={isUploading || !selectedKbId}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      上传中...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      开始上传
                    </>
                  )}
                </button>
              )}
            </div>
            <div className="divide-y divide-gray-100">
              {files.map(file => (
                <div key={file.id} className="px-6 py-3 flex items-center gap-4">
                  <div className={`${
                    file.status === 'success' ? 'text-green-500' :
                    file.status === 'error' ? 'text-red-500' :
                    file.status === 'uploading' ? 'text-blue-500' :
                    'text-gray-400'
                  }`}>
                    {file.status === 'uploading' ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : file.status === 'success' ? (
                      <CheckCircle className="w-5 h-5" />
                    ) : file.status === 'error' ? (
                      <AlertCircle className="w-5 h-5" />
                    ) : (
                      getFileIcon(file.name)
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                    <p className="text-xs text-gray-400">
                      {formatFileSize(file.size)}
                      {file.error && <span className="text-red-500 ml-2">{file.error}</span>}
                    </p>
                  </div>
                  {file.status === 'pending' && (
                    <button
                      onClick={() => removeFile(file.id)}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 上传统计 */}
        {(completedFiles.length > 0 || errorFiles.length > 0) && (
          <div className="mt-4 flex items-center gap-4 text-sm">
            {completedFiles.length > 0 && (
              <span className="text-green-600">
                <CheckCircle className="w-4 h-4 inline mr-1" />
                {completedFiles.length} 个文件上传成功
              </span>
            )}
            {errorFiles.length > 0 && (
              <span className="text-red-600">
                <AlertCircle className="w-4 h-4 inline mr-1" />
                {errorFiles.length} 个文件上传失败
              </span>
            )}
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
    </div>
  )
}
