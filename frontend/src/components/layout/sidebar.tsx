"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAppStore } from "@/lib/store";
import {
  MessageSquare,
  Database,
  Settings,
  Plus,
  ChevronLeft,
  ChevronRight,
  GitCompare,
  Trash2,
  Search,
} from "lucide-react";

interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

const navItems = [
  {
    title: "对话",
    href: "/chat",
    icon: MessageSquare,
  },
  {
    title: "知识库",
    href: "/knowledge-bases",
    icon: Database,
  },
  {
    title: "Playground",
    href: "/compare",
    icon: GitCompare,
  },
  {
    title: "检索对比",
    href: "/retrieval-compare",
    icon: Search,
  },
  {
    title: "设置",
    href: "/settings",
    icon: Settings,
  },
];

export function Sidebar({ collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const {
    conversations,
    currentConversationId,
    setCurrentConversationId,
    refreshConversations,
    deleteConversation,
    isConnected,
  } = useAppStore();

  // 加载对话列表
  useEffect(() => {
    if (isConnected) {
      refreshConversations();
    }
  }, [isConnected, refreshConversations]);

  const handleNewChat = () => {
    // 清除当前对话 ID
    setCurrentConversationId(null);
    // 如果已经在 /chat 页面，使用 replace 强制刷新；否则正常导航
    if (pathname === "/chat") {
      // 强制重新加载组件状态
      window.location.href = "/chat";
    } else {
      router.push("/chat");
    }
  };

  const handleSelectConversation = (id: string) => {
    router.push(`/chat/${id}`);
  };

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm("确定删除此对话？")) {
      await deleteConversation(id);
    }
  };

  return (
    <aside
      className={cn(
        "flex flex-col border-r bg-background transition-all duration-300 h-full",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* 顶部新建按钮和导航 */}
      <div className="p-3 space-y-2">
        <Button
          variant="default"
          className={cn(
            "w-full justify-start gap-2 shadow-sm",
            collapsed && "justify-center px-2"
          )}
          onClick={handleNewChat}
        >
          <Plus className="h-4 w-4" />
          {!collapsed && <span>新建对话</span>}
        </Button>

        <nav className="flex flex-col gap-1 pt-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
            return (
              <Button
                key={item.href}
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start gap-3 text-sm font-normal h-9",
                  collapsed && "justify-center px-2",
                  isActive && "bg-accent text-accent-foreground"
                )}
                asChild
              >
                <Link href={item.href}>
                  <item.icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                  {!collapsed && <span>{item.title}</span>}
                </Link>
              </Button>
            );
          })}
        </nav>
      </div>

      {/* 对话历史列表 */}
      {!collapsed && conversations.length > 0 && (
        <div className="flex-1 overflow-hidden flex flex-col mt-2">
          <div className="px-4 py-2 text-xs font-medium text-muted-foreground/70 uppercase tracking-wider">
            历史对话
          </div>
          <ScrollArea className="flex-1 px-2">
            <div className="space-y-0.5 pb-2">
              {conversations.slice(0, 50).map((conv) => (
                <div
                  key={conv.id}
                  className={cn(
                    "group flex items-center gap-2 rounded-md px-2 py-2 text-sm cursor-pointer hover:bg-accent/50 transition-colors",
                    currentConversationId === conv.id && "bg-accent text-accent-foreground"
                  )}
                  onClick={() => handleSelectConversation(conv.id)}
                >
                  <span className="flex-1 truncate text-foreground/80 group-hover:text-foreground">
                    {conv.title || "新对话"}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-background hover:text-destructive"
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      {/* 底部折叠按钮 */}
      <div className="p-3 mt-auto border-t">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-center text-muted-foreground hover:text-foreground"
          onClick={onToggle}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <div className="flex items-center gap-2">
              <ChevronLeft className="h-4 w-4" />
              <span className="text-xs">收起侧边栏</span>
            </div>
          )}
        </Button>
      </div>
    </aside>
  );
}
