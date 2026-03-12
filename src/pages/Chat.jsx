import { useState, useRef, useEffect } from 'react'
import { 
  Send, 
  Loader2, 
  Database, 
  Sparkles, 
  MessageSquare, 
  Search,
  ChevronDown,
  Bot,
  User,
  FileText,
  ExternalLink,
  Shield
} from 'lucide-react'
import { backendClient } from '../services/backend'
import { authService } from '../services/auth'

const RETRIEVERS = [
  { value: 'dense', label: 'Dense (向量)' },
  { value: 'bm25', label: 'BM25 (稀疏)' },
  { value: 'hybrid', label: 'Hybrid (混合)' },
  { value: 'hyde', label: 'HyDE (假设文档)' },
  { value: 'fusion', label: 'Fusion (融合)' },
]

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [retriever, setRetriever] = useState('hybrid')
  const [knowledgeBases, setKnowledgeBases] = useState([])
  const [selectedKbIds, setSelectedKbIds] = useState([])
  const [kbMenuOpen, setKbMenuOpen] = useState(false)
  const [retrieverMenuOpen, setRetrieverMenuOpen] = useState(false)
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)
  const user = authService.getUser()

  // 加载知识库列表
  useEffect(() => {
    loadKnowledgeBases()
  }, [])

  // 自动滚动到底部
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadKnowledgeBases = async () => {
    try {
      const result = await backendClient.listKnowledgeBases()
      setKnowledgeBases(result.items || [])
      // 默认选择第一个知识库
      if (result.items?.length > 0 && selectedKbIds.length === 0) {
        setSelectedKbIds([result.items[0].id])
      }
    } catch (err) {
      console.error('Failed to load knowledge bases:', err)
      setError('加载知识库失败: ' + err.message)
    }
  }

  const toggleKnowledgeBase = (id) => {
    setSelectedKbIds(prev => 
      prev.includes(id) 
        ? prev.filter(kbId => kbId !== id)
        : [...prev, id]
    )
  }

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return
    if (selectedKbIds.length === 0) {
      setError('请先选择知识库')
      return
    }

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    }

    const assistantMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      sources: [],
      isStreaming: true,
    }

    setMessages(prev => [...prev, userMessage, assistantMessage])
    setInput('')
    setIsLoading(true)
    setError(null)

    try {
      // 使用后端代理的 RAG 接口（自动注入用户身份）
      const result = await backendClient.rag(userMessage.content, selectedKbIds, { topK: 5, retriever })
      
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessage.id
            ? { 
                ...msg, 
                content: result.answer || result.response || '无法生成回答',
                sources: result.sources || result.results || [],
                isStreaming: false 
              }
            : msg
        )
      )
    } catch (err) {
      setError(`请求失败: ${err.message}`)
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessage.id
            ? { ...msg, content: `错误: ${err.message}`, isStreaming: false }
            : msg
        )
      )
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const getSelectedKbNames = () => {
    if (selectedKbIds.length === 0) return '选择知识库'
    if (selectedKbIds.length === 1) {
      const kb = knowledgeBases.find(k => k.id === selectedKbIds[0])
      return kb?.name || '已选择 1 个'
    }
    return `已选 ${selectedKbIds.length} 个知识库`
  }

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col bg-gray-50">
      {/* 顶部工具栏 */}
      <div className="flex items-center gap-4 p-4 bg-white border-b border-gray-200">
        {/* 用户身份提示 */}
        {user && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg text-xs">
            <Shield className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-blue-700">
              {user.display_name} · {user.clearance || 'public'}
            </span>
          </div>
        )}

        {/* 知识库选择 */}
        <div className="relative">
          <button
            onClick={() => setKbMenuOpen(!kbMenuOpen)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 transition-colors min-w-[200px]"
          >
            <Database className="w-4 h-4 text-gray-500" />
            <span className="truncate flex-1 text-left">{getSelectedKbNames()}</span>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>
          {kbMenuOpen && (
            <div className="absolute top-full left-0 mt-1 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
              {knowledgeBases.length === 0 ? (
                <div className="px-4 py-3 text-sm text-gray-500">暂无知识库</div>
              ) : (
                knowledgeBases.map(kb => (
                  <label
                    key={kb.id}
                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedKbIds.includes(kb.id)}
                      onChange={() => toggleKnowledgeBase(kb.id)}
                      className="w-4 h-4 text-primary-600 rounded"
                    />
                    <span className="text-sm truncate">{kb.name}</span>
                  </label>
                ))
              )}
            </div>
          )}
        </div>

        {/* 检索器选择 */}
        <div className="relative">
          <button
            onClick={() => setRetrieverMenuOpen(!retrieverMenuOpen)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 transition-colors"
          >
            <Search className="w-4 h-4 text-gray-500" />
            <span>{RETRIEVERS.find(r => r.value === retriever)?.label}</span>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>
          {retrieverMenuOpen && (
            <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
              {RETRIEVERS.map(r => (
                <button
                  key={r.value}
                  onClick={() => {
                    setRetriever(r.value)
                    setRetrieverMenuOpen(false)
                  }}
                  className={`w-full px-4 py-2.5 text-left text-sm hover:bg-gray-50 ${
                    retriever === r.value ? 'bg-primary-50 text-primary-600' : ''
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 点击外部关闭菜单 */}
      {(kbMenuOpen || retrieverMenuOpen) && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => {
            setKbMenuOpen(false)
            setRetrieverMenuOpen(false)
          }}
        />
      )}

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-20 text-center">
              <div className="relative mb-6">
                <div className="absolute inset-0 bg-primary-500/20 rounded-full blur-xl animate-pulse" />
                <div className="relative bg-gradient-to-br from-primary-100 to-primary-50 p-5 rounded-2xl border border-primary-200">
                  <Sparkles className="h-10 w-10 text-primary-600" />
                </div>
              </div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-3">知识库智能问答</h2>
              <p className="text-gray-500 max-w-md mb-8">
                基于 RAG 技术，从您的知识库中检索相关内容，为您提供准确、有据可查的回答。
              </p>
              <div className="grid grid-cols-3 gap-4 max-w-lg">
                <div className="flex flex-col items-center p-4 rounded-xl bg-white border border-gray-200 shadow-sm">
                  <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center mb-2">
                    <Database className="h-5 w-5 text-blue-600" />
                  </div>
                  <span className="text-sm font-medium text-gray-700">知识库检索</span>
                </div>
                <div className="flex flex-col items-center p-4 rounded-xl bg-white border border-gray-200 shadow-sm">
                  <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center mb-2">
                    <Search className="h-5 w-5 text-green-600" />
                  </div>
                  <span className="text-sm font-medium text-gray-700">多检索器</span>
                </div>
                <div className="flex flex-col items-center p-4 rounded-xl bg-white border border-gray-200 shadow-sm">
                  <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center mb-2">
                    <MessageSquare className="h-5 w-5 text-amber-600" />
                  </div>
                  <span className="text-sm font-medium text-gray-700">引用来源</span>
                </div>
              </div>
              {selectedKbIds.length === 0 && (
                <div className="mt-6 flex items-center gap-2 text-sm text-gray-500 bg-gray-100 px-4 py-2 rounded-full">
                  <Database className="h-4 w-4" />
                  <span>请先在上方选择一个知识库</span>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map(msg => (
                <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-9 h-9 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-5 h-5 text-primary-600" />
                    </div>
                  )}
                  <div className={`max-w-[75%] ${msg.role === 'user' ? 'order-1' : ''}`}>
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        msg.role === 'user'
                          ? 'bg-primary-600 text-white'
                          : 'bg-white border border-gray-200 shadow-sm'
                      }`}
                    >
                      <div className="whitespace-pre-wrap text-sm leading-relaxed">
                        {msg.content || (msg.isStreaming && <Loader2 className="w-4 h-4 animate-spin" />)}
                      </div>
                    </div>
                    {/* 引用来源 */}
                    {msg.role === 'assistant' && msg.sources?.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs text-gray-500 font-medium">参考来源:</p>
                        {msg.sources.slice(0, 3).map((source, idx) => (
                          <div
                            key={idx}
                            className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg border border-gray-100"
                          >
                            <FileText className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-xs text-gray-600 line-clamp-2">{source.text}</p>
                              {source.document_title && (
                                <p className="text-xs text-gray-400 mt-1 truncate">
                                  {source.document_title}
                                </p>
                              )}
                            </div>
                            {source.score != null && (
                              <span className="text-xs text-primary-600 font-medium flex-shrink-0">
                                {(source.score * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0 order-2">
                      <User className="w-5 h-5 text-gray-600" />
                    </div>
                  )}
                </div>
              ))}
              <div ref={scrollRef} />
            </div>
          )}
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mx-4 mb-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
          {error}
        </div>
      )}

      {/* 输入区域 */}
      <div className="p-4 bg-white border-t border-gray-200">
        <div className="max-w-4xl mx-auto">
          <div className="relative flex items-end gap-3 bg-gray-100 border border-gray-200 rounded-xl p-2 focus-within:ring-2 focus-within:ring-primary-500 focus-within:border-transparent">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入问题... (Shift+Enter 换行)"
              rows={1}
              className="flex-1 resize-none bg-transparent border-none focus:outline-none px-3 py-2 text-sm max-h-32"
              style={{ minHeight: '40px' }}
              disabled={isLoading}
            />
            <button
              onClick={handleSubmit}
              disabled={isLoading || !input.trim() || selectedKbIds.length === 0}
              className="w-10 h-10 rounded-lg bg-primary-600 text-white flex items-center justify-center hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
