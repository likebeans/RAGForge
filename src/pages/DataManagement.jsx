import { useState, useEffect } from 'react'
import { Download, Upload, Plus, Briefcase, FileSpreadsheet, RefreshCw, BarChart3, Layers, Clock, FileText } from 'lucide-react'
import backendClient from '../services/backend'
import ProjectFilters from './projects/components/ProjectFilters'
import ProjectTable from './projects/components/ProjectTable'
import ProjectModal from './projects/components/ProjectModal'
import PdfExtractModal from './projects/components/PdfExtractModal'

export default function DataManagement() {
  // 状态管理
  const [projects, setProjects] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [dicts, setDicts] = useState({})
  const [lastUpdate, setLastUpdate] = useState(null)
  
  // 模态框状态
  const [modal, setModal] = useState({
    show: false,
    mode: 'view', // 'view' | 'edit' | 'create'
    project: null
  })
  
  // PDF 智能提取模态框
  const [showPdfExtract, setShowPdfExtract] = useState(false)

  // 筛选条件
  const [filters, setFilters] = useState({
    keyword: '',
    drug_type: '',
    dev_phase: '',
    score_min: '',
    score_max: '',
  })

  // 初始化加载
  useEffect(() => {
    loadDicts()
  }, [])

  // 监听分页变化
  useEffect(() => {
    loadProjects()
  }, [page])

  const loadDicts = async () => {
    try {
      const data = await backendClient.getDicts()
      setDicts(data)
    } catch (error) {
      console.error('加载字典失败:', error)
    }
  }

  const loadProjects = async () => {
    setLoading(true)
    try {
      const params = { page, page_size: pageSize, ...filters }
      // 清理空值参数
      Object.keys(params).forEach(key => {
        if (params[key] === '' || params[key] === null || params[key] === undefined) {
          delete params[key]
        }
      })
      
      const data = await backendClient.getProjects(params)
      setProjects(data.items)
      setTotal(data.total)
      setLastUpdate(new Date())
    } catch (error) {
      console.error('加载数据失败:', error)
      alert('加载数据失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  // 事件处理
  const handleSearch = () => {
    setPage(1)
    loadProjects()
  }

  const handleReset = () => {
    const emptyFilters = {
      keyword: '',
      drug_type: '',
      dev_phase: '',
      score_min: '',
      score_max: '',
    }
    setFilters(emptyFilters)
    setPage(1)
    
    // 立即触发一次重置后的查询
    setLoading(true)
    backendClient.getProjects({ page: 1, page_size: pageSize, ...emptyFilters })
      .then(data => {
        setProjects(data.items)
        setTotal(data.total)
      })
      .catch(err => {
        console.error('重置查询失败:', err)
        alert('重置查询失败: ' + err.message)
      })
      .finally(() => setLoading(false))
  }

  const handleImport = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!confirm('确定要导入数据吗？将以追加模式导入。')) return

    try {
      const result = await backendClient.importProjects(file, 'append')
      alert(`导入完成！\n成功: ${result.success_count}\n失败: ${result.error_count}`)
      if (result.errors?.length > 0) {
        console.error('导入错误:', result.errors)
      }
      loadProjects()
    } catch (error) {
      alert('导入失败: ' + error.message)
    }
    e.target.value = ''
  }

  const handleExport = async () => {
    try {
      const params = { ...filters }
      Object.keys(params).forEach(key => !params[key] && delete params[key])
      
      const blob = await backendClient.exportProjects(params)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `projects_export_${new Date().toISOString().slice(0,10)}.xlsx`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      alert('导出失败: ' + error.message)
    }
  }

  const handleDownloadTemplate = async () => {
    try {
      const blob = await backendClient.downloadTemplate()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'project_import_template.xlsx'
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      alert('下载模板失败: ' + error.message)
    }
  }

  const handleDelete = async (project) => {
    if (!confirm(`确定要删除项目 "${project.project_name}" 吗？此操作不可恢复。`)) return
    
    try {
      await backendClient.deleteProject(project.id)
      loadProjects()
    } catch (error) {
      alert('删除失败: ' + error.message)
    }
  }

  const handleSaveProject = async (data) => {
    try {
      if (modal.mode === 'edit') {
        await backendClient.updateProject(data.id, data)
      } else {
        // 暂未实现创建API的前端调用，预留
        await backendClient.createProject(data)
      }
      setModal({ show: false, mode: 'view', project: null })
      loadProjects()
    } catch (error) {
      alert('保存失败: ' + error.message)
    }
  }

  // 计算统计数据
  const getStats = () => {
    const drugTypes = {}
    const stages = {}
    projects.forEach(p => {
      if (p.drug_type) drugTypes[p.drug_type] = (drugTypes[p.drug_type] || 0) + 1
      if (p.dev_phase) stages[p.dev_phase] = (stages[p.dev_phase] || 0) + 1
    })
    return {
      drugTypeCount: Object.keys(drugTypes).length,
      stageCount: Object.keys(stages).length
    }
  }
  const stats = getStats()

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/30">
              <Briefcase className="w-5 h-5 text-white" />
            </div>
            项目管理中心
          </h1>
          <p className="text-gray-500 mt-1">
            统一管理研发项目资产，支持多维度筛选、批量导入导出
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Clock className="w-4 h-4" />
          {lastUpdate ? `更新于 ${lastUpdate.toLocaleTimeString()}` : '加载中...'}
        </div>
      </div>

      {/* 操作工具栏 */}
      <div className="bg-white rounded-xl border border-gray-100 p-4 mb-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">数据操作</span>
            <span className="text-xs text-gray-400">|</span>
            <span className="text-xs text-gray-500">支持 Excel 格式 (.xlsx, .xls)</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <button 
              onClick={handleDownloadTemplate}
              className="px-3 py-1.5 text-sm bg-gray-50 text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-1.5"
            >
              <FileSpreadsheet className="w-4 h-4" />
              下载模板
            </button>
            
            <label className="px-3 py-1.5 text-sm bg-blue-50 text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors flex items-center gap-1.5 cursor-pointer">
              <Upload className="w-4 h-4" />
              导入数据
              <input type="file" accept=".xlsx,.xls" onChange={handleImport} className="hidden" />
            </label>
            
            <button 
              onClick={handleExport}
              className="px-3 py-1.5 text-sm bg-green-50 text-green-700 border border-green-200 rounded-lg hover:bg-green-100 transition-colors flex items-center gap-1.5"
            >
              <Download className="w-4 h-4" />
              导出数据
            </button>

            <button 
              onClick={() => setShowPdfExtract(true)}
              className="px-3 py-1.5 text-sm bg-violet-50 text-violet-700 border border-violet-200 rounded-lg hover:bg-violet-100 transition-colors flex items-center gap-1.5"
            >
              <FileText className="w-4 h-4" />
              PDF 智能提取
            </button>

            <button 
              onClick={() => setModal({ show: true, mode: 'create', project: null })} 
              className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              新增记录
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <ProjectFilters 
        filters={filters}
        setFilters={setFilters}
        onSearch={handleSearch}
        onReset={handleReset}
        dicts={dicts}
      />

      {/* Table */}
      <ProjectTable 
        projects={projects}
        loading={loading}
        dicts={dicts}
        pagination={{
          page,
          total,
          totalPages: Math.ceil(total / pageSize)
        }}
        onPageChange={setPage}
        onView={(project) => setModal({ show: true, mode: 'view', project })}
        onEdit={(project) => setModal({ show: true, mode: 'edit', project })}
        onDelete={handleDelete}
      />


      {/* Detail/Edit Modal */}
      {modal.show && (
        <ProjectModal
          project={modal.project}
          mode={modal.mode}
          dicts={dicts}
          onClose={() => setModal({ show: false, mode: 'view', project: null })}
          onSave={handleSaveProject}
        />
      )}

      {/* PDF 智能提取模态框 */}
      <PdfExtractModal
        show={showPdfExtract}
        onClose={() => setShowPdfExtract(false)}
      />
    </div>
  )
}
