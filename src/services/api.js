/**
 * RAGForge API 客户端
 * 用于与后端RAG服务通信
 */

const STORAGE_KEY = 'ragforge_config'

const getStoredConfig = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (e) {
    console.error('Failed to load config:', e)
  }
  return {
    baseUrl: 'http://192.168.168.105:8020',
    apiKey: 'kb_sk_yvmEUfH-E4R9CgNKxeo_9m2L4wzHcy8bxI3BSo0XxcQ'
  }
}

class APIClient {
  constructor() {
    this.refreshConfig()
    // 监听配置变化
    if (typeof window !== 'undefined') {
      window.addEventListener('config-changed', () => this.refreshConfig())
    }
  }

  refreshConfig() {
    const config = getStoredConfig()
    this.apiKey = config.apiKey
    this.baseUrl = config.baseUrl
  }

  async request(method, endpoint, data = null, isFormData = false) {
    const headers = {
      'Authorization': `Bearer ${this.apiKey}`,
    }

    if (!isFormData && data) {
      headers['Content-Type'] = 'application/json'
    }

    const config = {
      method,
      headers,
    }

    if (data) {
      config.body = isFormData ? data : JSON.stringify(data)
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, config)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      let message = `HTTP ${response.status}`
      if (error.detail) {
        message = typeof error.detail === 'string'
          ? error.detail
          : error.detail.detail || JSON.stringify(error.detail)
      }
      throw new Error(message)
    }

    if (response.status === 204) {
      return {}
    }

    return response.json()
  }

  // ==================== 知识库管理 ====================

  async listKnowledgeBases() {
    return this.request('GET', '/v1/knowledge-bases')
  }

  async createKnowledgeBase(name, description = '') {
    return this.request('POST', '/v1/knowledge-bases', { name, description })
  }

  async deleteKnowledgeBase(id) {
    return this.request('DELETE', `/v1/knowledge-bases/${id}`)
  }

  async getKnowledgeBase(id) {
    return this.request('GET', `/v1/knowledge-bases/${id}`)
  }

  // ==================== 文档管理 ====================

  async listDocuments(kbId) {
    return this.request('GET', `/v1/knowledge-bases/${kbId}/documents`)
  }

  async uploadDocument(kbId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return this.request('POST', `/v1/knowledge-bases/${kbId}/documents`, formData, true)
  }

  async deleteDocument(docId) {
    return this.request('DELETE', `/v1/documents/${docId}`)
  }

  async getDocument(docId) {
    return this.request('GET', `/v1/documents/${docId}`)
  }

  // ==================== 检索 API ====================

  async retrieve(query, kbIds, topK = 5, retrieverName = 'hybrid') {
    const payload = {
      query,
      knowledge_base_ids: kbIds,
      top_k: topK,
    }
    if (retrieverName !== 'dense') {
      payload.retriever_override = { name: retrieverName }
    }
    return this.request('POST', '/v1/retrieve', payload)
  }

  // ==================== RAG 生成 API ====================

  async rag(query, kbIds, options = {}) {
    const { topK = 5, retriever = 'hybrid', systemPrompt, temperature, maxTokens } = options
    const payload = {
      query,
      knowledge_base_ids: kbIds,
      top_k: topK,
    }
    if (retriever !== 'dense') {
      payload.retriever_override = { name: retriever }
    }
    if (systemPrompt) payload.system_prompt = systemPrompt
    if (temperature !== undefined) payload.temperature = temperature
    if (maxTokens) payload.max_tokens = maxTokens
    
    return this.request('POST', '/v1/rag', payload)
  }

  // ==================== 流式 RAG API ====================

  streamRAG(query, kbIds, options = {}) {
    const { topK = 5, retriever = 'hybrid', onSources, onContent, onDone, onError } = options
    const controller = new AbortController()

    const payload = {
      query,
      knowledge_base_ids: kbIds,
      top_k: topK,
    }
    if (retriever !== 'dense') {
      payload.retriever_override = { name: retriever }
    }

    const run = async () => {
      try {
        const response = await fetch(`${this.baseUrl}/v1/rag/stream`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        })

        if (!response.ok) {
          const error = await response.json().catch(() => ({ detail: response.statusText }))
          throw new Error(error.detail || `HTTP ${response.status}`)
        }

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No response body')

        const decoder = new TextDecoder()
        let buffer = ''
        let currentEventType = 'content'

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEventType = line.slice(7).trim()
              continue
            }
            if (line.startsWith('data: ')) {
              const data = line.slice(6)

              if (currentEventType === 'done' || data === '[DONE]') {
                onDone?.()
                return
              }

              if (currentEventType === 'error') {
                try {
                  const parsed = JSON.parse(data)
                  onError?.(parsed.error || data)
                } catch {
                  onError?.(data)
                }
                return
              }

              if (currentEventType === 'sources') {
                try {
                  const parsed = JSON.parse(data)
                  if (Array.isArray(parsed)) {
                    onSources?.(parsed)
                  }
                } catch {
                  console.warn('Failed to parse sources:', data)
                }
                continue
              }

              if (data && currentEventType === 'content') {
                const text = data.replace(/\\n/g, '\n').replace(/\\r/g, '\r')
                if (text) onContent?.(text)
              }
            }
          }
        }
        onDone?.()
      } catch (error) {
        if (error.name !== 'AbortError') {
          onError?.(error.message)
        }
      }
    }

    run()
    return controller
  }

  // ==================== 模型设置 ====================

  async getModelSettings() {
    return this.request('GET', '/v1/settings/models')
  }

  // ==================== API Key 管理 ====================

  async listApiKeys() {
    return this.request('GET', '/v1/api-keys')
  }

  async createApiKey(data) {
    // data: { name, role, description, scope_kb_ids, identity, expires_at, rate_limit_per_minute }
    return this.request('POST', '/v1/api-keys', data)
  }

  async revokeApiKey(id) {
    return this.request('DELETE', `/v1/api-keys/${id}`)
  }

  async getCurrentApiKeyInfo() {
    // 获取当前 API Key 的信息
    return this.request('GET', '/v1/api-keys/me')
  }

  // ==================== 文档上传（带ACL） ====================

  async uploadDocumentWithACL(kbId, file, aclOptions = {}) {
    const formData = new FormData()
    formData.append('file', file)
    
    // ACL 选项
    if (aclOptions.sensitivity_level) {
      formData.append('sensitivity_level', aclOptions.sensitivity_level)
    }
    if (aclOptions.acl_allow_users?.length) {
      formData.append('acl_allow_users', JSON.stringify(aclOptions.acl_allow_users))
    }
    if (aclOptions.acl_allow_roles?.length) {
      formData.append('acl_allow_roles', JSON.stringify(aclOptions.acl_allow_roles))
    }
    if (aclOptions.acl_allow_groups?.length) {
      formData.append('acl_allow_groups', JSON.stringify(aclOptions.acl_allow_groups))
    }
    
    return this.request('POST', `/v1/knowledge-bases/${kbId}/documents`, formData, true)
  }

  // ==================== 健康检查 ====================

  async health() {
    const response = await fetch(`${this.baseUrl}/health`)
    return response.json()
  }
}

// 创建默认客户端实例
const apiClient = new APIClient()

export { APIClient, apiClient }
export default apiClient
