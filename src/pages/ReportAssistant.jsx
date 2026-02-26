import React, { useEffect, useState } from 'react'
import { backendClient } from '../services/backend'

export default function ReportAssistant() {
  const [height, setHeight] = useState(typeof window !== 'undefined' ? window.innerHeight - 64 : 600)
  const [saving, setSaving] = useState(false)
  const [tip, setTip] = useState(null)

  useEffect(() => {
    const onResize = () => setHeight(window.innerHeight - 64)
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    const handler = async (event) => {
      try {
        if (!event || !event.data || event.origin.indexOf('://localhost:3010') === -1) return
        const { type, payload } = event.data || {}
        if (type !== 'YA0YAN_REPORT_GENERATED' || !payload) return
        const title = payload.title || '自动生成的报告'
        const content = payload.content || ''
        setSaving(true)
        await backendClient.createReport({ title, content, status: 'published' })
        setTip('已保存到报告列表')
        setTimeout(() => setTip(null), 3000)
      } catch (e) {
        setTip('保存失败：' + e.message)
        setTimeout(() => setTip(null), 4000)
      } finally {
        setSaving(false)
      }
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [])

  return (
    <div className="w-full overflow-hidden" style={{ height }}>
      {tip && (
        <div className="absolute right-6 top-20 z-10 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow">
          {saving ? '正在保存...' : tip}
        </div>
      )}
      <iframe
        src="http://localhost:3010/chat?sidebar=1"
        className="w-full h-full border-0"
        title="DeerFlow Deep Research Assistant"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
      />
    </div>
  )
}
