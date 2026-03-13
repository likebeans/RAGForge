import { useState, useEffect, useRef } from 'react'
import {
  X, Upload, FileSpreadsheet, FilePlus, Trash2, FileText,
  Download, Loader2, Check, AlertCircle, DatabaseZap,
  ChevronDown, ChevronUp, CheckCircle2, XCircle
} from 'lucide-react'
import backendClient from '../../../services/backend'

// ─────────────────────────────────────────────
// 字段映射：PDF 解析结果 → ProjectCreate 结构
// TODO: 拿到实际解析返回值后在这里对齐字段名
// ─────────────────────────────────────────────
function mapExtractedToProject(item) {
  const f = item.fields || {}
  return {
    // ── project_master ──────────────────────
    project_name:      f.project_name      ?? f['项目名称']      ?? item.filename?.replace(/\.pdf$/i, '') ?? '',
    target_name:       f.target_name       ?? f['靶点']          ?? null,
    indication:        f.indication        ?? f['适应症']         ?? null,
    dev_phase:         f.dev_phase         ?? f['研发阶段']       ?? null,
    overall_status:    f.overall_status    ?? 'SCREENING',
    overall_score:     f.overall_score     != null ? parseFloat(f.overall_score)     : null,

    // ── project_details ─────────────────────
    drug_type:         f.drug_type         ?? f['药物类型']       ?? null,
    dosage_form:       f.dosage_form       ?? f['剂型']           ?? null,
    mechanism:         f.mechanism         ?? f['作用机制']       ?? null,
    project_highlights:f.project_highlights?? f['项目亮点']       ?? null,
    differentiation:   f.differentiation   ?? f['差异化优势']     ?? null,
    current_therapy:   f.current_therapy   ?? f['当前标准疗法']   ?? null,

    // ── project_valuations ──────────────────
    asking_price:      f.asking_price      != null ? parseFloat(f.asking_price)      : null,
    project_valuation: f.project_valuation != null ? parseFloat(f.project_valuation) : null,
    company_valuation: f.company_valuation != null ? parseFloat(f.company_valuation) : null,
    strategic_fit_score: f.strategic_fit_score != null ? parseFloat(f.strategic_fit_score) : null,

    // ── research_details ────────────────────
    policy_impact:     f.policy_impact     ?? f['政策影响']       ?? null,
    market_json:       f.market_json       ?? null,
    competitor_data:   f.competitor_data   ?? null,
    patent_json:       f.patent_json       ?? null,

    // ── project_management_info ─────────────
    risk_notes:        f.risk_notes        ?? f['风险提示']       ?? null,
  }
}

// 字段分组展示配置（给结果卡片用）
const FIELD_GROUPS = [
  {
    label: '基本信息',
    fields: [
      { key: 'project_name',    label: '项目名称' },
      { key: 'target_name',     label: '靶点' },
      { key: 'indication',      label: '适应症' },
      { key: 'dev_phase',       label: '研发阶段' },
      { key: 'overall_score',   label: '综合评分' },
    ],
  },
  {
    label: '研发详情',
    fields: [
      { key: 'drug_type',          label: '药物类型' },
      { key: 'dosage_form',        label: '剂型' },
      { key: 'mechanism',          label: '作用机制' },
      { key: 'project_highlights', label: '项目亮点' },
      { key: 'differentiation',    label: '差异化优势' },
    ],
  },
  {
    label: '估值信息',
    fields: [
      { key: 'asking_price',       label: '报价(万元)' },
      { key: 'project_valuation',  label: '项目估值(万元)' },
      { key: 'company_valuation',  label: '公司估值(万元)' },
      { key: 'strategic_fit_score',label: '战略匹配度' },
    ],
  },
  {
    label: '研究 & 管理',
    fields: [
      { key: 'policy_impact', label: '政策影响' },
      { key: 'risk_notes',    label: '风险提示' },
    ],
  },
]

// 导入状态 badge
function ImportBadge({ status }) {
  const map = {
    idle:      { label: '待导入',  cls: 'bg-gray-100 text-gray-500' },
    importing: { label: '导入中…', cls: 'bg-blue-100 text-blue-600' },
    success:   { label: '已导入',  cls: 'bg-green-100 text-green-700' },
    error:     { label: '导入失败',cls: 'bg-red-100 text-red-600' },
  }
  const { label, cls } = map[status] || map.idle
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>{label}</span>
}

