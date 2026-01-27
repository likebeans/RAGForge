import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'

export default function TrendChart({ title, subtitle, data, period, onPeriodChange, maxValue }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
          <p className="text-sm text-gray-400">{subtitle}</p>
        </div>
        <div className="flex bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => onPeriodChange('7d')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              period === '7d'
                ? 'bg-primary-500 text-white'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            近7天
          </button>
          <button
            onClick={() => onPeriodChange('30d')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              period === '30d'
                ? 'bg-primary-500 text-white'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            近30天
          </button>
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
            <XAxis
              dataKey="day"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#9CA3AF', fontSize: 12 }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#9CA3AF', fontSize: 12 }}
              domain={[0, maxValue]}
              ticks={[0, maxValue * 0.25, maxValue * 0.5, maxValue * 0.75, maxValue]}
            />
            <Tooltip
              cursor={{ fill: 'rgba(59, 130, 246, 0.1)' }}
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #E5E7EB',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Bar
              dataKey="value"
              fill="#3B82F6"
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
