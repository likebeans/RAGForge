"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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
  Database, 
  Plus, 
  Trash2, 
  RefreshCw, 
  Loader2, 
  FileText,
  Image as ImageIcon,
  BookOpen,
  Sparkles,
  Brain,
  Lightbulb,
  GraduationCap,
  FolderOpen,
  Archive,
  Settings,
  MoreHorizontal,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { ProviderModelSelector } from "@/components/settings";

// 预设封面图片选项
const COVER_ICONS = [
  { id: "database", icon: Database, color: "bg-blue-500" },
  { id: "book", icon: BookOpen, color: "bg-green-500" },
  { id: "sparkles", icon: Sparkles, color: "bg-purple-500" },
  { id: "brain", icon: Brain, color: "bg-pink-500" },
  { id: "lightbulb", icon: Lightbulb, color: "bg-yellow-500" },
  { id: "graduation", icon: GraduationCap, color: "bg-indigo-500" },
  { id: "folder", icon: FolderOpen, color: "bg-orange-500" },
  { id: "archive", icon: Archive, color: "bg-teal-500" },
];

// 从 localStorage 获取知识库封面（预设图标 ID）
const getKbCover = (kbId: string): string => {
  if (typeof window === "undefined") return "database";
  const covers = JSON.parse(localStorage.getItem("kb_covers") || "{}");
  return covers[kbId] || "database";
};

// 从 localStorage 获取自定义图标 URL
const getKbCustomIcon = (kbId: string): string | null => {
  if (typeof window === "undefined") return null;
  const customIcons = JSON.parse(localStorage.getItem("kb_custom_icons") || "{}");
  return customIcons[kbId] || null;
};

// 保存知识库封面到 localStorage
const setKbCover = (kbId: string, coverId: string) => {
  const covers = JSON.parse(localStorage.getItem("kb_covers") || "{}");
  covers[kbId] = coverId;
  localStorage.setItem("kb_covers", JSON.stringify(covers));
};

