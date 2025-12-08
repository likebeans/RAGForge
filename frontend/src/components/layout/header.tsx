"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Database, Settings, LogOut, Check, X, Menu } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { ThemeToggle } from "@/components/theme-toggle";

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const router = useRouter();
  const { isConnected, apiKey, apiBase, disconnect } = useAppStore();

  return (
    <header className="h-14 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-full items-center justify-between px-4">
        <div className="flex items-center gap-3">
          {onMenuClick && (
            <Button variant="ghost" size="icon" className="md:hidden" onClick={onMenuClick}>
              <Menu className="h-5 w-5" />
            </Button>
          )}
          <div className="flex items-center gap-2">
            <Database className="h-6 w-6 text-primary" />
            <h1 className="text-lg font-semibold">RAG Console</h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          
          <Badge variant={isConnected ? "default" : "secondary"} className="gap-1 hidden sm:flex">
            {isConnected ? (
              <>
                <Check className="h-3 w-3" />
                已连接
              </>
            ) : (
              <>
                <X className="h-3 w-3" />
                未连接
              </>
            )}
          </Badge>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <Settings className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="px-2 py-1.5 text-sm text-muted-foreground">
                API: {apiBase || "未配置"}
              </div>
              <div className="px-2 py-1.5 text-sm text-muted-foreground truncate">
                Key: {apiKey ? `${apiKey.slice(0, 12)}...` : "未配置"}
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push("/settings")}>
                <Settings className="mr-2 h-4 w-4" />
                设置
              </DropdownMenuItem>
              <DropdownMenuItem 
                className="text-destructive" 
                onClick={() => {
                  disconnect();
                  router.push("/settings");
                }}
              >
                <LogOut className="mr-2 h-4 w-4" />
                断开连接
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
