"use client";

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Header } from "./header";
import { Sidebar } from "./sidebar";
import { ErrorBoundary } from "@/components/error-boundary";
import { useAppStore } from "@/lib/store";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const autoConnect = useAppStore((state) => state.autoConnect);
  const pathname = usePathname();

  // 在知识库详情页和 Playground 详情页隐藏全局侧边栏
  const isKnowledgeBaseDetailPage = pathname?.match(/^\/knowledge-bases\/[^/]+$/);
  const isPlaygroundDetailPage = pathname?.match(/^\/compare\/[^/]+$/);
  const hideSidebar = !!isKnowledgeBaseDetailPage || !!isPlaygroundDetailPage;

  // 页面加载时自动重连（如果有保存的 API Key）
  useEffect(() => {
    autoConnect();
  }, [autoConnect]);

  return (
    <div className="flex h-screen flex-col">
      <Header onMenuClick={() => setMobileMenuOpen(!mobileMenuOpen)} />
      
      <div className="flex flex-1 overflow-hidden">
        {/* 桌面端侧边栏 - 在知识库详情页隐藏 */}
        {!hideSidebar && (
          <div className="hidden md:flex h-full">
            <Sidebar
              collapsed={sidebarCollapsed}
              onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
            />
          </div>
        )}

        {/* 移动端侧边栏 */}
        {mobileMenuOpen && !hideSidebar && (
          <>
            <div
              className="fixed inset-0 z-40 bg-black/50 md:hidden"
              onClick={() => setMobileMenuOpen(false)}
            />
            <div className="fixed inset-y-0 left-0 z-50 w-64 md:hidden">
              <Sidebar onToggle={() => setMobileMenuOpen(false)} />
            </div>
          </>
        )}

        {/* 主内容区 */}
        <main className="flex-1 overflow-auto bg-background">
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
