import { useState, useEffect } from 'react'
import {
  Users,
  UserPlus,
  Shield,
  Building2,
  Trash2,
  Plus,
  Save,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  X,
  Edit2,
  Loader2
} from 'lucide-react'
import { backendClient } from '../services/backend'

export default function UserRoleManagement() {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('users')
  const [message, setMessage] = useState(null)
  
  // 新增表单
  const [newUser, setNewUser] = useState({ username: '', password: '', display_name: '', email: '', clearance: 'public', role_ids: [], group_ids: [] })
  const [newRole, setNewRole] = useState({ name: '', display_name: '' })
  const [newGroup, setNewGroup] = useState({ name: '', display_name: '' })
  const [showUserForm, setShowUserForm] = useState(false)
  const [editingUser, setEditingUser] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [usersData, rolesData, groupsData] = await Promise.all([
        backendClient.getUsers(),
        backendClient.getRoles(),
        backendClient.getGroups()
      ])
      setUsers(usersData)
      setRoles(rolesData)
      setGroups(groupsData)
    } catch (e) {
      showMessage('error', '加载数据失败: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  const showMessage = (type, text) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 3000)
  }

  // 用户管理
  const handleAddUser = async () => {
    if (!newUser.username.trim() || !newUser.password.trim()) {
      showMessage('error', '请输入用户名和密码')
      return
    }
    
    try {
      await backendClient.createUser({
        username: newUser.username.trim(),
        password: newUser.password,
        display_name: newUser.display_name.trim() || newUser.username.trim(),
        email: newUser.email.trim() || null,
        clearance: newUser.clearance,
        role_ids: newUser.role_ids,
        group_ids: newUser.group_ids
      })
      showMessage('success', '用户创建成功')
      setNewUser({ username: '', password: '', display_name: '', email: '', clearance: 'public', role_ids: [], group_ids: [] })
      setShowUserForm(false)
      loadData()
    } catch (e) {
      showMessage('error', '创建失败: ' + e.message)
    }
  }

  const handleUpdateUser = async () => {
    if (!editingUser) return
    
    try {
      // 更新用户角色
      await backendClient.setUserRoles(editingUser.id, editingUser.role_ids || [])
      // 更新用户部门
      await backendClient.setUserGroups(editingUser.id, editingUser.group_ids || [])
      showMessage('success', '用户更新成功')
      setEditingUser(null)
      loadData()
    } catch (e) {
      showMessage('error', '更新失败: ' + e.message)
    }
  }

  const handleDeleteUser = async (userId) => {
    if (!confirm('确定要删除此用户吗？')) return
    try {
      await backendClient.deleteUser(userId)
      showMessage('success', '用户已删除')
      loadData()
    } catch (e) {
      showMessage('error', '删除失败: ' + e.message)
    }
  }

  // 角色管理
  const handleAddRole = async () => {
    if (!newRole.name.trim()) return
    try {
      await backendClient.createRole({
        name: newRole.name.trim(),
        display_name: newRole.display_name.trim() || newRole.name.trim()
      })
      showMessage('success', '角色创建成功')
      setNewRole({ name: '', display_name: '' })
      loadData()
    } catch (e) {
      showMessage('error', '创建失败: ' + e.message)
    }
  }

  const handleDeleteRole = async (roleId) => {
    if (!confirm('确定要删除此角色吗？')) return
    try {
      await backendClient.deleteRole(roleId)
      showMessage('success', '角色已删除')
      loadData()
    } catch (e) {
      showMessage('error', '删除失败: ' + e.message)
    }
  }

  // 部门管理
  const handleAddGroup = async () => {
    if (!newGroup.name.trim()) return
    try {
      await backendClient.createGroup({
        name: newGroup.name.trim(),
        display_name: newGroup.display_name.trim() || newGroup.name.trim()
      })
      showMessage('success', '部门创建成功')
      setNewGroup({ name: '', display_name: '' })
      loadData()
    } catch (e) {
      showMessage('error', '创建失败: ' + e.message)
    }
  }

  const handleDeleteGroup = async (groupId) => {
    if (!confirm('确定要删除此部门吗？')) return
    try {
      await backendClient.deleteGroup(groupId)
      showMessage('success', '部门已删除')
      loadData()
    } catch (e) {
      showMessage('error', '删除失败: ' + e.message)
    }
  }

  const toggleUserRole = (roleId, isEditing = false) => {
    if (isEditing && editingUser) {
      setEditingUser(prev => ({
        ...prev,
        role_ids: prev.role_ids?.includes(roleId) 
          ? prev.role_ids.filter(r => r !== roleId)
          : [...(prev.role_ids || []), roleId]
      }))
    } else {
      setNewUser(prev => ({
        ...prev,
        role_ids: prev.role_ids.includes(roleId) 
          ? prev.role_ids.filter(r => r !== roleId)
          : [...prev.role_ids, roleId]
      }))
    }
  }

  const toggleUserGroup = (groupId, isEditing = false) => {
    if (isEditing && editingUser) {
      setEditingUser(prev => ({
        ...prev,
        group_ids: prev.group_ids?.includes(groupId) 
          ? prev.group_ids.filter(g => g !== groupId)
          : [...(prev.group_ids || []), groupId]
      }))
    } else {
      setNewUser(prev => ({
        ...prev,
        group_ids: prev.group_ids.includes(groupId) 
          ? prev.group_ids.filter(g => g !== groupId)
          : [...prev.group_ids, groupId]
      }))
    }
  }

  const tabs = [
    { id: 'users', label: '用户', icon: Users, count: users.length },
    { id: 'roles', label: '角色', icon: Shield, count: roles.length },
    { id: 'groups', label: '部门/组', icon: Building2, count: groups.length },
  ]

  return (
    <div className="p-6">
      {/* 页头 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <Users className="w-7 h-7" />
            用户与角色
          </h1>
          <p className="text-gray-500 mt-1">管理用户、角色和部门，用于文档访问控制（ACL）配置</p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50"
        >
          <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      )}

      {/* 标签页 */}
      <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                activeTab === tab.id ? 'bg-primary-100 text-primary-700' : 'bg-gray-200 text-gray-600'
              }`}>
                {tab.count}
              </span>
            </button>
          )
        })}
      </div>

      {/* 用户管理 */}
      {activeTab === 'users' && !loading && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="font-medium text-gray-900">用户列表</h3>
            <button
              onClick={() => setShowUserForm(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
            >
              <UserPlus className="w-4 h-4" />
              添加用户
            </button>
          </div>
          
          {users.length === 0 ? (
            <div className="p-12 text-center">
              <Users className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">暂无用户</p>
              <p className="text-sm text-gray-400 mt-1">添加用户后可在文档ACL中选择</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">用户名</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">权限等级</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">角色</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">部门</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-mono text-gray-900">
                      {user.username}
                      {user.is_admin && <span className="ml-2 px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-xs">管理员</span>}
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{user.display_name}</p>
                        {user.email && <p className="text-xs text-gray-400">{user.email}</p>}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        user.clearance === 'confidential' ? 'bg-red-100 text-red-700' :
                        user.clearance === 'restricted' ? 'bg-yellow-100 text-yellow-700' :
                        user.clearance === 'internal' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {user.clearance}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {user.roles?.map(role => (
                          <span key={role.id} className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">
                            {role.display_name || role.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {user.groups?.map(group => (
                          <span key={group.id} className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                            {group.display_name || group.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setEditingUser({ 
                            ...user, 
                            role_ids: user.roles?.map(r => r.id) || [],
                            group_ids: user.groups?.map(g => g.id) || []
                          })}
                          className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteUser(user.id)}
                          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* 角色管理 */}
      {activeTab === 'roles' && !loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex gap-3 mb-6">
            <input
              type="text"
              value={newRole.name}
              onChange={(e) => setNewRole({ ...newRole, name: e.target.value })}
              placeholder="角色标识（如 finance）"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
            />
            <input
              type="text"
              value={newRole.display_name}
              onChange={(e) => setNewRole({ ...newRole, display_name: e.target.value })}
              placeholder="显示名称（如 财务人员）"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
              onKeyDown={(e) => e.key === 'Enter' && handleAddRole()}
            />
            <button
              onClick={handleAddRole}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Plus className="w-4 h-4" />
              添加
            </button>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {roles.map(role => (
              <div
                key={role.id}
                className="flex items-center gap-2 px-3 py-2 bg-purple-50 border border-purple-200 rounded-lg group"
              >
                <Shield className="w-4 h-4 text-purple-500" />
                <span className="text-purple-700 font-medium">{role.display_name}</span>
                <span className="text-purple-400 text-xs">({role.name})</span>
                <button
                  onClick={() => handleDeleteRole(role.id)}
                  className="p-0.5 text-purple-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
          
          {roles.length === 0 && (
            <p className="text-center text-gray-400 py-8">暂无角色，请添加</p>
          )}
        </div>
      )}

      {/* 部门管理 */}
      {activeTab === 'groups' && !loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex gap-3 mb-6">
            <input
              type="text"
              value={newGroup.name}
              onChange={(e) => setNewGroup({ ...newGroup, name: e.target.value })}
              placeholder="部门标识（如 dept_tech）"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
            />
            <input
              type="text"
              value={newGroup.display_name}
              onChange={(e) => setNewGroup({ ...newGroup, display_name: e.target.value })}
              placeholder="显示名称（如 技术部）"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
              onKeyDown={(e) => e.key === 'Enter' && handleAddGroup()}
            />
            <button
              onClick={handleAddGroup}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Plus className="w-4 h-4" />
              添加
            </button>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {groups.map(group => (
              <div
                key={group.id}
                className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg group/item"
              >
                <Building2 className="w-4 h-4 text-green-500" />
                <span className="text-green-700 font-medium">{group.display_name}</span>
                <span className="text-green-400 text-xs">({group.name})</span>
                <button
                  onClick={() => handleDeleteGroup(group.id)}
                  className="p-0.5 text-green-400 hover:text-red-500 opacity-0 group-hover/item:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
          
          {groups.length === 0 && (
            <p className="text-center text-gray-400 py-8">暂无部门，请添加</p>
          )}
        </div>
      )}

      {/* 添加/编辑用户对话框 */}
      {(showUserForm || editingUser) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              {editingUser ? '编辑用户' : '添加用户'}
            </h3>
            
            <div className="space-y-4">
              {!editingUser && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        用户名 <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={newUser.username}
                        onChange={(e) => setNewUser(prev => ({ ...prev, username: e.target.value }))}
                        placeholder="登录用户名"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        密码 <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="password"
                        value={newUser.password}
                        onChange={(e) => setNewUser(prev => ({ ...prev, password: e.target.value }))}
                        placeholder="登录密码"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">显示名称</label>
                      <input
                        type="text"
                        value={newUser.display_name}
                        onChange={(e) => setNewUser(prev => ({ ...prev, display_name: e.target.value }))}
                        placeholder="用户显示名"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
                      <input
                        type="email"
                        value={newUser.email}
                        onChange={(e) => setNewUser(prev => ({ ...prev, email: e.target.value }))}
                        placeholder="可选"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">权限等级</label>
                    <select
                      value={newUser.clearance}
                      onChange={(e) => setNewUser(prev => ({ ...prev, clearance: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="public">public - 仅公开</option>
                      <option value="internal">internal - 内部</option>
                      <option value="restricted">restricted - 受限</option>
                      <option value="confidential">confidential - 机密</option>
                    </select>
                  </div>
                </>
              )}

              {editingUser && (
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">
                    用户: <span className="font-medium">{editingUser.display_name}</span> ({editingUser.username})
                  </p>
                  <p className="text-xs text-gray-400 mt-1">编辑模式下只能修改角色和部门</p>
                </div>
              )}
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">所属角色</label>
                <div className="flex flex-wrap gap-2">
                  {roles.map(role => {
                    const isSelected = editingUser 
                      ? editingUser.role_ids?.includes(role.id)
                      : newUser.role_ids.includes(role.id)
                    return (
                      <button
                        key={role.id}
                        type="button"
                        onClick={() => toggleUserRole(role.id, !!editingUser)}
                        className={`px-3 py-1.5 rounded-lg border text-sm transition-colors ${
                          isSelected
                            ? 'border-purple-500 bg-purple-50 text-purple-700'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        {role.display_name}
                      </button>
                    )
                  })}
                  {roles.length === 0 && <span className="text-gray-400 text-sm">暂无角色</span>}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">所属部门</label>
                <div className="flex flex-wrap gap-2">
                  {groups.map(group => {
                    const isSelected = editingUser 
                      ? editingUser.group_ids?.includes(group.id)
                      : newUser.group_ids.includes(group.id)
                    return (
                      <button
                        key={group.id}
                        type="button"
                        onClick={() => toggleUserGroup(group.id, !!editingUser)}
                        className={`px-3 py-1.5 rounded-lg border text-sm transition-colors ${
                          isSelected
                            ? 'border-green-500 bg-green-50 text-green-700'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        {group.display_name}
                      </button>
                    )
                  })}
                  {groups.length === 0 && <span className="text-gray-400 text-sm">暂无部门</span>}
                </div>
              </div>
            </div>
            
            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200">
              <button
                onClick={() => {
                  setShowUserForm(false)
                  setEditingUser(null)
                  setNewUser({ username: '', password: '', display_name: '', email: '', clearance: 'public', role_ids: [], group_ids: [] })
                }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                取消
              </button>
              <button
                onClick={editingUser ? handleUpdateUser : handleAddUser}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                <Save className="w-4 h-4" />
                {editingUser ? '保存' : '添加'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 消息提示 */}
      {message && (
        <div className={`fixed bottom-4 right-4 max-w-md p-4 rounded-lg shadow-lg flex items-center gap-3 ${
          message.type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}>
          {message.type === 'success' 
            ? <CheckCircle className="w-5 h-5 text-green-500" />
            : <AlertCircle className="w-5 h-5 text-red-500" />
          }
          <p className={`text-sm ${message.type === 'success' ? 'text-green-700' : 'text-red-700'}`}>
            {message.text}
          </p>
        </div>
      )}
    </div>
  )
}
