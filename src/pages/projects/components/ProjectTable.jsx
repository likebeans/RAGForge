import { Eye, Edit2, Trash2, ChevronLeft, ChevronRight } from 'lucide-react'

// 徽章颜色映射
const BADGE_COLORS = {
  // 研究阶段
  preclinical: 'bg-gray-100 text-gray-700',
  phase1: 'bg-blue-50 text-blue-700',
  phase2: 'bg-indigo-50 text-indigo-700',
  phase3: 'bg-purple-50 text-purple-700',
  nda: 'bg-orange-50 text-orange-700',
  approved: 'bg-green-50 text-green-700',
  
  // 药物类型
  small_molecule: 'bg-slate-100 text-slate-700',
  biologic: 'bg-rose-50 text-rose-700',
  adc: 'bg-amber-50 text-amber-700',
  cell_therapy: 'bg-teal-50 text-teal-700',
  gene_therapy: 'bg-cyan-50 text-cyan-700',
}

export default function ProjectTable({ 
  projects, 
  loading, 
  dicts, 
  pagination,
  onPageChange,
  onView,
  onEdit,
  onDelete 
}) {
  const getLabel = (category, code) => {
    return dicts[category]?.find(d => d.code === code)?.label || code || '-'
  }

  const getBadgeColor = (code) => {
    return BADGE_COLORS[code] || 'bg-gray-50 text-gray-600'
  }

  // 适应症：兼容纯字符串 / JSON 数组字符串 / 实际数组
  const formatIndication = (indication) => {
    if (!indication) return null
    if (Array.isArray(indication)) return indication
    const str = String(indication).trim()
    // 尝试解析 JSON 数组
    if (str.startsWith('[')) {
      try {
        const parsed = JSON.parse(str)
        if (Array.isArray(parsed)) return parsed
      } catch (_) {}
      // 降级：去掉括号和引号后按逗号分割
      return str.replace(/^\[|\]$/g, '').split(',').map(s => s.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean)
    }
    // 普通字符串按逗号/顿号分割
    return str.split(/[,，、]/).map(s => s.trim()).filter(Boolean)
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
        <p className="text-gray-500">正在加载项目数据...</p>
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
        <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
          <span className="text-3xl">📭</span>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-1">暂无数据</h3>
        <p className="text-gray-500">尝试调整筛选条件或导入新数据</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">名称 / 靶点</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">药物类型</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">研究阶段</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">适应症</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">评分 / 估值</th>
              <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {projects.map((project) => (
              <tr key={project.id} className="hover:bg-gray-50/80 transition-colors group">
                <td className="px-6 py-4">
                  <div className="flex flex-col">
                    <span className="font-medium text-gray-900">{project.project_name}</span>
                    <span className="text-xs text-gray-500 mt-0.5">
                      靶点: {project.target_name || '-'}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getBadgeColor(project.drug_type)}`}>
                    {getLabel('drug_type', project.drug_type)}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getBadgeColor(project.dev_phase)}`}>
                    {project.dev_phase || '-'}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-wrap gap-1 max-w-[200px]">
                    {(() => {
                      const items = formatIndication(project.indication)
                      if (!items || items.length === 0) return <span className="text-sm text-gray-400">-</span>
                      return items.slice(0, 3).map((item, i) => (
                        <span key={i} className="inline-block px-1.5 py-0.5 bg-blue-50 text-blue-700 text-xs rounded">
                          {item}
                        </span>
                      )).concat(
                        items.length > 3
                          ? [<span key="more" className="text-xs text-gray-400">+{items.length - 3}</span>]
                          : []
                      )
                    })()}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-col">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-semibold text-primary-600">{project.overall_score || '-'}</span>
                      <span className="text-xs text-gray-400">分</span>
                    </div>
                    {project.asking_price && (
                      <span className="text-xs text-gray-500 mt-0.5">
                        ¥ {project.asking_price.toLocaleString()} 万
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button 
                      onClick={() => onView(project)}
                      className="p-1.5 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                      title="查看详情"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => onEdit(project)}
                      className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="编辑"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => onDelete(project)}
                      className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="删除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 分页控制 */}
      {pagination.totalPages > 1 && (
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between bg-gray-50/50">
          <div className="text-sm text-gray-500">
            显示 {projects.length} 条，共 {pagination.total} 条记录
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(Math.max(1, pagination.page - 1))}
              disabled={pagination.page === 1}
              className="p-1.5 border border-gray-200 rounded-lg hover:bg-white hover:text-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm font-medium text-gray-700 px-2">
              {pagination.page} / {pagination.totalPages}
            </span>
            <button
              onClick={() => onPageChange(Math.min(pagination.totalPages, pagination.page + 1))}
              disabled={pagination.page === pagination.totalPages}
              className="p-1.5 border border-gray-200 rounded-lg hover:bg-white hover:text-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
