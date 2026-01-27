import { useState, useEffect } from 'react'
import {
  Key,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  Copy,
  CheckCircle,
  AlertCircle,
  Eye,
  EyeOff,
  Clock,
  Shield,
  Database,
  X,
  ChevronDown,
  Info
} from 'lucide-react'
import apiClient from '../services/api'

const ROLES = [
  { value: 'admin', label: '管理员', desc: '全部权限 + 管理 API Key', color: 'red' },
  { value: 'write', label: '读写', desc: '创建/删除 KB、上传文档、检索', color: 'blue' },
  { value: 'read', label: '只读', desc: '仅检索和列表查询', color: 'green' },
]

const CLEARANCE_LEVELS = [
  { value: 'public', label: '公开', desc: '只能访问公开文档' },
  { value: 'restricted', label: '受限', desc: '可访问受限文档（需ACL匹配）' },
]

export default function ApiKeyManagement() {
  const [apiKeys, setApiKeys] = useState([])
  const [knowledgeBases, setKnowledgeBases] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [currentKeyInfo, setCurrentKeyInfo] = useState(null)
  
  // 创建对话框
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    role: 'read',
    scope_kb_ids: [],
    useKbScope: false,
    identity: {
      user_id: '',
      roles: [],
      groups: [],
      clearance: 'public'
    },
    useIdentity: false,
    expires_at: '',
    rate_limit_per_minute: '',
  })
  const [isCreating, setIsCreating] = useState(false)
  const [newKeyResult, setNewKeyResult] = useState(null)
  const [copied, setCopied] = useState(false)
  
  // 删除确认
  const [deleteTarget, setDeleteTarget] = useState(null)
  
  // 展开的KB选择器
  const [kbSelectorOpen, setKbSelectorOpen] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [keysRes, kbsRes] = await Promise.all([
        apiClient.listApiKeys().catch(() => ({ items: [] })),
        apiClient.listKnowledgeBases().catch(() => ({ items: [] }))
      ])
      setApiKeys(keysRes.items || [])
      setKnowledgeBases(kbsRes.items || [])
      
      // 尝试获取当前Key信息
      try {
        const currentInfo = await apiClient.getCurrentApiKeyInfo()
        setCurrentKeyInfo(currentInfo)
      } catch {
        // 可能没有这个接口，忽略
      }
    } catch (err) {
      setError('加载数据失败: ' + err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateKey = async () => {
    if (!createForm.name.trim()) {
      setError('请输入 Key 名称')
      return
    }
    
    setIsCreating(true)
    try {
      const payload = {
        name: createForm.name.trim(),
        role: createForm.role,
      }
      
      if (createForm.description.trim()) {
        payload.description = createForm.description.trim()
      }
      
      if (createForm.useKbScope && createForm.scope_kb_ids.length > 0) {
        payload.scope_kb_ids = createForm.scope_kb_ids
      }
      
      if (createForm.useIdentity) {
        const identity = { clearance: createForm.identity.clearance }
        if (createForm.identity.user_id.trim()) {
          identity.user_id = createForm.identity.user_id.trim()
        }
        if (createForm.identity.roles.length > 0) {
          identity.roles = createForm.identity.roles
        }
        if (createForm.identity.groups.length > 0) {
          identity.groups = createForm.identity.groups
        }
        payload.identity = identity
      }
      
      if (createForm.expires_at) {
        payload.expires_at = new Date(createForm.expires_at).toISOString()
      }
      
      if (createForm.rate_limit_per_minute) {
        payload.rate_limit_per_minute = parseInt(createForm.rate_limit_per_minute)
      }
      
      const result = await apiClient.createApiKey(payload)
      setNewKeyResult(result)
      await loadData()
    } catch (err) {
      setError('创建失败: ' + err.message)
    } finally {
      setIsCreating(false)
    }
  }

  const handleRevokeKey = async (id) => {
    try {
      await apiClient.revokeApiKey(id)
      setDeleteTarget(null)
      await loadData()
    } catch (err) {
      setError('撤销失败: ' + err.message)
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const resetCreateForm = () => {
    setCreateForm({
      name: '',
      description: '',
      role: 'read',
      scope_kb_ids: [],
      useKbScope: false,
      identity: { user_id: '', roles: [], groups: [], clearance: 'public' },
      useIdentity: false,
      expires_at: '',
      rate_limit_per_minute: '',
    })
    setNewKeyResult(null)
    setShowCreateDialog(false)
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('zh-CN')
  }

  const getRoleBadge = (role) => {
    const config = ROLES.find(r => r.value === role) || ROLES[2]
    const colors = {
      red: 'bg-red-100 text-red-700',
      blue: 'bg-blue-100 text-blue-700',
      green: 'bg-green-100 text-green-700',
    }
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${colors[config.color]}`}>
        {config.label}
      </span>
    )
  }

  const toggleKbScope = (kbId) => {
    setCreateForm(prev => ({
      ...prev,
      scope_kb_ids: prev.scope_kb_ids.includes(kbId)
        ? prev.scope_kb_ids.filter(id => id !== kbId)
        : [...prev.scope_kb_ids, kbId]
    }))
  }

  const addIdentityItem = (field, value) => {
    if (!value.trim()) return
    setCreateForm(prev => ({
      ...prev,
      identity: {
        ...prev.identity,
        [field]: [...prev.identity[field], value.trim()]
      }
    }))
  }

  const removeIdentityItem = (field, index) => {
    setCreateForm(prev => ({
      ...prev,
      identity: {
        ...prev.identity,
        [field]: prev.identity[field].filter((_, i) => i !== index)
      }
    }))
  }

  return (
    <div className="p-6">
      {/* 页头 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <Key className="w-7 h-7" />
            API Key 管理
          </h1>
          <p className="text-gray-500 mt-1">创建和管理 API Key，控制访问权限</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
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
            创建 Key
          </button>
        </div>
      </div>

      {/* 当前 Key 信息 */}
      {currentKeyInfo && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2 text-blue-700 mb-2">
            <Info className="w-4 h-4" />
            <span className="font-medium">当前使用的 API Key</span>
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-blue-600">名称：</span>
              <span className="text-blue-900">{currentKeyInfo.name || '-'}</span>
            </div>
            <div>
              <span className="text-blue-600">角色：</span>
              {getRoleBadge(currentKeyInfo.role)}
            </div>
            <div>
              <span className="text-blue-600">KB范围：</span>
              <span className="text-blue-900">
                {currentKeyInfo.scope_kb_ids?.length > 0 
                  ? `${currentKeyInfo.scope_kb_ids.length} 个知识库` 
                  : '全部'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Key 列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : apiKeys.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Key className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 mb-2">暂无 API Key</p>
          <p className="text-sm text-gray-400">点击上方按钮创建第一个 Key</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">角色</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">KB范围</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">最后使用</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {apiKeys.map(key => (
                <tr key={key.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div>
                      <p className="font-medium text-gray-900">{key.name}</p>
                      {key.description && (
                        <p className="text-xs text-gray-500 truncate max-w-[200px]">{key.description}</p>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">{getRoleBadge(key.role)}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {key.scope_kb_ids?.length > 0 
                      ? `${key.scope_kb_ids.length} 个` 
                      : '全部'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{formatDate(key.last_used_at)}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{formatDate(key.created_at)}</td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => setDeleteTarget(key)}
                      disabled={key.is_initial}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed"
                      title={key.is_initial ? '初始管理员 Key 不可删除' : '撤销'}
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
        <div className="fixed bottom-4 right-4 max-w-md p-4 bg-red-50 border border-red-200 rounded-lg shadow-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700 flex-1">{error}</p>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 创建对话框 */}
      {showCreateDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            {newKeyResult ? (
              // 创建成功显示
              <div className="p-6">
                <div className="text-center mb-6">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900">API Key 创建成功</h3>
                  <p className="text-sm text-red-500 mt-2">
                    ⚠️ 请立即复制保存，此 Key 仅显示一次！
                  </p>
                </div>
                
                <div className="bg-gray-100 rounded-lg p-4 mb-6">
                  <div className="flex items-center justify-between gap-3">
                    <code className="text-sm font-mono text-gray-800 break-all flex-1">
                      {newKeyResult.key || newKeyResult.api_key}
                    </code>
                    <button
                      onClick={() => copyToClipboard(newKeyResult.key || newKeyResult.api_key)}
                      className="flex items-center gap-1 px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex-shrink-0"
                    >
                      {copied ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      {copied ? '已复制' : '复制'}
                    </button>
                  </div>
                </div>
                
                <button
                  onClick={resetCreateForm}
                  className="w-full py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  关闭
                </button>
              </div>
            ) : (
              // 创建表单
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">创建 API Key</h3>
                
                <div className="space-y-5">
                  {/* 基本信息 */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        名称 <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={createForm.name}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="例如：客服系统Key"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">角色</label>
                      <select
                        value={createForm.role}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, role: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        {ROLES.map(role => (
                          <option key={role.value} value={role.value}>{role.label} - {role.desc}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                    <input
                      type="text"
                      value={createForm.description}
                      onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="可选，描述此 Key 的用途"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>

                  {/* KB 访问范围 */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={createForm.useKbScope}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, useKbScope: e.target.checked }))}
                        className="w-4 h-4 text-primary-600 rounded"
                      />
                      <Database className="w-4 h-4 text-gray-500" />
                      <span className="font-medium text-gray-700">限制知识库访问范围</span>
                    </label>
                    
                    {createForm.useKbScope && (
                      <div className="mt-3 pl-6">
                        <p className="text-xs text-gray-500 mb-2">选择允许访问的知识库（不选则可访问全部）</p>
                        <div className="flex flex-wrap gap-2">
                          {knowledgeBases.map(kb => (
                            <label
                              key={kb.id}
                              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border cursor-pointer transition-colors ${
                                createForm.scope_kb_ids.includes(kb.id)
                                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                                  : 'border-gray-200 hover:border-gray-300'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={createForm.scope_kb_ids.includes(kb.id)}
                                onChange={() => toggleKbScope(kb.id)}
                                className="hidden"
                              />
                              <span className="text-sm">{kb.name}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* 身份信息 */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={createForm.useIdentity}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, useIdentity: e.target.checked }))}
                        className="w-4 h-4 text-primary-600 rounded"
                      />
                      <Shield className="w-4 h-4 text-gray-500" />
                      <span className="font-medium text-gray-700">设置身份信息（用于文档ACL）</span>
                    </label>
                    
                    {createForm.useIdentity && (
                      <div className="mt-3 pl-6 space-y-3">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">用户ID</label>
                            <input
                              type="text"
                              value={createForm.identity.user_id}
                              onChange={(e) => setCreateForm(prev => ({
                                ...prev,
                                identity: { ...prev.identity, user_id: e.target.value }
                              }))}
                              placeholder="例如：user_001"
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">访问级别</label>
                            <select
                              value={createForm.identity.clearance}
                              onChange={(e) => setCreateForm(prev => ({
                                ...prev,
                                identity: { ...prev.identity, clearance: e.target.value }
                              }))}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                            >
                              {CLEARANCE_LEVELS.map(level => (
                                <option key={level.value} value={level.value}>{level.label}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                        
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">角色列表</label>
                          <div className="flex flex-wrap gap-1 mb-2">
                            {createForm.identity.roles.map((role, i) => (
                              <span key={i} className="flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                                {role}
                                <button onClick={() => removeIdentityItem('roles', i)} className="hover:text-blue-900">×</button>
                              </span>
                            ))}
                          </div>
                          <input
                            type="text"
                            placeholder="输入角色后按回车添加"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault()
                                addIdentityItem('roles', e.target.value)
                                e.target.value = ''
                              }
                            }}
                          />
                        </div>
                        
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">部门/组</label>
                          <div className="flex flex-wrap gap-1 mb-2">
                            {createForm.identity.groups.map((group, i) => (
                              <span key={i} className="flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                                {group}
                                <button onClick={() => removeIdentityItem('groups', i)} className="hover:text-green-900">×</button>
                              </span>
                            ))}
                          </div>
                          <input
                            type="text"
                            placeholder="输入部门后按回车添加"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault()
                                addIdentityItem('groups', e.target.value)
                                e.target.value = ''
                              }
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* 高级设置 */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        <Clock className="w-4 h-4 inline mr-1" />
                        过期时间（可选）
                      </label>
                      <input
                        type="datetime-local"
                        value={createForm.expires_at}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, expires_at: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        限流（次/分钟，可选）
                      </label>
                      <input
                        type="number"
                        value={createForm.rate_limit_per_minute}
                        onChange={(e) => setCreateForm(prev => ({ ...prev, rate_limit_per_minute: e.target.value }))}
                        placeholder="留空使用默认值"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200">
                  <button
                    onClick={resetCreateForm}
                    className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleCreateKey}
                    disabled={isCreating || !createForm.name.trim()}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    {isCreating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    创建
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 删除确认对话框 */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">撤销 API Key</h3>
            <p className="text-gray-600 mb-6">
              确定要撤销 <span className="font-medium">"{deleteTarget.name}"</span> 吗？
              撤销后此 Key 将立即失效，无法恢复。
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                取消
              </button>
              <button
                onClick={() => handleRevokeKey(deleteTarget.id)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                撤销
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