// ─────────────────────────────────────────────
// 主组件
// ─────────────────────────────────────────────
export default function PdfExtractModal({ show, onClose }) {
  const [step, setStep] = useState(1)
  const [schemas, setSchemas] = useState([])
  const [selectedSchema, setSelectedSchema] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 新建模板
  const [showCreateSchema, setShowCreateSchema] = useState(false)
  const [newSchemaName, setNewSchemaName] = useState('')
  const [newSchemaFile, setNewSchemaFile] = useState(null)

  // PDF 上传
  const [pdfFiles, setPdfFiles] = useState([])
  const pdfInputRef = useRef(null)

  // 提取结果
  const [extractResult, setExtractResult] = useState(null)
  const [extracting, setExtracting] = useState(false)

  // 导入状态：{ [key]: 'idle' | 'importing' | 'success' | 'error' }
  const [importStatuses, setImportStatuses] = useState({})
  // 展开的结果卡片
  const [expandedItems, setExpandedItems] = useState({})

  useEffect(() => {
    if (show) {
      loadSchemas()
      setStep(1)
      setSelectedSchema(null)
      setPdfFiles([])
      setExtractResult(null)
      setImportStatuses({})
      setExpandedItems({})
      setError('')
    }
  }, [show])

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
      if (selectedSchema?.id === schemaId) setSelectedSchema(null)
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
        const url = URL.createObjectURL(result)
        const a = document.createElement('a')
        a.href = url
        a.download = 'extraction_result.xlsx'
        a.click()
        URL.revokeObjectURL(url)
      } else {
        setExtractResult(result)
        const initStatuses = {}
        ;(result.results || []).forEach((item, idx) => {
          initStatuses[itemKey(item, idx)] = 'idle'
        })
        setImportStatuses(initStatuses)
        setStep(3)
      }
    } catch (err) {
      setError('提取失败: ' + err.message)
    } finally {
      setExtracting(false)
    }
  }

  // 唯一 key：用 filename + idx 防重名
  const itemKey = (item, idx) => `${item.filename ?? idx}_${idx}`

  // 单条导入
  const handleImportOne = async (item, idx) => {
    const key = itemKey(item, idx)
    setImportStatuses(prev => ({ ...prev, [key]: 'importing' }))
    try {
      const projectData = mapExtractedToProject(item)
      await backendClient.createProject(projectData)
      setImportStatuses(prev => ({ ...prev, [key]: 'success' }))
    } catch (err) {
      setImportStatuses(prev => ({ ...prev, [key]: 'error' }))
      setError(`导入「${item.filename}」失败: ${err.message}`)
    }
  }

  // 全部导入（跳过已成功/正在导入）
  const handleImportAll = async () => {
    const items = extractResult?.results || []
    for (let idx = 0; idx < items.length; idx++) {
      const key = itemKey(items[idx], idx)
      if (importStatuses[key] === 'success' || importStatuses[key] === 'importing') continue
      await handleImportOne(items[idx], idx)
    }
  }

  const importedCount  = Object.values(importStatuses).filter(s => s === 'success').length
  const importingCount = Object.values(importStatuses).filter(s => s === 'importing').length
  const totalItems     = extractResult?.results?.length ?? 0

  const toggleExpand = (key) =>
    setExpandedItems(prev => ({ ...prev, [key]: !prev[key] }))

  if (!show) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">PDF 智能提取</h2>
              <p className="text-sm text-gray-500">上传 PDF，按模板提取字段并导入项目库</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* ── Steps ── */}
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
          <div className="flex items-center justify-center gap-4">
            {[
              { num: 1, label: '选择模板' },
              { num: 2, label: '上传 PDF' },
              { num: 3, label: '提取 & 导入' },
            ].map((s, idx) => (
              <div key={s.num} className="flex items-center">
                <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
                  step === s.num ? 'bg-violet-100 text-violet-700' :
                  step > s.num  ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                    step === s.num ? 'bg-violet-600 text-white' :
                    step > s.num  ? 'bg-green-500 text-white' : 'bg-gray-300 text-white'
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

        {/* ── Error Banner ── */}
        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-600">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm flex-1">{error}</span>
            <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ── Content ── */}
        <div className="flex-1 overflow-y-auto p-6">

          {/* Step 1: 选择模板 */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">选择提取模板</h3>
                <button
                  onClick={() => setShowCreateSchema(true)}
                  className="px-3 py-1.5 text-sm bg-violet-50 text-violet-600 rounded-lg hover:bg-violet-100 flex items-center gap-1"
                >
                  <FilePlus className="w-4 h-4" />新建模板
                </button>
              </div>

              {showCreateSchema && (
                <div className="p-4 bg-violet-50 rounded-xl border border-violet-100 space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">模板名称</label>
                    <input
                      type="text"
                      value={newSchemaName}
                      onChange={(e) => setNewSchemaName(e.target.value)}
                      placeholder="如：创新药项目提取"
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Excel 模板文件</label>
                    <p className="text-xs text-gray-500 mb-2">第一行字段名，第二行字段类型（string / number / date）</p>
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

              {loading && !showCreateSchema ? (
                <div className="flex items-center justify-center py-12 text-gray-500">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" />加载中...
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
                            <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">{f.name}</span>
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
              <div>
                <h3 className="font-medium text-gray-900">上传 PDF 文件</h3>
                <p className="text-sm text-gray-500">已选模板：{selectedSchema?.name}</p>
              </div>
              <div
                onClick={() => pdfInputRef.current?.click()}
                className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-violet-400 hover:bg-violet-50/50 transition-colors"
              >
                <Upload className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                <p className="text-gray-600 font-medium">点击或拖拽上传 PDF 文件</p>
                <p className="text-sm text-gray-400 mt-1">支持批量上传多个文件</p>
                <input ref={pdfInputRef} type="file" accept=".pdf" multiple onChange={handlePdfSelect} className="hidden" />
              </div>

              {pdfFiles.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-700">已选 {pdfFiles.length} 个文件</h4>
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
                        <button onClick={() => removePdfFile(idx)} className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg">
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: 提取结果 & 导入 */}
          {step === 3 && extractResult && (
            <div className="space-y-4">
              {/* 统计栏 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    提取成功 {extractResult.success ?? totalItems} 条
                  </div>
                  {(extractResult.failed ?? 0) > 0 && (
                    <div className="flex items-center gap-2 text-sm text-red-500">
                      <XCircle className="w-4 h-4" />
                      失败 {extractResult.failed} 条
                    </div>
                  )}
                  {importedCount > 0 && (
                    <div className="flex items-center gap-2 text-sm text-violet-600">
                      <DatabaseZap className="w-4 h-4" />
                      已导入 {importedCount} / {totalItems}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleExtract('excel')}
                    disabled={extracting}
                    className="px-3 py-1.5 text-sm border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 flex items-center gap-1.5"
                  >
                    {extracting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                    下载 Excel
                  </button>
                  <button
                    onClick={handleImportAll}
                    disabled={importingCount > 0 || importedCount === totalItems}
                    className="px-3 py-1.5 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 flex items-center gap-1.5"
                  >
                    <DatabaseZap className="w-4 h-4" />
                    {importedCount === totalItems ? '全部已导入' : '全部导入'}
                  </button>
                </div>
              </div>

              {/* 结果卡片列表 */}
              <div className="space-y-3">
                {(extractResult.results || []).map((item, idx) => {
                  const key = itemKey(item, idx)
                  const status = importStatuses[key] ?? 'idle'
                  const mapped = mapExtractedToProject(item)
                  const isExpanded = expandedItems[key]

                  return (
                    <div key={key} className="border border-gray-200 rounded-xl overflow-hidden">
                      {/* 卡片头部 */}
                      <div className="flex items-center justify-between px-4 py-3 bg-gray-50">
                        <div className="flex items-center gap-3 min-w-0">
                          <FileText className="w-4 h-4 text-red-400 flex-shrink-0" />
                          <span className="text-sm font-medium text-gray-900 truncate">{item.filename}</span>
                          <ImportBadge status={status} />
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                          {/* 导入按钮 */}
                          {status !== 'success' && (
                            <button
                              onClick={() => handleImportOne(item, idx)}
                              disabled={status === 'importing'}
                              className="px-3 py-1 text-xs bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 flex items-center gap-1"
                            >
                              {status === 'importing'
                                ? <Loader2 className="w-3 h-3 animate-spin" />
                                : <DatabaseZap className="w-3 h-3" />}
                              导入
                            </button>
                          )}
                          {status === 'success' && (
                            <span className="flex items-center gap-1 text-xs text-green-600">
                              <CheckCircle2 className="w-4 h-4" />已导入
                            </span>
                          )}
                          {/* 展开/收起 */}
                          <button
                            onClick={() => toggleExpand(key)}
                            className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded"
                          >
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>

                      {/* 展开详情：按系统表结构分组显示 */}
                      {isExpanded && (
                        <div className="px-4 py-3 grid grid-cols-2 gap-x-6 gap-y-4">
                          {FIELD_GROUPS.map(group => {
                            const nonEmpty = group.fields.filter(f => mapped[f.key] != null && mapped[f.key] !== '')
                            if (nonEmpty.length === 0) return null
                            return (
                              <div key={group.label}>
                                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                                  {group.label}
                                </p>
                                <div className="space-y-1.5">
                                  {nonEmpty.map(f => (
                                    <div key={f.key} className="flex items-start gap-2 text-sm">
                                      <span className="text-gray-400 w-24 flex-shrink-0">{f.label}</span>
                                      <span className="text-gray-800 break-all">
                                        {typeof mapped[f.key] === 'object'
                                          ? JSON.stringify(mapped[f.key])
                                          : String(mapped[f.key])}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="px-6 py-4 border-t border-gray-100 flex justify-between bg-gray-50 rounded-b-2xl">
          <button
            onClick={() => step > 1 ? setStep(step - 1) : onClose()}
            className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg"
          >
            {step === 1 ? '取消' : '上一步'}
          </button>

          {step === 1 && (
            <button
              onClick={() => setStep(2)}
              disabled={!selectedSchema}
              className="px-6 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              下一步
            </button>
          )}

          {step === 2 && (
            <button
              onClick={() => handleExtract('json')}
              disabled={pdfFiles.length === 0 || extracting}
              className="px-6 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {extracting && <Loader2 className="w-4 h-4 animate-spin" />}
              开始提取
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
