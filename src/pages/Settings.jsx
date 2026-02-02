import { useState, useEffect } from 'react'
import {
  Settings as SettingsIcon,
  Server,
  Key,
  Save,
  CheckCircle,
  AlertCircle,
  Loader2,
  RefreshCw,
  Eye,
  EyeOff,
  Globe,
  Cpu,
  Database
} from 'lucide-react'

const CONFIG_KEY = 'ragforge_config'

// 从 localStorage 或环境变量获取配置
const getStoredConfig = () => {
  try {
    const stored = localStorage.getItem(CONFIG_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (e) {
    console.error('Failed to load config:', e)
  }
  // 默认使用环境变量，强制用户通过设置页面配置
  return {
    baseUrl: import.meta.env.VITE_RAGFORGE_URL || '',
    apiKey: import.meta.env.VITE_RAGFORGE_API_KEY || ''
  }
}

const saveConfig = (config) => {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
  window.dispatchEvent(new CustomEvent('config-changed', { detail: config }))
}

export { getStoredConfig, saveConfig }

export default function Settings() {
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [modelSettings, setModelSettings] = useState(null)
  const [loadingModels, setLoadingModels] = useState(false)

  useEffect(() => {
    const config = getStoredConfig()
    setBaseUrl(config.baseUrl || '')
    setApiKey(config.apiKey || '')
  }, [])

  const handleSave = () => {
    setIsSaving(true)
    setSaveSuccess(false)
    
    setTimeout(() => {
      saveConfig({ baseUrl, apiKey })
      setIsSaving(false)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    }, 300)
  }

  const testConnection = async () => {
    setIsTesting(true)
    setTestResult(null)
    
    try {
      const response = await fetch(`${baseUrl}/health`)
      if (response.ok) {
        const data = await response.json()
        setTestResult({ 
          success: true, 
          message: `连接成功! 服务版本: ${data.version || 'unknown'}` 
        })
      } else {
        setTestResult({ 
          success: false, 
          message: `连接失败: HTTP ${response.status}` 
        })
      }
    } catch (err) {
      setTestResult({ 
        success: false, 
        message: `连接失败: ${err.message}` 
      })
    } finally {
      setIsTesting(false)
    }
  }

  const loadModelSettings = async () => {
    setLoadingModels(true)
    try {
      const response = await fetch(`${baseUrl}/v1/settings/models`, {
        headers: {
          'Authorization': `Bearer ${apiKey}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setModelSettings(data)
      } else {
        setModelSettings(null)
      }
    } catch (err) {
      console.error('Failed to load model settings:', err)
      setModelSettings(null)
    } finally {
      setLoadingModels(false)
    }
  }

  useEffect(() => {
    if (baseUrl && apiKey) {
      loadModelSettings()
    }
  }, [])

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
          <SettingsIcon className="w-7 h-7" />
          系统设置
        </h1>
        <p className="text-gray-500 mt-1">配置RAG服务连接和系统参数</p>
      </div>

      {/* API 配置 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Server className="w-5 h-5 text-primary-600" />
          服务配置
        </h2>
        
        <div className="space-y-4">
          {/* Base URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <Globe className="w-4 h-4 inline mr-1" />
              服务地址 (Base URL)
            </label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="http://localhost:8020"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-400 mt-1">RAGForge 后端服务的地址</p>
          </div>

          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <Key className="w-4 h-4 inline mr-1" />
              API Key
            </label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="kb_sk_xxxxxxxxxxxxxxxx"
                className="w-full px-4 py-2.5 pr-12 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showApiKey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">用于认证的 API 密钥</p>
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={testConnection}
              disabled={isTesting || !baseUrl}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {isTesting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              测试连接
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {isSaving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : saveSuccess ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {saveSuccess ? '已保存' : '保存配置'}
            </button>
          </div>

          {/* 测试结果 */}
          {testResult && (
            <div className={`flex items-center gap-2 p-3 rounded-lg ${
              testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            }`}>
              {testResult.success ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <AlertCircle className="w-5 h-5" />
              )}
              <span className="text-sm">{testResult.message}</span>
            </div>
          )}
        </div>
      </div>

      {/* 模型配置信息 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-primary-600" />
            模型配置
          </h2>
          <button
            onClick={loadModelSettings}
            disabled={loadingModels || !baseUrl || !apiKey}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
          >
            <RefreshCw className={`w-4 h-4 ${loadingModels ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>

        {loadingModels ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : modelSettings ? (
          <div className="space-y-4">
            {/* 默认模型 */}
            {modelSettings.defaults && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {modelSettings.defaults.llm && (
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500 mb-1">LLM 模型</p>
                    <p className="font-medium text-gray-900">{modelSettings.defaults.llm.model}</p>
                    <p className="text-xs text-gray-400">{modelSettings.defaults.llm.provider}</p>
                  </div>
                )}
                {modelSettings.defaults.embedding && (
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500 mb-1">Embedding 模型</p>
                    <p className="font-medium text-gray-900 text-sm">{modelSettings.defaults.embedding.model}</p>
                    <p className="text-xs text-gray-400">{modelSettings.defaults.embedding.provider}</p>
                  </div>
                )}
                {modelSettings.defaults.rerank && (
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500 mb-1">Rerank 模型</p>
                    <p className="font-medium text-gray-900 text-sm">{modelSettings.defaults.rerank.model}</p>
                    <p className="text-xs text-gray-400">{modelSettings.defaults.rerank.provider}</p>
                  </div>
                )}
              </div>
            )}

            {/* 提供商配置 */}
            {modelSettings.providers && Object.keys(modelSettings.providers).length > 0 && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">已配置的提供商</p>
                <div className="flex flex-wrap gap-2">
                  {Object.keys(modelSettings.providers).map(provider => (
                    <span key={provider} className="px-3 py-1 bg-primary-50 text-primary-700 rounded-full text-sm">
                      {provider}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Database className="w-10 h-10 mx-auto mb-2 text-gray-300" />
            <p>无法加载模型配置</p>
            <p className="text-xs text-gray-400 mt-1">请先保存有效的服务配置</p>
          </div>
        )}
      </div>
    </div>
  )
}
