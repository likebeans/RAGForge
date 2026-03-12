/**
 * yaoyan 后端 API 客户端
 * 处理认证、用户管理和 RAGForge 代理
 */

import { authService } from './auth'

// 使用相对路径，通过 nginx 代理到后端
// 这样无论从 localhost 还是服务器 IP 访问都能正常工作
const BACKEND_URL = ''

class BackendClient {
  constructor() {
    this.baseUrl = BACKEND_URL
  }

  async request(method, endpoint, data = null, requireAuth = true) {
    const headers = {}

    if (requireAuth) {
      const token = authService.getToken()
      if (!token) {
        throw new Error('未登录')
      }
      headers['Authorization'] = `Bearer ${token}`
    }

    if (data && !(data instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }

    const config = {
      method,
      headers,
    }

    if (data) {
      config.body = data instanceof FormData ? data : JSON.stringify(data)
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, config)

    if (response.status === 401 && requireAuth) {
      authService.clearAuth()
      window.location.href = '/login'
      throw new Error('登录已过期')
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    if (response.status === 204) {
      return {}
    }

    return response.json()
  }

  // ==================== 认证 ====================

  async login(username, password) {
    const data = await this.request('POST', '/api/auth/login', { username, password }, false)
    authService.setAuth(data.access_token, data.user)
    return data
  }

  async register(username, password, displayName) {
    const data = await this.request('POST', '/api/auth/register', {
      username,
      password,
      display_name: displayName
    }, false)
    authService.setAuth(data.access_token, data.user)
    return data
  }

  async getCurrentUser() {
    return this.request('GET', '/api/auth/me')
  }

  logout() {
    authService.clearAuth()
  }

  // ==================== 用户管理 ====================

  async getUsers() {
    return this.request('GET', '/api/users')
  }

  async createUser(userData) {
    return this.request('POST', '/api/users', userData)
  }

  async updateUser(userId, userData) {
    return this.request('PUT', `/api/users/${userId}`, userData)
  }

  async deleteUser(userId) {
    return this.request('DELETE', `/api/users/${userId}`)
  }

  async setUserRoles(userId, roleIds) {
    return this.request('PUT', `/api/users/${userId}/roles`, { role_ids: roleIds })
  }

  async setUserGroups(userId, groupIds) {
    return this.request('PUT', `/api/users/${userId}/groups`, { group_ids: groupIds })
  }

  // ==================== 角色管理 ====================

  async getRoles() {
    return this.request('GET', '/api/roles')
  }

  async createRole(data) {
    return this.request('POST', '/api/roles', data)
  }

  async updateRole(roleId, data) {
    return this.request('PUT', `/api/roles/${roleId}`, data)
  }

  async deleteRole(roleId) {
    return this.request('DELETE', `/api/roles/${roleId}`)
  }

  // ==================== 部门管理 ====================

  async getGroups() {
    return this.request('GET', '/api/groups')
  }

  async createGroup(data) {
    return this.request('POST', '/api/groups', data)
  }

  async updateGroup(groupId, data) {
    return this.request('PUT', `/api/groups/${groupId}`, data)
  }

  async deleteGroup(groupId) {
    return this.request('DELETE', `/api/groups/${groupId}`)
  }

  // ==================== RAGForge 代理 ====================

  async listKnowledgeBases() {
    return this.request('GET', '/api/ragforge/knowledge-bases')
  }

  async createKnowledgeBase(name, description = '') {
    return this.request('POST', '/api/ragforge/knowledge-bases', { name, description })
  }

  async deleteKnowledgeBase(id) {
    return this.request('DELETE', `/api/ragforge/knowledge-bases/${id}`)
  }

  async listDocuments(kbId) {
    return this.request('GET', `/api/ragforge/knowledge-bases/${kbId}/documents`)
  }

  async uploadDocument(kbId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return this.request('POST', `/api/ragforge/knowledge-bases/${kbId}/documents`, formData)
  }

  async deleteDocument(docId) {
    return this.request('DELETE', `/api/ragforge/documents/${docId}`)
  }

  async retrieve(query, kbIds, topK = 5) {
    return this.request('POST', '/api/ragforge/retrieve', {
      query,
      knowledge_base_ids: kbIds,
      top_k: topK
    })
  }

  async rag(query, kbIds, options = {}) {
    const { topK = 5, retriever = 'hybrid' } = options
    return this.request('POST', '/api/ragforge/rag', {
      query,
      knowledge_base_ids: kbIds,
      top_k: topK,
      retriever,
    })
  }

  // ==================== 项目管理 ====================

  async getProjects(params = {}) {
    const queryString = new URLSearchParams(params).toString()
    return this.request('GET', `/api/projects?${queryString}`)
  }

  async getProject(projectId) {
    return this.request('GET', `/api/projects/${projectId}`)
  }

  async createProject(data) {
    return this.request('POST', '/api/projects', data)
  }

  async updateProject(projectId, data) {
    return this.request('PUT', `/api/projects/${projectId}`, data)
  }

  async deleteProject(projectId) {
    return this.request('DELETE', `/api/projects/${projectId}`)
  }

  async downloadTemplate() {
    const token = authService.getToken()
    const response = await fetch(`${this.baseUrl}/api/projects/template/download`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('下载模板失败')
    return response.blob()
  }

  async importProjects(file, mode = 'append') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('mode', mode)
    return this.request('POST', '/api/projects/import', formData)
  }

  async exportProjects(params = {}) {
    const token = authService.getToken()
    const queryString = new URLSearchParams(params).toString()
    const response = await fetch(`${this.baseUrl}/api/projects/export?${queryString}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('导出失败')
    return response.blob()
  }

  async getReports(params = {}) {
    const queryString = new URLSearchParams(params).toString()
    return this.request('GET', `/api/reports?${queryString}`)
  }

  async getReport(reportId) {
    return this.request('GET', `/api/reports/${reportId}`)
  }

  async createReport(data) {
    return this.request('POST', '/api/reports', data)
  }

  async updateReport(reportId, data) {
    return this.request('PUT', `/api/reports/${reportId}`, data)
  }

  async deleteReport(reportId) {
    return this.request('DELETE', `/api/reports/${reportId}`)
  }

  async bulkDeleteReports(ids = []) {
    return this.request('POST', '/api/reports/bulk-delete', { ids })
  }

  async exportReports(params = {}, ids = null) {
    const token = authService.getToken()
    const query = { ...params }
    if (ids && ids.length > 0) {
      query.ids = ids.join(',')
    }
    const queryString = new URLSearchParams(query).toString()
    const response = await fetch(`${this.baseUrl}/api/reports/export?${queryString}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('导出失败')
    return response.blob()
  }

  // ==================== 字典管理 ====================

  async getDicts() {
    return this.request('GET', '/api/dicts')
  }

  async getDictByCategory(category) {
    return this.request('GET', `/api/dicts/${category}`)
  }

  // ==================== PDF 智能提取 ====================

  async listExtractionSchemas() {
    return this.request('GET', '/api/ragforge/extraction-schemas')
  }

  async createExtractionSchema(file, name) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', name)
    return this.request('POST', '/api/ragforge/extraction-schemas', formData)
  }

  async getExtractionSchema(schemaId) {
    return this.request('GET', `/api/ragforge/extraction-schemas/${schemaId}`)
  }

  async deleteExtractionSchema(schemaId) {
    return this.request('DELETE', `/api/ragforge/extraction-schemas/${schemaId}`)
  }

  async extractFromPdfs(schemaId, files, outputFormat = 'json') {
    const token = authService.getToken()
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    formData.append('output_format', outputFormat)
    
    const response = await fetch(`${this.baseUrl}/api/ragforge/extraction-schemas/${schemaId}/extract`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }
    
    if (outputFormat === 'excel') {
      return response.blob()
    }
    return response.json()
  }
}

export const backendClient = new BackendClient()
export default backendClient
