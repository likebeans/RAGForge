import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText,
  Plus,
  Download,
  RefreshCw,
  Search,
  Eye,
  Edit2,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { backendClient } from '../services/backend'
import { Document, Packer, Paragraph, TextRun, HeadingLevel } from 'docx'

import { saveAs } from 'file-saver'

function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  if (date.getFullYear() <= 1970) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

function stripHtml(html) {
  if (!html) return ''
  // If content is Markdown (which it is now), use marked to render it to HTML first
  // so that stripHtml can actually strip the tags.
  // Or, if it's just raw markdown text, stripHtml might not work as intended for things like **bold**.
  // But for a simple preview, rendering to HTML then stripping tags is a good way to get plain text.
  try {
    const rendered = marked.parse(html)
    const tmp = document.createElement('div')
    tmp.innerHTML = rendered
    return tmp.textContent || tmp.innerText || ''
  } catch (e) {
    return html
  }
}

export default function ReportsList() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, type: 'single', data: null })
  const [message, setMessage] = useState(null)

  const [keywordInput, setKeywordInput] = useState('')
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [selectedIds, setSelectedIds] = useState(() => new Set())

  const pageCount = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize])
  const selectedCount = selectedIds.size
  const allSelectedOnPage = useMemo(() => items.length > 0 && items.every(r => selectedIds.has(r.id)), [items, selectedIds])

  const showMessage = (type, text) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 3000)
  }

  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  const loadReports = async (opts = {}) => {
    setLoading(true)
    try {
      const res = await backendClient.getReports({
        page: opts.page ?? page,
        page_size: pageSize,
        keyword: keyword.trim() || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        status: 'published'
      })
      setItems(res.items || [])
      setTotal(res.total || 0)
    } catch (e) {
      showMessage('error', '加载失败: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => setKeyword(keywordInput), 300)
    return () => clearTimeout(timer)
  }, [keywordInput])

  useEffect(() => {
    loadReports()
  }, [page, pageSize])

  useEffect(() => {
    if (page !== 1) {
      setPage(1)
      return
    }
    loadReports({ page: 1 })
  }, [keyword, sortBy, sortOrder])

  const toggleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
      return
    }
    setSortBy(field)
    setSortOrder(field === 'created_at' ? 'desc' : 'asc')
  }

  const toggleSelect = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAllPage = () => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (allSelectedOnPage) {
        items.forEach(r => next.delete(r.id))
      } else {
        items.forEach(r => next.add(r.id))
      }
      return next
    })
  }

  const handleDelete = (report) => {
    if (!report || !report.id) {
      showMessage('error', '无效的报告信息')
      return
    }
    setDeleteConfirm({ open: true, type: 'single', data: report })
  }

  const handleBulkDelete = () => {
    if (selectedCount === 0) return
    setDeleteConfirm({ open: true, type: 'bulk', data: null })
  }

  const confirmDelete = async () => {
    const { type, data } = deleteConfirm
    setDeleteConfirm(prev => ({ ...prev, open: false })) // Close modal immediately

    if (type === 'single') {
      try {
        await backendClient.deleteReport(data.id)
        showMessage('success', '已删除')
        setSelectedIds(prev => {
          const next = new Set(prev)
          next.delete(data.id)
          return next
        })
        if (items.length === 1 && page > 1) {
          setPage(page - 1)
        } else {
          loadReports()
        }
      } catch (e) {
        showMessage('error', '删除失败: ' + e.message)
      }
    } else if (type === 'bulk') {
      setBulkDeleting(true)
      try {
        const res = await backendClient.bulkDeleteReports(Array.from(selectedIds))
        const deleted = res.deleted_count || 0
        showMessage('success', `已删除 ${deleted} 条`)
        setSelectedIds(new Set())
        loadReports()
      } catch (e) {
        showMessage('error', '批量删除失败: ' + e.message)
      } finally {
        setBulkDeleting(false)
      }
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const blob = await backendClient.exportReports(
        {
          keyword: keyword.trim() || undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
          status: 'published'
        },
        selectedCount > 0 ? Array.from(selectedIds) : null
      )
      const name = selectedCount > 0 ? `reports_selected_${selectedCount}.csv` : 'reports.csv'
      downloadBlob(blob, name)
      showMessage('success', '已导出')
    } catch (e) {
      showMessage('error', '导出失败: ' + e.message)
    } finally {
      setExporting(false)
    }
  }

  const handleExportWord = async (reportId) => {
    try {
      const r = await backendClient.getReport(reportId)
      const title = (r.title || '未命名报告').replace(/[\\/:*?"<>|]/g, '_')
      const content = r.content || ''

      // Parse Markdown to Tokens
      const tokens = marked.lexer(content)

      const children = []

      // Add Title
      children.push(
        new Paragraph({
          text: r.title || '未命名报告',
          heading: HeadingLevel.TITLE,
          spacing: { after: 200 }
        })
      )

      // Convert Tokens to Docx Paragraphs
      const processTokens = (tokens) => {
        const result = []
        tokens.forEach(token => {
          if (token.type === 'heading') {
            const level = token.depth === 1 ? HeadingLevel.HEADING_1 :
                          token.depth === 2 ? HeadingLevel.HEADING_2 :
                          token.depth === 3 ? HeadingLevel.HEADING_3 :
                          token.depth === 4 ? HeadingLevel.HEADING_4 :
                          token.depth === 5 ? HeadingLevel.HEADING_5 : HeadingLevel.HEADING_6
            result.push(new Paragraph({
              text: token.text,
              heading: level,
              spacing: { before: 200, after: 100 }
            }))
          } else if (token.type === 'paragraph') {
            // Check if paragraph contains an image
            if (token.tokens && token.tokens.some(t => t.type === 'image')) {
              // Image handling is complex in browser (CORS, async loading), skip for now or show placeholder
              result.push(new Paragraph({
                children: [new TextRun({ text: "[图片] (Word导出暂不支持图片)", italics: true, color: "888888" })],
                spacing: { after: 100 }
              }))
            } else {
              result.push(new Paragraph({
                children: [new TextRun(token.text)],
                spacing: { after: 100 }
              }))
            }
          } else if (token.type === 'list') {
            token.items.forEach(item => {
              result.push(new Paragraph({
                text: item.text,
                bullet: { level: 0 }
              }))
            })
          } else if (token.type === 'space') {
            // Ignore space
          } else {
             // Fallback for other types
             result.push(new Paragraph({
               children: [new TextRun(token.raw || '')],
               spacing: { after: 100 }
             }))
          }
        })
        return result
      }

      const docParagraphs = processTokens(tokens)
      children.push(...docParagraphs)

      const doc = new Document({
        sections: [{
          properties: {},
          children: children
        }]
      })

      const blob = await Packer.toBlob(doc)
      saveAs(blob, `${title}.docx`)
      showMessage('success', '导出成功')
    } catch (e) {
      showMessage('error', '导出失败: ' + e.message)
    }
  }

  return (
    <div className="p-6 min-w-full w-fit min-h-full bg-gray-50 inline-block">
      <div className="">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <FileText className="w-7 h-7" />
            报告列表
          </h1>
          <p className="text-gray-500 mt-1">查看与管理已创建的报告</p>
        </div>
        <div className="flex items-center gap-2">
          {selectedCount > 0 && (
            <div className="hidden md:flex items-center text-sm text-gray-500 mr-2">
              已选择 <span className="mx-1 font-medium text-gray-900">{selectedCount}</span> 条
            </div>
           )}
           

          <button
            onClick={handleExport}
            disabled={loading || exporting}
            className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm disabled:opacity-50"
            title={selectedCount > 0 ? '导出选中' : '导出全部（按当前筛选/排序）'}
          >
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            导出
          </button>
          <button
            onClick={handleBulkDelete}
            disabled={selectedCount === 0 || bulkDeleting}
            className="flex items-center gap-2 px-3 py-2 border border-red-200 text-red-700 rounded-lg hover:bg-red-50 text-sm disabled:opacity-50"
          >
            {bulkDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            批量删除
          </button>
          <button
            onClick={() => navigate('/reports/new')}
            className="flex items-center gap-2 px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
          >
            <Plus className="w-4 h-4" />
            新建报告
          </button>
          <button
            onClick={() => loadReports()}
            disabled={loading}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50"
            title="刷新"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 max-w-[560px] overflow-hidden">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              placeholder="搜索标题/内容关键词"
              className="w-full h-10 pl-9 pr-10 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            {keywordInput && (
              <button
                onClick={() => setKeywordInput('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 rounded p-1"
                aria-label="清除搜索"
              >
                ×
              </button>
            )}
          </div>
          <div className="text-sm text-gray-500 whitespace-nowrap mt-2">
            共 {total} 条
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
          </div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">暂无报告</p>
            <p className="text-sm text-gray-400 mt-1">点击右上角“新建报告”开始创建</p>
          </div>
        ) : (
          <>
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-10">
                    <input
                      type="checkbox"
                      checked={allSelectedOnPage}
                      onChange={toggleSelectAllPage}
                      className="h-4 w-4 rounded border-gray-300"
                      aria-label="select all"
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-64 md:w-80 min-w-[18rem]">
                    <button
                      type="button"
                      onClick={() => toggleSort('title')}
                      className="inline-flex items-center gap-1 hover:text-gray-700"
                    >
                      标题
                      {sortBy === 'title' ? (
                        <span className="text-gray-700">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-gray-400" />
                      )}
                    </button>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-72 min-w-[16rem]">内容预览</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-48 min-w-[12rem]">
                    <button
                      type="button"
                      onClick={() => toggleSort('user_id')}
                      className="inline-flex items-center gap-1 hover:text-gray-700"
                    >
                      创建人
                      {sortBy === 'user_id' ? (
                        <span className="text-gray-700">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-gray-400" />
                      )}
                    </button>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    <button
                      type="button"
                      onClick={() => toggleSort('created_at')}
                      className="inline-flex items-center gap-1 hover:text-gray-700"
                    >
                      创建时间
                      {sortBy === 'created_at' ? (
                        <span className="text-gray-700">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-gray-400" />
                      )}
                    </button>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    <button
                      type="button"
                      onClick={() => toggleSort('updated_at')}
                      className="inline-flex items-center gap-1 hover:text-gray-700"
                    >
                      更新时间
                      {sortBy === 'updated_at' ? (
                        <span className="text-gray-700">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-gray-400" />
                      )}
                    </button>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {items.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(r.id)}
                        onChange={() => toggleSelect(r.id)}
                        className="h-4 w-4 rounded border-gray-300"
                        aria-label={`select ${r.id}`}
                      />
                    </td>
                    <td className="px-6 py-4 w-64 md:w-80 min-w-[18rem]">
                      <div>
                        <button
                          type="button"
                          onClick={() => navigate(`/reports/${r.id}`)}
                          className="block truncate max-w-[18rem] text-sm font-medium text-gray-900 hover:text-primary-700"
                        >
                          {r.title}
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      <div
                        className="max-w-[360px] truncate"
                        title={stripHtml(r.content || '').replace(/\s+/g, ' ').trim()}
                      >
                        {r.content ? stripHtml(r.content).replace(/\s+/g, ' ').trim() : '—'}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700 font-mono w-48 min-w-[12rem]">
                      {r.user?.display_name || r.user?.username || '—'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      {formatDateTime(r.created_at)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      {formatDateTime(r.updated_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleExportWord(r.id)}
                          className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg"
                          title="导出Word"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => navigate(`/reports/${r.id}`)}
                          className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
                          title="查看"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => navigate(`/reports/${r.id}/edit`)}
                          className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg"
                          title="编辑"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(r)}
                          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
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

            <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-4 py-3 sm:px-6 mt-0 rounded-b-xl">
        <div className="flex flex-1 justify-between sm:hidden">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            上一页
          </button>
          <button
            onClick={() => setPage(Math.min(pageCount, page + 1))}
            disabled={page === pageCount}
            className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            下一页
          </button>
        </div>
        <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-gray-700">
              显示第 <span className="font-medium">{(page - 1) * pageSize + 1}</span> 到 <span className="font-medium">{Math.min(page * pageSize, total)}</span> 条，
              共 <span className="font-medium">{total}</span> 条
            </p>
          </div>
          <div>
            <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
              >
                <span className="sr-only">Previous</span>
                <ChevronLeft className="h-5 w-5" aria-hidden="true" />
              </button>
              {[...Array(pageCount)].map((_, i) => {
                const p = i + 1
                if (p === 1 || p === pageCount || (p >= page - 1 && p <= page + 1)) {
                  return (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      aria-current={page === p ? 'page' : undefined}
                      className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ${
                        page === p
                          ? 'z-10 bg-blue-600 text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
                          : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                      }`}
                    >
                      {p}
                    </button>
                  )
                } else if (p === page - 2 || p === page + 2) {
                  return (
                    <span key={p} className="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-700 ring-1 ring-inset ring-gray-300 focus:outline-offset-0">
                      ...
                    </span>
                  )
                }
                return null
              })}
              <button
                onClick={() => setPage(Math.min(pageCount, page + 1))}
                disabled={page === pageCount}
                className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
              >
                <span className="sr-only">Next</span>
                <ChevronRight className="h-5 w-5" aria-hidden="true" />
              </button>
            </nav>
          </div>
        </div>
      </div>

          </>
        )}
      </div>

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
      
      {deleteConfirm.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full shadow-xl transform transition-all">
            <h3 className="text-lg font-bold text-gray-900 mb-2">确认删除</h3>
            <p className="text-gray-600 mb-6 leading-relaxed">
              {deleteConfirm.type === 'bulk' 
                ? `确定要删除选中的 ${selectedCount} 条报告吗？` 
                : `确定要删除报告「${deleteConfirm.data?.title}」吗？`
              }
              <br/>
              <span className="text-sm text-red-500">此操作无法撤销。</span>
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(prev => ({ ...prev, open: false }))}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded-lg shadow-sm transition-colors"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  )
}
