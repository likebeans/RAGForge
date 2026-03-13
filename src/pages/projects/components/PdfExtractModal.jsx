import { useState, useEffect, useRef } from 'react'
import { X, Upload, FileSpreadsheet, FilePlus, Trash2, FileText, Download, Loader2, Check, AlertCircle, Save, Database } from 'lucide-react'
import backendClient from '../../../services/backend'

export default function PdfExtractModal({ show, onClose }) {
  const [step, setStep] = useState(1) // 1: 选择模板, 2: 上传PDF, 3: 提取结果, 4: 入库结果
  const [schemas, setSchemas] = useState([])
  const [selectedSchema, setSelectedSchema] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // 创建模板
  const [showCreateSchema, setShowCreateSchema] = useState(false)
  const [newSchemaName, setNewSchemaName] = useState('')
  const [newSchemaFile, setNewSchemaFile] = useState(null)
  
  // PDF 上传
  const [pdfFiles, setPdfFiles] = useState([])
  const pdfInputRef = useRef(null)
  
  // 提取结果
  const [extractResult, setExtractResult] = useState(null)
  const [extracting, setExtracting] = useState(false)
  
  // 入库状态
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState(null)

  useEffect(() => {
    if (show) {
      loadSchemas()
      setStep(1)
      setSelectedSchema(null)
      setPdfFiles([])
      setExtractResult(null)
      setSaveResult(null)
      setError('')
    }
  }, [show])

  // 使用 qwen-plus 提取 PDF（不需要模板）
  const handleExtractWithQwen = async () => {
    if (pdfFiles.length === 0) return
    
    setExtracting(true)
    setError('')
    try {
      // 使用 qwen-plus 接口提取
      const result = await backendClient.extractFromPdfsWithQwen(pdfFiles[0])
      setExtractResult(result)
      setStep(3)
    } catch (err) {
      setError('提取失败: ' + err.message)
    } finally {
      setExtracting(false)
    }
  }

  // 确认入库
  const handleSaveAndIngest = async () => {
    if (!extractResult || !pdfFiles[0]) return
    
    setSaving(true)
    setError('')
    try {
      const result = await backendClient.saveAndIngest(
        '71dd8415-8a4b-4543-b6f0-8f11e3b88176',
        extractResult.extracted_fields,
        pdfFiles[0]
      )
      setSaveResult(result)
      setStep(4)
    } catch (err) {
      setError('入库失败: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  const loadSchemas = async () => {
    setLoading(true)
    try {
      const data = await backendClient.listExtractionSchemas()
      setSchemas(data.items || data || [])
    } catch (err) {
      setError('加载模板列表失败: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateSchema = async () => {
    if (!newSchemaFile || !newSchemaName.trim()) {
      setError('请输入模板名称并选择 Excel 文件')
      return
    }
    
    setLoading(true)
    setError('')
    try {
      const result = await backendClient.createExtractionSchema(newSchemaFile, newSchemaName.trim())
      setSchemas(prev => [...prev, result])
      setShowCreateSchema(false)
      setNewSchemaName('')
      setNewSchemaFile(null)
      setSelectedSchema(result)
    } catch (err) {
      setError('创建模板失败: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteSchema = async (schemaId, e) => {
    e.stopPropagation()
    if (!confirm('确定删除此模板？')) return
    
    try {
      await backendClient.deleteExtractionSchema(schemaId)
      setSchemas(prev => prev.filter(s => s.id !== schemaId))
      if (selectedSchema?.id === schemaId) {
        setSelectedSchema(null)
      }
    } catch (err) {
      setError('删除失败: ' + err.message)
    }
  }

  const handlePdfSelect = (e) => {
    const files = Array.from(e.target.files)
    setPdfFiles(prev => [...prev, ...files])
  }

  const removePdfFile = (index) => {
    setPdfFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleExtract = async (outputFormat = 'json') => {
    if (!selectedSchema || pdfFiles.length === 0) return
    
    setExtracting(true)
    setError('')
    try {
      const result = await backendClient.extractFromPdfs(selectedSchema.id, pdfFiles, outputFormat)
      
      if (outputFormat === 'excel') {
        // 下载 Excel 文件
        const url = URL.createObjectURL(result)
        const a = document.createElement('a')
        a.href = url
        a.download = 'extraction_result.xlsx'
        a.click()
        URL.revokeObjectURL(url)
      } else {
        setExtractResult(result)
        setStep(3)
      }
    } catch (err) {
      setError('提取失败: ' + err.message)
    } finally {
      setExtracting(false)
    }
  }

  const downloadExcel = async () => {
    await handleExtract('excel')
  }

  if (!show) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">PDF 智能提取</h2>
              <p className="text-sm text-gray-500">上传 PDF 文件，按模板提取字段生成 Excel</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Steps */}
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
          <div className="flex items-center justify-center gap-4">
            {[
              { num: 1, label: '选择模板' },
              { num: 2, label: '上传 PDF' },
              { num: 3, label: '提取结果' }
            ].map((s, idx) => (
              <div key={s.num} className="flex items-center">
                <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
                  step === s.num ? 'bg-violet-100 text-violet-700' : 
                  step > s.num ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                    step === s.num ? 'bg-violet-600 text-white' : 
                    step > s.num ? 'bg-green-500 text-white' : 'bg-gray-300 text-white'
                  }`}>
                    {step > s.num ? <Check className="w-4 h-4" /> : s.num}
                  </div>
                  <span className="font-medium">{s.label}</span>
                </div>
                {idx < 2 && <div className="w-12 h-0.5 bg-gray-200 mx-2" />}
              </div>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-600">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">{error}</span>
            <button onClick={() => setError('')} className="ml-auto text-red-400 hover:text-red-600">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Step 1: 选择模板 */}
          {step === 1 && (
            <div className="space-y-4">
              {/* 默认模板选项 */}
              <div 
                onClick={() => { setSelectedSchema(null); setStep(2) }}
                className={`p-4 border-2 rounded-xl cursor-pointer transition-all ${
                  selectedSchema === null
                    ? 'border-violet-500 bg-violet-50'
                    : 'border-gray-200 hover:border-violet-300 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    selectedSchema === null ? 'bg-violet-500 text-white' : 'bg-gray-100 text-gray-600'
                  }`}>
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">默认模板 (Qwen-PLUS)</h4>
                    <p className="text-sm text-gray-500">使用系统默认的30个字段模板，无需创建模板</p>
                  </div>
                  {selectedSchema === null && <Check className="w-5 h-5 text-violet-600" />}
                </div>
              </div>

              <div className="flex items-center gap-2 text-gray-400">
                <div className="flex-1 h-px bg-gray-200"></div>
                <span className="text-sm">或选择已有模板</span>
                <div className="flex-1 h-px bg-gray-200"></div>
              </div>

              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">选择提取模板</h3>
                <button
                  onClick={() => setShowCreateSchema(true)}
                  className="px-3 py-1.5 text-sm bg-violet-50 text-violet-600 rounded-lg hover:bg-violet-100 flex items-center gap-1"
                >
                  <FilePlus className="w-4 h-4" />
                  新建模板
                </button>
              </div>

              {/* 创建模板表单 */}
              {showCreateSchema && (
                <div className="p-4 bg-violet-50 rounded-xl border border-violet-100 space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">模板名称</label>
                    <input
                      type="text"
                      value={newSchemaName}
                      onChange={(e) => setNewSchemaName(e.target.value)}
                      placeholder="如：产品信息提取"
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Excel 模板文件</label>
                    <p className="text-xs text-gray-500 mb-2">第一行为字段名，第二行为字段类型（string/number/date）</p>
                    <input
                      type="file"
                      accept=".xlsx,.xls"
                      onChange={(e) => setNewSchemaFile(e.target.files[0])}
                      className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-violet-100 file:text-violet-700 hover:file:bg-violet-200"
                    />
                  </div>
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={handleCreateSchema}
                      disabled={loading}
                      className="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 flex items-center gap-2"
                    >
                      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                      创建模板
                    </button>
                    <button
                      onClick={() => { setShowCreateSchema(false); setNewSchemaName(''); setNewSchemaFile(null) }}
                      className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}

              {/* 模板列表 */}
              {loading && !showCreateSchema ? (
                <div className="flex items-center justify-center py-12 text-gray-500">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  加载中...
                </div>
              ) : schemas.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p>暂无模板，请先创建一个提取模板</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {schemas.map(schema => (
                    <div
                      key={schema.id}
                      onClick={() => setSelectedSchema(schema)}
                      className={`p-4 border-2 rounded-xl cursor-pointer transition-all ${
                        selectedSchema?.id === schema.id
                          ? 'border-violet-500 bg-violet-50'
                          : 'border-gray-200 hover:border-violet-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                            selectedSchema?.id === schema.id ? 'bg-violet-500 text-white' : 'bg-gray-100 text-gray-600'
                          }`}>
                            <FileSpreadsheet className="w-5 h-5" />
                          </div>
                          <div>
                            <h4 className="font-medium text-gray-900">{schema.name}</h4>
                            <p className="text-sm text-gray-500">{schema.fields?.length || 0} 个字段</p>
                          </div>
                        </div>
                        <button
                          onClick={(e) => handleDeleteSchema(schema.id, e)}
                          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      {schema.fields && (
                        <div className="mt-3 flex flex-wrap gap-1">
                          {schema.fields.slice(0, 4).map((f, i) => (
                            <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                              {f.name}
                            </span>
                          ))}
                          {schema.fields.length > 4 && (
                            <span className="px-2 py-0.5 text-gray-400 text-xs">+{schema.fields.length - 4}</span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step 2: 上传 PDF */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">上传 PDF 文件</h3>
                  <p className="text-sm text-gray-500">
                    {selectedSchema ? `已选模板: ${selectedSchema.name}` : '使用默认30字段模板'}
                  </p>
                </div>
              </div>

              {/* 上传区域 */}
              <div
                onClick={() => pdfInputRef.current?.click()}
                className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-violet-400 hover:bg-violet-50/50 transition-colors"
              >
                <Upload className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                <p className="text-gray-600 font-medium">点击或拖拽上传 PDF 文件</p>
                <p className="text-sm text-gray-400 mt-1">支持批量上传多个文件</p>
                <input
                  ref={pdfInputRef}
                  type="file"
                  accept=".pdf"
                  multiple
                  onChange={handlePdfSelect}
                  className="hidden"
                />
              </div>

              {/* 已选文件列表 */}
              {pdfFiles.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-700">已选择 {pdfFiles.length} 个文件</h4>
                  <div className="max-h-48 overflow-y-auto space-y-2">
                    {pdfFiles.map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <FileText className="w-5 h-5 text-red-500" />
                          <div>
                            <p className="text-sm font-medium text-gray-900">{file.name}</p>
                            <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                          </div>
                        </div>
                        <button
                          onClick={() => removePdfFile(idx)}
                          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: 提取结果 */}
          {step === 3 && extractResult && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">提取完成</h3>
                  <p className="text-sm text-gray-500">
                    共提取 {extractResult.extracted_fields?.length || 0} 个项目
                  </p>
                </div>
              </div>

              {/* 确认入库按钮 */}
              <div className="flex gap-3 p-4 bg-blue-50 border border-blue-200 rounded-xl">
                <div className="flex-1">
                  <h4 className="font-medium text-blue-900">确认入库</h4>
                  <p className="text-sm text-blue-700">
                    将提取的项目保存到数据库并入库到向量库
                  </p>
                </div>
                <button
                  onClick={handleSaveAndIngest}
                  disabled={saving}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 self-center"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
                  确认入库
                </button>
              </div>

              {/* 结果预览 */}
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <div className="overflow-x-auto max-h-96">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">#</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">项目</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">靶点</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">适应症</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">研究阶段</th>
                        <th className="px-4 py-3 text-left font-medium text-gray-600">研发机构</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {extractResult.extracted_fields?.map((item, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-500">{idx + 1}</td>
                          <td className="px-4 py-3 text-gray-900 font-medium">{item['项目'] || '-'}</td>
                          <td className="px-4 py-3 text-gray-600">{item['靶点'] || '-'}</td>
                          <td className="px-4 py-3 text-gray-600">{item['适应症'] || '-'}</td>
                          <td className="px-4 py-3 text-gray-600">{item['研究阶段'] || '-'}</td>
                          <td className="px-4 py-3 text-gray-600">{item['研发机构'] || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: 入库结果 */}
          {step === 4 && saveResult && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">入库完成</h3>
                  <p className="text-sm text-gray-500">
                    项目已保存到数据库，向量库入库成功
                  </p>
                </div>
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                  <Check className="w-6 h-6 text-green-600" />
                </div>
              </div>

              {/* 入库结果详情 */}
              <div className="p-4 bg-green-50 border border-green-200 rounded-xl space-y-3">
                <h4 className="font-medium text-green-900">保存结果</h4>
                {saveResult.saved_projects?.map((p, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm">
                    <span className="text-green-700">{p.project_name}</span>
                    <span className="text-green-500">- {p.status === 'created' ? '新建' : '更新'}</span>
                  </div>
                ))}
              </div>

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
                <h4 className="font-medium text-blue-900">向量库入库</h4>
                <p className="text-sm text-blue-700">
                  Document ID: <span className="font-mono">{saveResult.ragforge_document_id}</span>
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex justify-between bg-gray-50 rounded-b-2xl">
          <button
            onClick={() => step > 1 ? setStep(step - 1) : onClose()}
            className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg"
          >
            {step === 1 ? '取消' : '上一步'}
          </button>
          
          {/* Step 1: 下一步（选择默认模板或有模板时可用） */}
          {step === 1 && (
            <button
              onClick={() => setStep(2)}
              className="px-6 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700"
            >
              下一步
            </button>
          )}
          
          {step === 2 && (
            <button
              onClick={() => selectedSchema ? handleExtract('json') : handleExtractWithQwen()}
              disabled={pdfFiles.length === 0 || extracting}
              className="px-6 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {extracting && <Loader2 className="w-4 h-4 animate-spin" />}
              {selectedSchema ? '开始提取' : '使用 Qwen-PLUS 提取'}
            </button>
          )}
          
          {step === 3 && (
            <button
              onClick={onClose}
              className="px-6 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700"
            >
              完成
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
