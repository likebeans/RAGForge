"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  Sparkles,
  FlaskConical,
  Beaker,
  TestTube,
  Atom,
  Microscope,
  Zap,
  Cpu,
  MoreHorizontal,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

// 预设封面图标选项
const COVER_ICONS = [
  { id: "sparkles", icon: Sparkles, color: "bg-purple-500" },
  { id: "flask", icon: FlaskConical, color: "bg-blue-500" },
  { id: "beaker", icon: Beaker, color: "bg-green-500" },
  { id: "testtube", icon: TestTube, color: "bg-pink-500" },
  { id: "atom", icon: Atom, color: "bg-indigo-500" },
  { id: "microscope", icon: Microscope, color: "bg-teal-500" },
  { id: "zap", icon: Zap, color: "bg-yellow-500" },
  { id: "cpu", icon: Cpu, color: "bg-orange-500" },
];

// Playground 接口
interface Playground {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  coverId: string;
}

// 从 localStorage 获取所有 Playground
const getPlaygrounds = (): Playground[] => {
  if (typeof window === "undefined") return [];
  return JSON.parse(localStorage.getItem("playgrounds") || "[]");
};

// 保存 Playground 列表到 localStorage
const savePlaygrounds = (playgrounds: Playground[]) => {
  localStorage.setItem("playgrounds", JSON.stringify(playgrounds));
};

// 创建 Playground
const createPlayground = (name: string): Playground => {
  const randomCover = COVER_ICONS[Math.floor(Math.random() * COVER_ICONS.length)];
  return {
    id: `playground-${Date.now()}`,
    name,
    createdAt: new Date().toISOString(),
    coverId: randomCover.id,
  };
};

// 删除 Playground
const deletePlayground = (id: string) => {
  const playgrounds = getPlaygrounds().filter(p => p.id !== id);
  savePlaygrounds(playgrounds);
};

export default function PlaygroundListPage() {
  const router = useRouter();
  
  // 状态
  const [playgrounds, setPlaygrounds] = useState<Playground[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // 创建对话框
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [selectedCover, setSelectedCover] = useState("sparkles");
  const [isCreating, setIsCreating] = useState(false);
  
  // 删除确认对话框
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Playground | null>(null);

  // 加载 Playground 列表
  const loadPlaygrounds = () => {
    setIsLoading(true);
    const list = getPlaygrounds();
    setPlaygrounds(list);
    setIsLoading(false);
  };

  useEffect(() => {
    loadPlaygrounds();
  }, []);

  // 创建新 Playground
  const handleCreate = () => {
    if (!newName.trim()) {
      toast.error("请输入名称");
      return;
    }

    setIsCreating(true);
    
    const newPlayground: Playground = {
      id: `playground-${Date.now()}`,
      name: newName.trim(),
      createdAt: new Date().toISOString(),
      coverId: selectedCover,
    };
    
    const list = getPlaygrounds();
    list.push(newPlayground);
    savePlaygrounds(list);
    
    setPlaygrounds(list);
    setCreateDialogOpen(false);
    setNewName("");
    setSelectedCover("sparkles");
    setIsCreating(false);
    
    toast.success("创建成功");
    
    // 跳转到详情页
    router.push(`/compare/${newPlayground.id}`);
  };

  // 确认删除
  const handleDelete = () => {
    if (!deleteTarget) return;
    
    deletePlayground(deleteTarget.id);
    setPlaygrounds(playgrounds.filter(p => p.id !== deleteTarget.id));
    setDeleteDialogOpen(false);
    setDeleteTarget(null);
    toast.success("删除成功");
  };

  // 获取图标组件
  const getCoverIcon = (coverId: string) => {
    const cover = COVER_ICONS.find(c => c.id === coverId) || COVER_ICONS[0];
    return cover;
  };

  return (
    <div className="flex-1 p-6">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Playground</h1>
          <p className="text-muted-foreground mt-1">
            创建和管理 RAG Pipeline 对比实验
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={loadPlaygrounds}
            disabled={isLoading}
          >
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          </Button>
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            新建 Playground
          </Button>
        </div>
      </div>

      {/* Playground 卡片列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : playgrounds.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
          <FlaskConical className="h-16 w-16 mb-4 opacity-20" />
          <p className="text-lg font-medium">暂无 Playground</p>
          <p className="text-sm mt-1">点击上方按钮创建第一个实验</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {playgrounds.map((pg) => {
            const cover = getCoverIcon(pg.coverId);
            const IconComponent = cover.icon;
            
            return (
              <div
                key={pg.id}
                className="group relative rounded-lg border bg-card hover:shadow-md transition-all cursor-pointer"
                onClick={() => router.push(`/compare/${pg.id}`)}
              >
                {/* 封面图标 */}
                <div className={cn("h-32 rounded-t-lg flex items-center justify-center", cover.color)}>
                  <IconComponent className="h-16 w-16 text-white" />
                </div>
                
                {/* 信息区 */}
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold truncate">{pg.name}</h3>
                      <p className="text-xs text-muted-foreground mt-1">
                        {pg.description || "暂无描述"}
                      </p>
                    </div>
                    
                    {/* 操作菜单 */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteTarget(pg);
                            setDeleteDialogOpen(true);
                          }}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          删除
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  
                  <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
                    <span>
                      创建于 {new Date(pg.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 创建对话框 */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建 Playground</DialogTitle>
            <DialogDescription>
              创建一个新的 RAG Pipeline 对比实验
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">名称</label>
              <Input
                placeholder="输入 Playground 名称"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">选择图标</label>
              <div className="grid grid-cols-4 gap-2">
                {COVER_ICONS.map((cover) => {
                  const IconComponent = cover.icon;
                  return (
                    <button
                      key={cover.id}
                      type="button"
                      onClick={() => setSelectedCover(cover.id)}
                      className={cn(
                        "h-16 rounded-lg flex items-center justify-center transition-all",
                        cover.color,
                        selectedCover === cover.id
                          ? "ring-2 ring-offset-2 ring-primary"
                          : "opacity-60 hover:opacity-100"
                      )}
                    >
                      <IconComponent className="h-8 w-8 text-white" />
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreate} disabled={isCreating}>
              {isCreating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除 "{deleteTarget?.name}" 吗？此操作无法撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
