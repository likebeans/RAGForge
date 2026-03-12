import { useState } from 'react'
import { Search, Filter, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'

export default function ProjectFilters({ filters, setFilters, onSearch, onReset, dicts }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const handleChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-3 mb-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-gray-800">
          <Filter className="w-5 h-5 text-primary-600" />
          <h3 className="font-semibold">数据筛选</h3>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* 关键词搜索 */}
        <div className="col-span-full md:col-span-2 lg:col-span-1">
          <label className="block text-xs font-medium text-gray-500 mb-1">关键词</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="项目名 / 靶点 / 适应症"
              value={filters.keyword}
              onChange={(e) => handleChange('keyword', e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
            />
          </div>
        </div>

        {/* 药物类型 */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">药物类型</label>
          <select 
            value={filters.drug_type} 
            onChange={(e) => handleChange('drug_type', e.target.value)}
            className="w-full px-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
          >
            <option value="">全部类型</option>
            {dicts.drug_type?.map(item => (
              <option key={item.code} value={item.code}>{item.label}</option>
            ))}
          </select>
        </div>

        {/* 研究阶段 */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">研究阶段</label>
          <select 
            value={filters.dev_phase} 
            onChange={(e) => handleChange('dev_phase', e.target.value)}
            className="w-full px-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
          >
            <option value="">全部阶段</option>
            <option value="PRE_CLINICAL">临床前</option>
            <option value="PHASE_I">I 期</option>
            <option value="PHASE_II">II 期</option>
            <option value="PHASE_III">III 期</option>
            <option value="NDA">上市申请</option>
            <option value="APPROVED">已上市</option>
          </select>
        </div>

        {/* 操作区 (占据第一排第4列) */}
        <div className="col-span-full md:col-span-2 lg:col-span-1 flex items-end gap-2">
          <button 
            onClick={onReset}
            className="flex-1 bg-white text-gray-600 border border-gray-200 px-3 py-1.5 text-xs rounded-lg hover:bg-gray-50 hover:text-gray-900 transition-colors flex items-center justify-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            重置
          </button>
          <button 
            onClick={onSearch}
            className="flex-1 bg-primary-600 text-white px-3 py-1.5 text-xs rounded-lg hover:bg-primary-700 active:bg-primary-800 transition-colors flex items-center justify-center gap-1.5 shadow-sm shadow-primary-600/30"
          >
            <Search className="w-3.5 h-3.5" />
            搜索
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex-none px-2 py-1.5 text-xs text-primary-600 hover:bg-primary-50 rounded-lg transition-colors flex items-center justify-center"
            title={isExpanded ? "收起筛选" : "展开筛选"}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        {/* 展开的第二排筛选项 */}
        {isExpanded && (
          <>
            {/* 适应症类型 */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">适应症类型</label>
              <select 
                value={filters.indication_type} 
                onChange={(e) => handleChange('indication_type', e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
              >
                <option value="">全部适应症</option>
                {dicts.indication_type?.map(item => (
                  <option key={item.code} value={item.code}>{item.label}</option>
                ))}
              </select>
            </div>

            {/* 靶点类型 */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">靶点类型</label>
              <select 
                value={filters.target_type} 
                onChange={(e) => handleChange('target_type', e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
              >
                <option value="">全部靶点类型</option>
                {dicts.target_type?.map(item => (
                  <option key={item.code} value={item.code}>{item.label}</option>
                ))}
              </select>
            </div>

            {/* 评分范围 */}
            <div className="col-span-full md:col-span-2">
              <label className="block text-xs font-medium text-gray-500 mb-1">综合评分范围</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  placeholder="Min"
                  value={filters.score_min}
                  onChange={(e) => handleChange('score_min', e.target.value)}
                  className="w-full px-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                />
                <span className="text-gray-400">-</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={filters.score_max}
                  onChange={(e) => handleChange('score_max', e.target.value)}
                  className="w-full px-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
