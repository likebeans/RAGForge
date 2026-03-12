import { useState, useEffect } from 'react'
import { X, Save, Edit2 } from 'lucide-react'

export default function ProjectModal({ 
  project, 
  mode, // 'view' or 'edit'
  onClose, 
  onSave, 
  dicts 
}) {
  const [formData, setFormData] = useState({})
  const [activeTab, setActiveTab] = useState('basic')

  useEffect(() => {
    if (project) {
      setFormData(JSON.parse(JSON.stringify(project)))
    } else {
      // 新增时初始化空表单
      setFormData({})
    }
  }, [project])

  const handleChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    await onSave(formData)
  }

  const tabs = [
    { id: 'basic', label: '基本信息' },
    { id: 'clinical', label: '临床与适应症' },
    { id: 'business', label: '商业价值' },
    { id: 'other', label: '其他信息' }
  ]

  const renderField = (label, key, type = 'text', options = null) => {
    const isEditing = mode === 'edit' || mode === 'create'
    const value = formData[key]

    if (!isEditing) {
      let displayValue = value
      if (options) {
        displayValue = options.find(opt => opt.code === value)?.label || value
      }
      return (
        <div className="mb-4">
          <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
          <div className="text-sm text-gray-900 min-h-[20px]">{displayValue || '-'}</div>
        </div>
      )
    }

    if (options) {
      return (
        <div className="mb-4">
          <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
          <select
            value={value || ''}
            onChange={(e) => handleChange(key, e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white"
          >
            <option value="">请选择</option>
            {options.map(opt => (
              <option key={opt.code} value={opt.code}>{opt.label}</option>
            ))}
          </select>
        </div>
      )
    }

    if (type === 'textarea') {
      return (
        <div className="mb-4 col-span-full">
          <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
          <textarea
            value={value || ''}
            onChange={(e) => handleChange(key, e.target.value)}
            rows={3}
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
          />
        </div>
      )
    }

    return (
      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
        <input
          type={type}
          value={value || ''}
          onChange={(e) => handleChange(key, e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
        />
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">
            {mode === 'create' ? '新增数据' : mode === 'edit' ? '编辑数据' : '数据详情'}
          </h2>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex px-6 border-b border-gray-100">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <form id="project-form" onSubmit={handleSubmit}>
            <div className={activeTab === 'basic' ? 'block' : 'hidden'}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {renderField('项目名称', 'drug_name')}
                {renderField('靶点', 'target_name')}
                {renderField('作用机制', 'mechanism')}
                {renderField('药物类型', 'drug_type', 'text', dicts.drug_type)}
                {renderField('药物剂型', 'dosage_form', 'text', dicts.dosage_form)}
                {renderField('研究阶段', 'dev_phase', 'text', [
                  { code: 'PRE_CLINICAL', label: '临床前' },
                  { code: 'PHASE_I', label: 'I 期' },
                  { code: 'PHASE_II', label: 'II 期' },
                  { code: 'PHASE_III', label: 'III 期' },
                  { code: 'NDA', label: '上市申请' },
                  { code: 'APPROVED', label: '已上市' },
                ])}
                {renderField('项目状态', 'overall_status', 'text', [
                  { code: 'SCREENING', label: '初筛' },
                  { code: 'IN_PROGRESS', label: '进行中' },
                  { code: 'MONITORING', label: '监控' },
                  { code: 'ARCHIVED', label: '归档' },
                  { code: 'RESTARTED', label: '已重启' },
                ])}
              </div>
            </div>

            <div className={activeTab === 'clinical' ? 'block' : 'hidden'}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {renderField('适应症', 'indication')}
                {renderField('适应症类型', 'indication_type', 'text', dicts.indication_type)}
                {renderField('主要药效指标', 'efficacy_indicators', 'textarea')}
                {renderField('主要安全性指标', 'safety_indicators', 'textarea')}
                {renderField('当前标准疗法', 'current_therapy', 'textarea')}
              </div>
            </div>

            <div className={activeTab === 'business' ? 'block' : 'hidden'}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {renderField('综合评分', 'overall_score', 'number')}
                {renderField('战略匹配度', 'strategic_fit_score', 'number')}
                {renderField('项目估值(万)', 'project_valuation', 'number')}
                {renderField('公司估值(万)', 'company_valuation', 'number')}
                {renderField('报价(万)', 'asking_price', 'number')}
                {renderField('专利状态', 'patent_status')}
                {renderField('专利布局', 'patent_layout', 'textarea')}
                {renderField('竞争格局', 'competition_status', 'textarea')}
              </div>
            </div>

            <div className={activeTab === 'other' ? 'block' : 'hidden'}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {renderField('项目亮点', 'project_highlights', 'textarea')}
                {renderField('差异化优势', 'differentiation', 'textarea')}
                {renderField('风险提示', 'risk_notes', 'textarea')}
                {renderField('项目负责人', 'project_leader')}
              </div>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-3 bg-gray-50 rounded-b-xl">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            {(mode === 'edit' || mode === 'create') ? '取消' : '关闭'}
          </button>
          {(mode === 'edit' || mode === 'create') && (
            <button
              type="submit"
              form="project-form"
              className="px-4 py-2 text-sm text-white bg-primary-600 rounded-lg hover:bg-primary-700 flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              保存更改
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