export default function KnowledgeBasesPage() {
  const router = useRouter();
  const {
    client,
    isConnected,
    knowledgeBases,
    refreshKnowledgeBases,
    defaultModels,
    setDefaultModel,
    providerCatalog,
    setProviderCatalog,
  } = useAppStore();
  
  // 创建对话框状态
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newKbName, setNewKbName] = useState("");
  const [newKbDesc, setNewKbDesc] = useState("");
  const [selectedCover, setSelectedCover] = useState("database");
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [llmProvider, setLlmProvider] = useState(defaultModels.llm?.provider || "");
  const [llmModel, setLlmModel] = useState(defaultModels.llm?.model || "");
  const [embedProvider, setEmbedProvider] = useState(defaultModels.embedding?.provider || "");
  const [embedModel, setEmbedModel] = useState(defaultModels.embedding?.model || "");
  
  // 删除确认对话框
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  
  // 封面映射状态（预设图标 ID）
  const [coverMap, setCoverMap] = useState<Record<string, string>>({});
  // 自定义图标映射状态
  const [customIconMap, setCustomIconMap] = useState<Record<string, string>>({});

  useEffect(() => {
    if (client && isConnected) {
      loadKnowledgeBases();
    }
  }, [client, isConnected]);

  useEffect(() => {
    if (client && isConnected && Object.keys(providerCatalog).length === 0) {
      client.listProviders().then(setProviderCatalog).catch(() => undefined);
    }
  }, [client, isConnected, providerCatalog, setProviderCatalog]);

  useEffect(() => {
    setLlmProvider(defaultModels.llm?.provider || "");
    setLlmModel(defaultModels.llm?.model || "");
    setEmbedProvider(defaultModels.embedding?.provider || "");
    setEmbedModel(defaultModels.embedding?.model || "");
  }, [defaultModels]);

  // 加载封面映射（预设图标和自定义图标）
  useEffect(() => {
    const covers: Record<string, string> = {};
    const customIcons: Record<string, string> = {};
    knowledgeBases.forEach((kb) => {
      covers[kb.id] = getKbCover(kb.id);
      const customIcon = getKbCustomIcon(kb.id);
      if (customIcon) {
        customIcons[kb.id] = customIcon;
      }
    });
    setCoverMap(covers);
    setCustomIconMap(customIcons);
  }, [knowledgeBases]);

  const loadKnowledgeBases = async () => {
    setIsLoading(true);
    await refreshKnowledgeBases();
    setIsLoading(false);
  };

  const handleCreateClick = () => {
    setNewKbName("");
    setNewKbDesc("");
    setSelectedCover("database");
    setCreateDialogOpen(true);
  };

  const createKnowledgeBase = async () => {
    if (!newKbName.trim()) {
      toast.error("请输入知识库名称");
      return;
    }
    if (!client) {
      toast.error("请先配置 API Key");
      return;
    }
    
    setIsCreating(true);
    try {
      const result = await client.createKnowledgeBase(newKbName, newKbDesc || undefined);
      // 保存封面选择
      if (result?.id) {
        setKbCover(result.id, selectedCover);
      }
      toast.success("知识库创建成功");
      setCreateDialogOpen(false);
      await refreshKnowledgeBases();
      // 跳转到知识库详情页
      if (result?.id) {
        router.push(`/knowledge-bases/${result.id}`);
      }
    } catch (error) {
      toast.error(`创建失败: ${(error as Error).message}`);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteClick = (e: React.MouseEvent, id: string, name: string) => {
    e.stopPropagation();
    setDeleteTarget({ id, name });
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!client || !deleteTarget) return;
    
    try {
      await client.deleteKnowledgeBase(deleteTarget.id);
      toast.success("知识库已删除");
      refreshKnowledgeBases();
    } catch (error) {
      toast.error(`删除失败: ${(error as Error).message}`);
    } finally {
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    }
  };

  const getCoverIcon = (coverId: string) => {
    return COVER_ICONS.find((c) => c.id === coverId) || COVER_ICONS[0];
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "-";
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const handleProviderChange = (type: "llm" | "embedding", provider: string) => {
    if (type === "llm") {
      setLlmProvider(provider);
      setLlmModel("");
    } else {
      setEmbedProvider(provider);
      setEmbedModel("");
    }
    setDefaultModel(type, provider ? { provider, model: "" } : null);
  };

  const handleModelChange = (type: "llm" | "embedding", model: string) => {
    if (type === "llm") {
      setLlmModel(model);
      if (llmProvider) setDefaultModel("llm", { provider: llmProvider, model });
    } else {
      setEmbedModel(model);
      if (embedProvider) setDefaultModel("embedding", { provider: embedProvider, model });
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* 页头 */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">知识库</h1>
          <p className="text-muted-foreground mt-1">管理你的知识库，上传文档构建智能问答</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadKnowledgeBases} disabled={isLoading}>
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          </Button>
          <Button onClick={handleCreateClick} disabled={!isConnected}>
            <Plus className="h-4 w-4 mr-2" />
            新建知识库
          </Button>
        </div>
      </div>

      {isConnected && (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">模型选择</CardTitle>
            <CardDescription>为知识库相关操作选择默认的 LLM 与 Embedding 模型（已在设置中验证的提供商）</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <ProviderModelSelector
              type="llm"
              providerValue={llmProvider}
              modelValue={llmModel}
              onProviderChange={(v) => handleProviderChange("llm", v)}
              onModelChange={(v) => handleModelChange("llm", v)}
            />
            <ProviderModelSelector
              type="embedding"
              providerValue={embedProvider}
              modelValue={embedModel}
              onProviderChange={(v) => handleProviderChange("embedding", v)}
              onModelChange={(v) => handleModelChange("embedding", v)}
            />
          </CardContent>
        </Card>
      )}

      {/* 知识库卡片网格 */}
      {!isConnected ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Database className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-medium mb-2">未连接到服务</h3>
          <p className="text-muted-foreground mb-4">请先在设置页面配置 API Key</p>
          <Button variant="outline" onClick={() => router.push("/settings")}>
            <Settings className="h-4 w-4 mr-2" />
            前往设置
          </Button>
        </div>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {/* 知识库卡片列表 */}
          {knowledgeBases.map((kb) => {
            const cover = getCoverIcon(coverMap[kb.id] || "database");
            const IconComponent = cover.icon;
            const customIcon = customIconMap[kb.id];
            
            return (
              <div
                key={kb.id}
                className="group relative flex flex-col h-[200px] rounded-xl border bg-card hover:shadow-lg hover:border-primary/30 transition-all cursor-pointer overflow-hidden"
                onClick={() => router.push(`/knowledge-bases/${kb.id}`)}
              >
                {/* 封面区域 */}
                <div className={cn("relative h-[100px] flex items-center justify-center", customIcon ? "bg-muted" : cover.color)}>
                  {customIcon ? (
                    <img src={customIcon} alt="知识库图标" className="max-w-full max-h-full object-contain" />
                  ) : (
                    <IconComponent className="h-10 w-10 text-white/90" />
                  )}
                  {/* 操作菜单 */}
                  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button size="icon" variant="secondary" className="h-7 w-7 bg-white/90 hover:bg-white">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(e) => handleDeleteClick(e, kb.id, kb.name)} className="text-destructive focus:text-destructive">
                          <Trash2 className="h-4 w-4 mr-2" />
                          删除
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
                
                {/* 信息区域 */}
                <div className="flex-1 p-4 flex flex-col">
                  <h3 className="font-medium text-base truncate" title={kb.name}>
                    {kb.name}
                  </h3>
                  {kb.description ? (
                    <p className="text-xs text-muted-foreground line-clamp-2 mt-1 flex-1">
                      {kb.description}
                    </p>
                  ) : (
                    <p className="text-xs text-muted-foreground/50 italic mt-1 flex-1">
                      暂无描述
                    </p>
                  )}
                  <div className="flex items-center justify-between mt-2 pt-2 border-t">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <FileText className="h-3 w-3" />
                      <span>{kb.document_count || 0} 文档</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(kb.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 空状态 */}
      {isConnected && !isLoading && knowledgeBases.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-center mt-8">
          <BookOpen className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-medium mb-2">还没有知识库</h3>
          <p className="text-muted-foreground mb-4 max-w-md">
            创建你的第一个知识库，上传文档后即可开始智能问答
          </p>
        </div>
      )}

      {/* 创建知识库对话框 */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>新建知识库</DialogTitle>
            <DialogDescription>
              创建一个新的知识库，用于存储和检索你的文档
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-5 py-4">
            {/* 封面选择 */}
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <ImageIcon className="h-4 w-4" />
                选择封面
              </label>
              <div className="flex flex-wrap gap-2">
                {COVER_ICONS.map((cover) => {
                  const IconComponent = cover.icon;
                  return (
                    <button
                      key={cover.id}
                      type="button"
                      onClick={() => setSelectedCover(cover.id)}
                      className={cn(
                        "w-12 h-12 rounded-lg flex items-center justify-center transition-all",
                        cover.color,
                        selectedCover === cover.id
                          ? "ring-2 ring-offset-2 ring-primary"
                          : "opacity-70 hover:opacity-100"
                      )}
                    >
                      <IconComponent className="h-6 w-6 text-white" />
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 名称输入 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                知识库名称 <span className="text-destructive">*</span>
              </label>
              <Input
                value={newKbName}
                onChange={(e) => setNewKbName(e.target.value)}
                placeholder="例如：产品文档、技术手册"
                maxLength={50}
              />
            </div>

            {/* 描述输入 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">描述</label>
              <Textarea
                value={newKbDesc}
                onChange={(e) => setNewKbDesc(e.target.value)}
                placeholder="简要描述知识库的用途和内容..."
                rows={3}
                maxLength={200}
              />
              <p className="text-xs text-muted-foreground text-right">
                {newKbDesc.length}/200
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={createKnowledgeBase} disabled={isCreating || !newKbName.trim()}>
              {isCreating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  创建中...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  创建并进入
                </>
              )}
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
              确定要删除知识库 <span className="font-medium text-foreground">"{deleteTarget?.name}"</span> 吗？
              此操作不可恢复，知识库中的所有文档也将被删除。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive hover:bg-destructive/90">
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
