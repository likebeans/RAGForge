import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Edit2, Trash2, Loader2, AlertCircle, CheckCircle, FileText } from 'lucide-react'
import { backendClient } from '../services/backend'

function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

export default function ReportDetail() {
  const navigate = useNavigate()
  const { reportId } = useParams()

  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [message, setMessage] = useState(null)
  const [report, setReport] = useState(null)

  const showMessage = (type, text) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 3000)
  }

  const load = async () => {
    setLoading(true)
    try {
      const data = await backendClient.getReport(reportId)
      setReport(data)
    } catch (e) {
      showMessage('error', '加载失败: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [reportId])

  const handleDelete = async () => {
    if (!report) return
    if (!confirm(`确定删除报告「${report.title}」吗？`)) return
    setDeleting(true)
    try {
      await backendClient.deleteReport(report.id)
      showMessage('success', '已删除')
      navigate('/reports')
    } catch (e) {
      showMessage('error', '删除失败: ' + e.message)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/reports')}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              title="返回列表"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              <FileText className="w-7 h-7" />
              报告详情
            </h1>
          </div>
          <p className="text-gray-500 mt-1">查看报告内容与元信息</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/reports/${reportId}/edit`)}
            disabled={loading || !report}
            className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm disabled:opacity-50"
          >
            <Edit2 className="w-4 h-4" />
            编辑
          </button>
          <button
            onClick={handleDelete}
            disabled={loading || !report || deleting}
            className="flex items-center gap-2 px-3 py-2 border border-red-200 text-red-700 rounded-lg hover:bg-red-50 text-sm disabled:opacity-50"
          >
            {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            删除
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      ) : report ? (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900">{report.title}</h2>
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">创建人</p>
                <p className="text-sm font-mono text-gray-900 mt-1">
                  {report.created_by_username || report.created_by || '—'}
                </p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">创建时间</p>
                <p className="text-sm text-gray-900 mt-1">{formatDateTime(report.created_at)}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">更新时间</p>
                <p className="text-sm text-gray-900 mt-1">{formatDateTime(report.updated_at)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">报告内容</h3>
            <div className="whitespace-pre-wrap text-sm text-gray-900 leading-6">
              {report.content ? report.content : '—'}
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500">未找到报告</p>
        </div>
      )}

      {message && (
        <div className={`fixed bottom-4 right-4 max-w-md p-4 rounded-lg shadow-lg flex items-center gap-3 ${
          message.type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}>
          {message.type === 'success'
            ? <CheckCircle className="w-5 h-5 text-green-500" />
            : <AlertCircle className="w-5 h-5 text-red-500" />
          }
          <p className={`text-sm ${message.type === 'success' ? 'text-green-700' : 'text-red-700'}`}>
            {message.text}
          </p>
        </div>
      )}
    </div>
  )
}

