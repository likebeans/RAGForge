import { useState } from 'react'
import { ChevronDown, MessageSquare, FileText, ClipboardList, ExternalLink } from 'lucide-react'
import StatsCard from '../components/StatsCard'
import TrendChart from '../components/TrendChart'

const aiDialogData = [
  { day: '周一', value: 35 },
  { day: '周二', value: 52 },
  { day: '周三', value: 58 },
  { day: '周四', value: 62 },
  { day: '周五', value: 85 },
  { day: '周六', value: 45 },
  { day: '周日', value: 28 }
]

const knowledgeData = [
  { day: '周一', value: 120 },
  { day: '周二', value: 165 },
  { day: '周三', value: 180 },
  { day: '周四', value: 175 },
  { day: '周五', value: 155 },
  { day: '周六', value: 140 },
  { day: '周日', value: 95 }
]

const activeProjects = [
  { name: '新药研发项目A', progress: 75, status: '进行中' },
  { name: '临床试验分析', progress: 45, status: '进行中' },
  { name: '文献综述自动化', progress: 90, status: '即将完成' }
]

const recentReports = [
  { title: '2024年Q4药物筛选报告', date: '2024-01-20', type: 'PDF' },
  { title: '临床数据分析摘要', date: '2024-01-19', type: 'DOCX' },
  { title: '分子对接结果汇总', date: '2024-01-18', type: 'PDF' }
]

export default function Dashboard() {
  const [selectedProject, setSelectedProject] = useState('AI 新药研发项目')
  const [aiPeriod, setAiPeriod] = useState('7d')
  const [kbPeriod, setKbPeriod] = useState('7d')

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">工作台</h1>
      </div>

      {/* 项目选择器 */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-500">当前项目</span>
        <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm hover:bg-gray-50">
          <span>{selectedProject}</span>
          <ChevronDown className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatsCard
          title="今日 AI 对话"
          value="125 条"
          subtitle="较昨日增加 10%"
          icon={MessageSquare}
        />
        <StatsCard
          title="近期文档浏览"
          value="240 篇"
          subtitle="近 7 天活跃度"
          icon={FileText}
        />
        <StatsCard
          title="待办任务"
          value="7 项"
          subtitle="即将到期 3 项"
          icon={ClipboardList}
        />
      </div>

      {/* 数据趋势分析 */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">数据趋势分析</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TrendChart
            title="AI 对话使用趋势"
            subtitle="每日/每周对话量变化"
            data={aiDialogData}
            period={aiPeriod}
            onPeriodChange={setAiPeriod}
            maxValue={100}
          />
          <TrendChart
            title="知识库交互趋势"
            subtitle="每日/每周文档查阅与编辑次数"
            data={knowledgeData}
            period={kbPeriod}
            onPeriodChange={setKbPeriod}
            maxValue={220}
          />
        </div>
      </div>

      {/* 活跃项目概览 & 最新报告 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 活跃项目概览 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">活跃项目概览</h3>
          <div className="space-y-4">
            {activeProjects.map((project, index) => (
              <div key={index} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-gray-700">{project.name}</span>
                  <span className="text-gray-500">{project.progress}%</span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-500 rounded-full transition-all"
                    style={{ width: `${project.progress}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 最新报告 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">最新报告</h3>
            <button className="flex items-center gap-1 text-sm text-gray-500 hover:text-primary-600">
              <span>查看所有报告</span>
              <ExternalLink className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-3">
            {recentReports.map((report, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                    <FileText className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-700">{report.title}</p>
                    <p className="text-xs text-gray-400">{report.date}</p>
                  </div>
                </div>
                <span className="text-xs font-medium text-gray-500 bg-gray-200 px-2 py-1 rounded">
                  {report.type}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
