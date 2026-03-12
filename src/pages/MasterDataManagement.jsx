import { Database } from 'lucide-react'

const dataDomains = [
  {
    code: 'Project_Master',
    title: '项目主表',
    description: '维护项目基础身份信息，是整个评估流程的锚点表。',
    tags: ['project_id', 'drug_name', 'target_id', 'indication', 'dev_phase', 'overall_status']
  },
  {
    code: 'Target_Dict',
    title: '标准靶点库',
    description: '统一靶点名称、别名和作用机制，支撑检索与标准化映射。',
    tags: ['target_id', 'standard_name', 'aliases', 'moa_default']
  },
  {
    code: 'Eval_Weights',
    title: '评分权重规则',
    description: '定义临床、市场、专利等维度的量化逻辑和权重值。',
    tags: ['criteria_id', 'dimension', 'weight_value', 'logic_desc']
  },
  {
    code: 'Monitoring_Config',
    title: '动态监控配置',
    description: '维护归档项目的守望关键词和触发条件，支撑后续重启评估。',
    tags: ['config_id', 'project_id', 'watch_keywords', 'trigger_event']
  }
]

const projectMasterFields = [
  ['project_id', 'String / PK', '项目唯一编码', '系统生成并贯穿全流程'],
  ['drug_name', 'String', '创新药或项目名称', '维护主名称口径'],
  ['target_id', 'String / FK', '关联标准靶点库', '建立标准化靶点映射'],
  ['indication', 'String', '适应症范围', '支持适应症分类和调研'],
  ['dev_phase', 'Enum', '研发阶段', '临床前 / I / II / III / 上市申请'],
  ['overall_status', 'Enum', '总状态', '初筛 / 进行中 / 归档 / 监控 / 已重启']
]

const weightFields = [
  ['criteria_id', 'String / PK', '评分指标 ID', '作为评分逻辑引用主键'],
  ['dimension', 'Enum', '评估维度', '如临床有效性、市场潜力、专利强度'],
  ['weight_value', 'Float', '权重分值', '作为总分计算依据'],
  ['logic_desc', 'Text', '打分逻辑说明', '保证规则透明可维护']
]

const monitoringFields = [
  ['config_id', 'String / PK', '规则 ID', '标识一条监控配置'],
  ['project_id', 'String / FK', '关联归档项目 ID', '将守望规则绑定到项目'],
  ['watch_keywords', 'String', '监控关键词', '如靶点名、竞品名、公司名'],
  ['trigger_event', 'String', '触发条件', '如竞品失败、节点推进、专利变化']
]

function FieldTable({ title, subtitle, rows }) {
  return (
    <section className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr className="text-left text-gray-500">
              <th className="px-6 py-3 font-medium">字段名</th>
              <th className="px-6 py-3 font-medium">类型</th>
              <th className="px-6 py-3 font-medium">说明</th>
              <th className="px-6 py-3 font-medium">规划用途</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row[0]} className="border-t border-gray-100">
                <td className="px-6 py-4 font-medium text-gray-900">{row[0]}</td>
                <td className="px-6 py-4 text-gray-600">{row[1]}</td>
                <td className="px-6 py-4 text-gray-600">{row[2]}</td>
                <td className="px-6 py-4 text-gray-600">{row[3]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default function MasterDataManagement() {
  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-800 to-slate-600 flex items-center justify-center shadow-lg shadow-slate-500/20">
              <Database className="w-5 h-5 text-white" />
            </div>
            数据管理
          </h1>
          <p className="mt-2 text-gray-500 max-w-3xl">
            基于《创新药项目评估系统》规划文档，这里用于维护项目基础主表、标准字典、评分权重和动态监控配置，
            为后续 1 到 8 步智能体协作提供统一的数据底座。
          </p>
        </div>
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-100 text-slate-700 text-sm">
          <span className="font-medium">规划驱动</span>
          <span>主表 / 字典 / 规则 / 监控</span>
        </div>
      </div>

      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {dataDomains.map((domain) => (
          <article key={domain.code} className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold tracking-[0.12em] text-gray-400 uppercase">{domain.code}</p>
                <h2 className="mt-2 text-lg font-semibold text-gray-900">{domain.title}</h2>
              </div>
              <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-medium">规划中</span>
            </div>
            <p className="mt-3 text-sm text-gray-500 leading-6">{domain.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {domain.tags.map((tag) => (
                <span key={tag} className="px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-medium">
                  {tag}
                </span>
              ))}
            </div>
          </article>
        ))}
      </section>

      <section className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
        <div className="flex flex-wrap gap-3">
          <span className="px-4 py-2 rounded-full bg-slate-900 text-white text-sm font-medium">基础主表</span>
          <span className="px-4 py-2 rounded-full bg-slate-100 text-slate-700 text-sm font-medium">标准字典</span>
          <span className="px-4 py-2 rounded-full bg-slate-100 text-slate-700 text-sm font-medium">评分规则</span>
          <span className="px-4 py-2 rounded-full bg-slate-100 text-slate-700 text-sm font-medium">监控配置</span>
        </div>
        <p className="mt-4 text-sm text-gray-500 leading-6">
          当前先把未来规划需要维护的数据域摊开，便于你后面继续决定是做成“多 Tab 管理台”，还是拆成“主表维护 / 字典维护 / 规则维护”三类独立页面。
        </p>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-[1.25fr_1fr] gap-6">
        <FieldTable
          title="项目主表字段设计"
          subtitle="来自规划文档的 Project_Master，承载项目基础身份信息和总状态。"
          rows={projectMasterFields}
        />

        <div className="space-y-6">
          <FieldTable
            title="评分权重规则字段"
            subtitle="对应 Eval_Weights，维护模型打分的量化逻辑。"
            rows={weightFields}
          />
          <FieldTable
            title="动态监控配置字段"
            subtitle="对应 Monitoring_Config，用于归档项目的持续守望和重启触发。"
            rows={monitoringFields}
          />
        </div>
      </div>
    </div>
  )
}
