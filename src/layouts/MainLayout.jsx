import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import Header from '../components/Header'
import { useEffect } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import 'react-quill/dist/quill.snow.css'

export default function MainLayout() {
  const location = useLocation()
  const noPaddingRoutes = ['/reports/assistant']
  const mainPaddingClass = noPaddingRoutes.includes(location.pathname) ? 'p-0' : 'p-6'
  const isReportDetail =
    location.pathname.startsWith('/reports/') &&
    !location.pathname.endsWith('/edit') &&
    location.pathname !== '/reports/new'
  const routeClass = isReportDetail ? 'route-report-detail' : ''

  useEffect(() => {
    if (!isReportDetail) return
    
    // Inject rendering logic for read-only preview
    const renderMarkdown = () => {
      const nodes = document.querySelectorAll('.whitespace-pre-wrap.text-sm.text-gray-900.leading-6')
      nodes.forEach((el) => {
        if (el.getAttribute('data-md-rendered') === '1') return
        
        const text = el.textContent || ''
        // Render Markdown to HTML
        const html = DOMPurify.sanitize(marked.parse(text))
        
        // Wrap in Quill classes for visual consistency with editor
        el.innerHTML = `<div class="ql-snow"><div class="ql-editor p-0">${html}</div></div>`
        
        el.classList.remove('whitespace-pre-wrap') // Remove pre-wrap to let HTML flow
        el.setAttribute('data-md-rendered', '1')
      })
    }

    // Run initially and observe changes (in case of data loading)
    renderMarkdown()
    const observer = new MutationObserver(renderMarkdown)
    observer.observe(document.body, { childList: true, subtree: true })
    
    return () => observer.disconnect()
  }, [location.pathname, isReportDetail])

  return (
    <div className="h-screen overflow-hidden bg-gray-50 flex">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col ml-64 h-full">
        <Header />
        <main className={`flex-1 min-w-0 overflow-auto bg-gray-50 ${mainPaddingClass} ${routeClass}`}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
