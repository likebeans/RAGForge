"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ChevronLeft,
  Upload,
  FileText,
  Trash2,
  RefreshCw,
  Loader2,
  File,
  Plus,
  Database,
  BookOpen,
  Sparkles,
  Brain,
  Lightbulb,
  ScrollText,
  Settings,
  GraduationCap,
  FolderOpen,
  Archive,
  Search,
  MoreHorizontal,
  Calendar,
  Layers,
  Eye,
  Save,
  Image,
  Info,
  HelpCircle,
  CheckCircle2,
  XCircle,
  Circle,
} from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAppStore } from "@/lib/store";
import { Document } from "@/lib/api";
import { cn } from "@/lib/utils";
import { AllModelsSelector } from "@/components/settings";

// 与列表页面共享的封面图标
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

const getKbCover = (kbId: string): string => {
  if (typeof window === "undefined") return "database";
  const covers = JSON.parse(localStorage.getItem("kb_covers") || "{}");
  return covers[kbId] || "database";
};

// 左侧导航菜单项
const NAV_ITEMS = [
  { id: "files", label: "文件列表", icon: FileText },
  { id: "search", label: "检索测试", icon: Search },
  { id: "logs", label: "日志", icon: ScrollText },
  { id: "config", label: "配置", icon: Settings },
];

export default function KnowledgeBaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const kbId = params.id as string;
  
  const { client, isConnected, knowledgeBases, defaultModels } = useAppStore();
  
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [coverIconId, setCoverIconId] = useState("database");
  const [activeNav, setActiveNav] = useState("files");
  const [searchQuery, setSearchQuery] = useState("");
  
  // 上传文件对话框
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [parseOnCreate, setParseOnCreate] = useState(false);
  
  // 新增空文件对话框
  const [newFileDialogOpen, setNewFileDialogOpen] = useState(false);
  const [newFileName, setNewFileName] = useState("");
  
  // 删除确认
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);

  // 知识库配置状态
  const [configName, setConfigName] = useState("");
  const [configDescription, setConfigDescription] = useState("");
  const [configEmbeddingModel, setConfigEmbeddingModel] = useState<{ provider: string; model: string }>({ provider: "ollama", model: "bge-m3" });
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  // 自定义图标
  const [customIconUrl, setCustomIconUrl] = useState<string | null>(null);
  const [isUploadingIcon, setIsUploadingIcon] = useState(false);
  const iconInputRef = useState<HTMLInputElement | null>(null);

  // 文档日志对话框
  const [logDialogOpen, setLogDialogOpen] = useState(false);
  const [logTarget, setLogTarget] = useState<{ id: string; title: string } | null>(null);
  const [logContent, setLogContent] = useState<string>("");
  const [isLoadingLog, setIsLoadingLog] = useState(false);

  const kb = knowledgeBases.find((k) => k.id === kbId);
  
  // 初始化配置
  useEffect(() => {
    if (kb) {
      setConfigName(kb.name || "");
      setConfigDescription(kb.description || "");
      // 从 kb.config 中读取配置（如果有）
      const kbConfig = (kb as any).config || {};
      if (kbConfig.embedding_provider && kbConfig.embedding_model) {
        setConfigEmbeddingModel({
          provider: kbConfig.embedding_provider,
          model: kbConfig.embedding_model,
        });
      }
      // 从 localStorage 读取自定义图标
      const customIcons = JSON.parse(localStorage.getItem("kb_custom_icons") || "{}");
      if (customIcons[kbId]) {
        setCustomIconUrl(customIcons[kbId]);
      }
    }
  }, [kb, kbId]);
  
  // 获取封面
  useEffect(() => {
    setCoverIconId(getKbCover(kbId));
  }, [kbId]);
  
  const coverIcon = COVER_ICONS.find((c) => c.id === coverIconId) || COVER_ICONS[0];
  const CoverIconComponent = coverIcon.icon;
  
  // 过滤文档
  const filteredDocuments = documents.filter((doc) =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 加载文档列表
  // silent: 静默刷新（轮询时不显示 loading，避免界面闪烁）
  const loadDocuments = useCallback(async (silent = false) => {
    if (!client || !kbId) return;
    if (!silent) setIsLoading(true);
    try {
      const result = await client.listDocuments(kbId);
      const newDocs = result.items || [];
      // 只在数据有变化时更新状态，避免不必要的重渲染
      setDocuments(prev => {
        const hasChanged = JSON.stringify(prev.map(d => ({ id: d.id, chunk_count: d.chunk_count, processing_status: d.processing_status }))) 
          !== JSON.stringify(newDocs.map(d => ({ id: d.id, chunk_count: d.chunk_count, processing_status: d.processing_status })));
        return hasChanged ? newDocs : prev;
      });
    } catch (error) {
      if (!silent) toast.error(`加载文档失败: ${(error as Error).message}`);
    } finally {
      if (!silent) setIsLoading(false);
    }
  }, [client, kbId]);

  useEffect(() => {
    if (client && isConnected && kbId) {
      loadDocuments();
    }
  }, [client, isConnected, kbId, loadDocuments]);

  // 自动刷新：当有文档处理中时，每 3 秒静默轮询一次
  useEffect(() => {
    const hasProcessingDocs = documents.some((doc) => doc.processing_status === "pending" || doc.processing_status === "processing");
    if (!hasProcessingDocs || !client || !isConnected) return;

    const interval = setInterval(() => {
      loadDocuments(true); // 静默刷新，不显示 loading
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, client, isConnected, loadDocuments]);

  // 文件上传
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!client) return;
    
    setIsUploading(true);
    const newProgress: Record<string, number> = {};
    
    for (const file of acceptedFiles) {
      newProgress[file.name] = 0;
      setUploadProgress({ ...newProgress });
      
      try {
        await client.uploadFile(kbId, file);
        newProgress[file.name] = 100;
        setUploadProgress({ ...newProgress });
        toast.success(`${file.name} 上传成功`);
      } catch (error) {
        toast.error(`${file.name} 上传失败: ${(error as Error).message}`);
        delete newProgress[file.name];
      }
    }
    
    setIsUploading(false);
    setUploadProgress({});
    loadDocuments();
  }, [client, kbId, loadDocuments]);


  // 新增空文件
  const handleCreateEmptyFile = async () => {
    if (!client || !newFileName.trim()) return;
    
    setIsUploading(true);
    try {
      // 创建一个空内容的文档
      await client.uploadDocument(kbId, newFileName.trim(), " ");
      toast.success("文件创建成功");
      setNewFileDialogOpen(false);
      setNewFileName("");
      loadDocuments();
    } catch (error) {
      toast.error(`创建失败: ${(error as Error).message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // 打开上传文件对话框
  const openUploadDialog = () => {
    setPendingFiles([]);
    setParseOnCreate(false);
    setUploadDialogOpen(true);
  };

  // 处理对话框内的文件选择（拖拽或点击）
  const handleDialogFileDrop = useCallback((acceptedFiles: File[]) => {
    setPendingFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  // 移除待上传文件
  const removePendingFile = (index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // 确认上传
  const handleConfirmUpload = async () => {
    if (pendingFiles.length === 0) return;
    
    setUploadDialogOpen(false);
    // 使用现有的 onDrop 函数上传
    onDrop(pendingFiles);
    setPendingFiles([]);
  };

  // 对话框内的 dropzone
  const {
    getRootProps: getDialogRootProps,
    getInputProps: getDialogInputProps,
    isDragActive: isDialogDragActive,
  } = useDropzone({
    onDrop: handleDialogFileDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/markdown': ['.md'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    disabled: isUploading,
  });

  // 删除文档 - 打开确认对话框
  const handleDeleteClick = (docId: string, title: string) => {
    setDeleteTarget({ id: docId, title });
    setDeleteDialogOpen(true);
  };

  // 确认删除
  const confirmDelete = async () => {
    if (!client || !deleteTarget) return;
    
    try {
      await client.deleteDocument(deleteTarget.id);
      toast.success("文档已删除");
      loadDocuments();
    } catch (error) {
      toast.error(`删除失败: ${(error as Error).message}`);
    } finally {
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    }
  };

  // 格式化日期
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "-";
    return date.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // 处理图标上传
  const handleIconUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // 验证文件类型
    if (!file.type.startsWith("image/")) {
      toast.error("请上传图片文件");
      return;
    }
    
    // 验证文件大小（最大 2MB）
    if (file.size > 2 * 1024 * 1024) {
      toast.error("图片大小不能超过 2MB");
      return;
    }
    
    setIsUploadingIcon(true);
    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      setCustomIconUrl(dataUrl);
      // 保存到 localStorage
      const customIcons = JSON.parse(localStorage.getItem("kb_custom_icons") || "{}");
      customIcons[kbId] = dataUrl;
      localStorage.setItem("kb_custom_icons", JSON.stringify(customIcons));
      setIsUploadingIcon(false);
      toast.success("图标已更新");
    };
    reader.onerror = () => {
      setIsUploadingIcon(false);
      toast.error("图片读取失败");
    };
    reader.readAsDataURL(file);
  };

  // 选择预设图标
  const handleSelectPresetIcon = (iconId: string) => {
    setCoverIconId(iconId);
    setCustomIconUrl(null);
    // 保存到 localStorage
    const covers = JSON.parse(localStorage.getItem("kb_covers") || "{}");
    covers[kbId] = iconId;
    localStorage.setItem("kb_covers", JSON.stringify(covers));
    // 清除自定义图标
    const customIcons = JSON.parse(localStorage.getItem("kb_custom_icons") || "{}");
    delete customIcons[kbId];
    localStorage.setItem("kb_custom_icons", JSON.stringify(customIcons));
  };

  // 查看文档日志（支持轮询刷新）
  const fetchDocumentLog = useCallback(async (docId: string) => {
    if (!client) return;
    try {
      const docDetail = await client.getDocument(docId);
      
      // 优先显示处理日志（如果存在）
      if (docDetail.processing_log) {
        setLogContent(docDetail.processing_log);
      } else {
        // 如果没有处理日志，显示基本文档信息
        const logLines: string[] = [];
        logLines.push(`[INFO] 文档信息`);
        logLines.push(`[INFO] 文档名称: ${docDetail.title}`);
        logLines.push(`[INFO] 文档 ID: ${docDetail.id}`);
        logLines.push(`[INFO] 创建时间: ${formatDate(docDetail.created_at)}`);
        logLines.push(`[INFO] 分块数量: ${docDetail.chunk_count}`);
        if (docDetail.source) {
          logLines.push(`[INFO] 来源类型: ${docDetail.source}`);
        }
        logLines.push(``);
        logLines.push(`[INFO] 暂无详细处理日志`);
        logLines.push(`[INFO] 通过 Ground 页面入库的文档会记录详细处理日志`);
        setLogContent(logLines.join("\n"));
      }
      return docDetail;
    } catch (error) {
      setLogContent(`[ERROR] 加载日志失败: ${(error as Error).message}`);
      return null;
    }
  }, [client]);

  const handleViewLog = async (docId: string, title: string) => {
    if (!client) return;
    setLogTarget({ id: docId, title });
    setLogDialogOpen(true);
    setIsLoadingLog(true);
    setLogContent("");
    
    await fetchDocumentLog(docId);
    setIsLoadingLog(false);
  };

  // 日志对话框打开时自动轮询刷新（当文档处理中时）
  useEffect(() => {
    if (!logDialogOpen || !logTarget?.id || !client) return;
    
    // 检查当前文档是否正在处理中
    const doc = documents.find(d => d.id === logTarget.id);
    const isProcessing = doc && (doc.processing_status === "pending" || doc.processing_status === "processing");
    
    if (!isProcessing) return;
    
    // 每 2 秒刷新一次日志
    const interval = setInterval(() => {
      fetchDocumentLog(logTarget.id);
    }, 2000);
    
    return () => clearInterval(interval);
  }, [logDialogOpen, logTarget?.id, client, documents, fetchDocumentLog]);

  // 保存知识库配置
  const handleSaveConfig = async () => {
    if (!client) return;
    setIsSavingConfig(true);
    try {
      // 如果没有选择 Embedding 模型，使用前端默认设置
      const embeddingProvider = configEmbeddingModel.provider || defaultModels.embedding?.provider;
      const embeddingModel = configEmbeddingModel.model || defaultModels.embedding?.model;
      
      // 调用更新知识库 API
      await client.updateKnowledgeBase(kbId, {
        name: configName,
        description: configDescription,
        config: {
          embedding_provider: embeddingProvider,
          embedding_model: embeddingModel,
        },
      });
      toast.success("配置保存成功");
    } catch (error) {
      toast.error(`保存失败: ${(error as Error).message}`);
    } finally {
      setIsSavingConfig(false);
    }
  };

  // 配置面板内容
  const renderConfigPanel = () => (
    <TooltipProvider>
      <div className="flex-1 overflow-auto">
        <div className="max-w-3xl space-y-6 pb-8">
          {/* 知识库图标 */}
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-center gap-2">
                <Image className="h-5 w-5 text-primary" />
                <CardTitle className="text-lg">知识库图标</CardTitle>
              </div>
              <CardDescription>选择预设图标或上传自定义图片</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 当前图标预览 */}
              <div className="flex items-center gap-4">
                <div className={cn(
                  "w-16 h-16 rounded-lg flex items-center justify-center overflow-hidden",
                  customIconUrl ? "bg-muted" : coverIcon.color
                )}>
                  {customIconUrl ? (
                    <img src={customIconUrl} alt="自定义图标" className="max-w-full max-h-full object-contain" />
                  ) : (
                    <CoverIconComponent className="h-8 w-8 text-white" />
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">当前图标</p>
                  <p className="text-xs text-muted-foreground">
                    {customIconUrl ? "自定义图片" : `预设图标: ${coverIcon.id}`}
                  </p>
                </div>
              </div>

              {/* 预设图标选择 */}
              <div>
                <Label className="text-sm text-muted-foreground mb-2 block">预设图标</Label>
                <div className="flex flex-wrap gap-2">
                  {COVER_ICONS.map((icon) => {
                    const IconComp = icon.icon;
                    const isSelected = !customIconUrl && coverIconId === icon.id;
                    return (
                      <button
                        key={icon.id}
                        onClick={() => handleSelectPresetIcon(icon.id)}
                        className={cn(
                          "w-10 h-10 rounded-lg flex items-center justify-center transition-all",
                          icon.color,
                          isSelected ? "ring-2 ring-offset-2 ring-primary" : "hover:opacity-80"
                        )}
                      >
                        <IconComp className="h-5 w-5 text-white" />
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 上传自定义图标 */}
              <div>
                <Label className="text-sm text-muted-foreground mb-2 block">自定义图片</Label>
                <div className="flex items-center gap-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => document.getElementById("icon-upload")?.click()}
                    disabled={isUploadingIcon}
                  >
                    {isUploadingIcon ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Upload className="h-4 w-4 mr-2" />
                    )}
                    上传图片
                  </Button>
                  <span className="text-xs text-muted-foreground">支持 JPG、PNG、GIF，最大 2MB</span>
                  <input
                    id="icon-upload"
                    type="file"
                    accept="image/*"
                    onChange={handleIconUpload}
                    className="hidden"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 基础信息 */}
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-center gap-2">
                <Info className="h-5 w-5 text-primary" />
                <CardTitle className="text-lg">基础信息</CardTitle>
              </div>
              <CardDescription>设置知识库的基本信息</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* 名称 */}
              <div className="grid grid-cols-[120px_1fr] items-center gap-4">
                <Label className="text-right text-muted-foreground">
                  名称 <span className="text-destructive">*</span>
                </Label>
                <Input
                  value={configName}
                  onChange={(e) => setConfigName(e.target.value)}
                  placeholder="知识库名称"
                  className="max-w-md"
                />
              </div>

              {/* 描述 */}
              <div className="grid grid-cols-[120px_1fr] items-start gap-4">
                <Label className="text-right text-muted-foreground pt-2">描述</Label>
                <Textarea
                  value={configDescription}
                  onChange={(e) => setConfigDescription(e.target.value)}
                  placeholder="知识库描述（可选）"
                  className="max-w-md min-h-[80px]"
                />
              </div>

              {/* 嵌入模型 - 使用新的 AllModelsSelector */}
              <div className="grid grid-cols-[120px_1fr] items-start gap-4">
                <Label className="text-right text-muted-foreground pt-2 flex items-center gap-1 justify-end">
                  嵌入模型
                  <Tooltip>
                    <TooltipTrigger>
                      <HelpCircle className="h-3.5 w-3.5 text-muted-foreground/60" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>用于将文本转换为向量的模型</p>
                    </TooltipContent>
                  </Tooltip>
                </Label>
                <div className="max-w-md">
                  <AllModelsSelector
                    type="embedding"
                    value={configEmbeddingModel}
                    onChange={setConfigEmbeddingModel}
                    label=""
                    placeholder="选择嵌入模型"
                  />
                  {(!configEmbeddingModel.provider || !configEmbeddingModel.model) && defaultModels.embedding && (
                    <p className="text-xs text-muted-foreground mt-1">
                      未选择时将使用默认设置: {defaultModels.embedding.provider} / {defaultModels.embedding.model}
                    </p>
                  )}
                </div>
              </div>

              {/* 分段设置（只读） */}
              <div className="grid grid-cols-[120px_1fr] items-start gap-4">
                <Label className="text-right text-muted-foreground pt-2">分段设置</Label>
                {kb?.config?.ingestion?.chunker ? (
                  <div className="max-w-md p-3 rounded-lg border bg-muted/30">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="secondary" className="text-xs">
                        {kb.config.ingestion.chunker.name || "未设置"}
                      </Badge>
                    </div>
                    {kb.config.ingestion.chunker.params && Object.keys(kb.config.ingestion.chunker.params).length > 0 && (
                      <div className="text-xs text-muted-foreground space-y-1">
                        {Object.entries(kb.config.ingestion.chunker.params).map(([key, value]) => (
                          <div key={key} className="flex justify-between">
                            <span>{key}:</span>
                            <span className="font-mono">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="max-w-md text-sm text-muted-foreground">
                    未配置（将使用默认设置）
                  </div>
                )}
              </div>

              {/* 索引方法设置（只读） */}
              <div className="grid grid-cols-[120px_1fr] items-start gap-4">
                <Label className="text-right text-muted-foreground pt-2">索引方法</Label>
                {kb?.config?.ingestion?.indexer ? (
                  <div className="max-w-md p-3 rounded-lg border bg-muted/30">
                    <div className="font-medium text-sm mb-1">{kb.config.ingestion.indexer.name}</div>
                    {kb.config.ingestion.indexer.params && Object.keys(kb.config.ingestion.indexer.params).length > 0 && (
                      <div className="text-xs text-muted-foreground space-y-1">
                        {Object.entries(kb.config.ingestion.indexer.params).map(([key, value]) => (
                          <div key={key} className="flex justify-between">
                            <span>{key}:</span>
                            <span className="font-mono">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="max-w-md text-sm text-muted-foreground">
                    standard（默认）
                  </div>
                )}
              </div>

              {/* 文档增强设置（只读） */}
              <div className="grid grid-cols-[120px_1fr] items-start gap-4">
                <Label className="text-right text-muted-foreground pt-2">文档增强</Label>
                {kb?.config?.ingestion?.enricher ? (
                  <div className="max-w-md p-3 rounded-lg border bg-muted/30">
                    <div className="font-medium text-sm mb-1">{kb.config.ingestion.enricher.name}</div>
                    <div className="text-xs text-muted-foreground space-y-1">
                      <div className="flex justify-between">
                        <span>文档摘要:</span>
                        <span className="font-mono">{kb.config.ingestion.enricher.generate_summary ? "已开启" : "未开启"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>分块增强:</span>
                        <span className="font-mono">{kb.config.ingestion.enricher.enrich_chunks ? "已开启" : "未开启"}</span>
                      </div>
                      {kb.config.ingestion.enricher.params && Object.keys(kb.config.ingestion.enricher.params).length > 0 && (
                        <>
                          {Object.entries(kb.config.ingestion.enricher.params).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span>{key}:</span>
                              <span className="font-mono">{String(value)}</span>
                            </div>
                          ))}
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="max-w-md text-sm text-muted-foreground">
                    未配置
                  </div>
                )}
              </div>

              {/* 全局默认模型配置（只读展示） */}
              <Separator className="my-4" />
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Label className="text-muted-foreground text-sm">全局默认模型</Label>
                  <Tooltip>
                    <TooltipTrigger>
                      <HelpCircle className="h-3.5 w-3.5 text-muted-foreground/60" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>项目中使用模型时的默认配置，可在主导航「设置」中修改</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <div className="max-w-md p-3 rounded-lg border bg-muted/30 space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">LLM:</span>
                    <span className="font-mono">
                      {defaultModels.llm ? `${defaultModels.llm.provider} / ${defaultModels.llm.model}` : "未设置"}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Embedding:</span>
                    <span className="font-mono">
                      {defaultModels.embedding ? `${defaultModels.embedding.provider} / ${defaultModels.embedding.model}` : "未设置"}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Rerank:</span>
                    <span className="font-mono">
                      {defaultModels.rerank ? `${defaultModels.rerank.provider} / ${defaultModels.rerank.model}` : "未设置"}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 保存按钮 */}
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setActiveNav("files")}>
              取消
            </Button>
            <Button onClick={handleSaveConfig} disabled={isSavingConfig || !configName.trim()}>
              {isSavingConfig ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-2" />
              )}
              保存
            </Button>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* 左侧边栏 */}
      <div className="w-52 border-r bg-muted/30 flex flex-col shrink-0">
        {/* 返回按钮 */}
        <div className="p-4 border-b">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => router.push("/knowledge-bases")}
            className="gap-2 text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
            返回知识库
          </Button>
        </div>

        {/* 知识库信息卡片 */}
        <div className="p-4 border-b">
          <div className="flex items-center gap-3">
            {customIconUrl ? (
              <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0 bg-muted flex items-center justify-center">
                <img src={customIconUrl} alt="知识库图标" className="max-w-full max-h-full object-contain" />
              </div>
            ) : (
              <div className={cn("w-12 h-12 rounded-lg flex items-center justify-center shrink-0", coverIcon.color)}>
                <CoverIconComponent className="h-6 w-6 text-white" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h2 className="font-semibold truncate" title={kb?.name}>
                {kb?.name || "知识库"}
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {documents.length} 个文件
              </p>
            </div>
          </div>
          {kb?.description && (
            <p className="text-xs text-muted-foreground mt-3 line-clamp-2">
              {kb.description}
            </p>
          )}
        </div>

        {/* 导航菜单 */}
        <nav className="flex-1 p-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setActiveNav(item.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  activeNav === item.id
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* 右侧主内容区 */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* 顶部工具栏 - 根据 activeNav 显示不同内容 */}
        {activeNav === "files" && (
          <div className="flex items-center justify-between px-6 py-4 border-b bg-background">
            <div>
              <h1 className="text-xl font-semibold">文件列表</h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                上传文档后即可进行智能问答
              </p>
            </div>
            <div className="flex items-center gap-3">
              {/* 搜索框 */}
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索文档..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 h-8 w-48 text-sm"
                />
              </div>
              <Button variant="outline" size="sm" onClick={() => loadDocuments()} disabled={isLoading}>
                <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
              </Button>
              {/* 新增文件下拉菜单 */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="sm" disabled={!isConnected || isUploading}>
                    {isUploading ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Plus className="h-4 w-4 mr-2" />
                    )}
                    新增文件
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-40">
                  <DropdownMenuItem onClick={openUploadDialog}>
                    <Upload className="h-4 w-4 mr-2" />
                    上传文件
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setNewFileDialogOpen(true)}>
                    <FileText className="h-4 w-4 mr-2" />
                    新增空文件
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        )}

        {activeNav === "config" && (
          <div className="flex items-center justify-between px-6 py-4 border-b bg-background">
            <div>
              <h1 className="text-xl font-semibold">配置</h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                在这里更新您的知识库详细信息，尤其是切片方法。
              </p>
            </div>
          </div>
        )}

        {activeNav === "search" && (
          <div className="flex items-center justify-between px-6 py-4 border-b bg-background">
            <div>
              <h1 className="text-xl font-semibold">检索测试</h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                测试知识库检索效果
              </p>
            </div>
          </div>
        )}

        {activeNav === "logs" && (
          <div className="flex items-center justify-between px-6 py-4 border-b bg-background">
            <div>
              <h1 className="text-xl font-semibold">日志</h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                查看知识库操作日志
              </p>
            </div>
          </div>
        )}

        {/* 内容区域 - 根据 activeNav 切换 */}
        {activeNav === "files" && (
        <div className="flex-1 flex flex-col min-h-0 px-6">
          {/* 上传进度显示 */}
          {Object.keys(uploadProgress).length > 0 && (
            <div className="my-4 p-4 border rounded-lg bg-muted/30">
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                正在上传...
              </h4>
              <div className="space-y-2">
                {Object.entries(uploadProgress).map(([name, progress]) => (
                  <div key={name} className="flex items-center gap-3 text-sm">
                    <File className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="flex-1 truncate">{name}</span>
                    <div className="w-32 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
                    </div>
                    <span className="w-10 text-right text-xs text-muted-foreground">{progress}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 文档列表 - 直接填充内容区域 */}
          <div className="flex-1 flex flex-col min-h-0 overflow-auto">
            {!isConnected ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Database className="h-10 w-10 text-muted-foreground/50 mb-3" />
                <p className="text-muted-foreground">请先在设置页面配置 API Key</p>
              </div>
            ) : isLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : filteredDocuments.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <FileText className="h-10 w-10 text-muted-foreground/50 mb-3" />
                <p className="text-muted-foreground">
                  {searchQuery ? "没有找到匹配的文档" : "暂无文档，上传文件开始使用"}
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="w-[40%]">名称</TableHead>
                    <TableHead className="w-[20%]">上传日期</TableHead>
                    <TableHead className="w-[15%] text-center">分块数</TableHead>
                    <TableHead className="w-[25%] text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredDocuments.map((doc) => (
                    <TableRow key={doc.id} className="group">
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded bg-muted flex items-center justify-center shrink-0">
                            <FileText className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <span className="font-medium truncate" title={doc.title}>
                            {doc.title}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="h-3.5 w-3.5" />
                          {formatDate(doc.created_at)}
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        {doc.processing_status === "pending" || doc.processing_status === "processing" ? (
                          <div className="flex items-center justify-center gap-1.5 text-amber-600">
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            <span className="text-sm">处理中</span>
                          </div>
                        ) : doc.processing_status === "failed" ? (
                          <div className="flex items-center justify-center gap-1.5 text-red-600">
                            <span className="text-sm">失败</span>
                          </div>
                        ) : doc.processing_status === "interrupted" ? (
                          <div className="flex items-center justify-center gap-1.5 text-orange-600">
                            <span className="text-sm">已中断</span>
                          </div>
                        ) : (
                          <div className="flex items-center justify-center gap-1.5">
                            <Layers className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="text-sm font-medium">{doc.chunk_count}</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button size="icon" variant="ghost" className="h-8 w-8" title="预览">
                            <Eye className="h-4 w-4" />
                          </Button>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button size="icon" variant="ghost" className="h-8 w-8">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                onClick={() => handleViewLog(doc.id, doc.title)}
                              >
                                <ScrollText className="h-4 w-4 mr-2" />
                                查看日志
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => handleDeleteClick(doc.id, doc.title)}
                                className="text-destructive focus:text-destructive"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                删除
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </div>
        )}

        {/* 配置面板 */}
        {activeNav === "config" && (
          <div className="flex-1 flex flex-col min-h-0 px-6 py-4 overflow-auto">
            {renderConfigPanel()}
          </div>
        )}

        {/* 检索测试面板 - 暂未实现 */}
        {activeNav === "search" && (
          <div className="flex-1 flex flex-col items-center justify-center">
            <Search className="h-12 w-12 text-muted-foreground/30 mb-4" />
            <p className="text-muted-foreground">检索测试功能开发中...</p>
          </div>
        )}

        {/* 日志面板 - 暂未实现 */}
        {activeNav === "logs" && (
          <div className="flex-1 flex flex-col items-center justify-center">
            <ScrollText className="h-12 w-12 text-muted-foreground/30 mb-4" />
            <p className="text-muted-foreground">日志功能开发中...</p>
          </div>
        )}
      </div>

      {/* 删除确认对话框 */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除文档 <span className="font-medium text-foreground">"{deleteTarget?.title}"</span> 吗？
              此操作不可恢复。
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

      {/* 上传文件对话框 */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="max-w-2xl overflow-hidden">
          <DialogHeader>
            <DialogTitle>上传文件</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            {/* 创建时解析开关 */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">创建时解析</Label>
              <div className="flex items-center gap-2">
                <Switch
                  checked={parseOnCreate}
                  onCheckedChange={setParseOnCreate}
                />
              </div>
            </div>

            {/* 文件区域 */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">文件</Label>
              <div
                {...getDialogRootProps()}
                className={cn(
                  "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors min-h-[200px] flex flex-col items-center justify-center",
                  isDialogDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50 bg-muted/20"
                )}
              >
                <input {...getDialogInputProps()} />
                <Upload className="h-10 w-10 mb-4 text-muted-foreground/50" />
                {isDialogDragActive ? (
                  <p className="text-sm text-primary font-medium">释放以添加文件</p>
                ) : (
                  <>
                    <p className="text-sm text-primary font-medium mb-2">
                      点击或拖拽文件至此区域即可上传
                    </p>
                    <p className="text-xs text-muted-foreground">
                      支持单次或批量上传。支持 PDF, DOCX, MD, TXT 格式。
                    </p>
                  </>
                )}
              </div>

              {/* 已选文件列表 */}
              {pendingFiles.length > 0 && (
                <div className="mt-4 space-y-2">
                  <Label className="text-xs text-muted-foreground">
                    已选择 {pendingFiles.length} 个文件
                  </Label>
                  <div className="max-h-32 overflow-auto space-y-1">
                    {pendingFiles.map((file, index) => (
                      <div key={index} className="flex items-center justify-between px-3 py-2 bg-muted/50 rounded text-sm">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <File className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="truncate">{file.name}</span>
                          <span className="text-xs text-muted-foreground shrink-0">
                            ({(file.size / 1024).toFixed(1)} KB)
                          </span>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 shrink-0"
                          onClick={() => removePendingFile(index)}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={handleConfirmUpload}
              disabled={pendingFiles.length === 0}
            >
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 新增空文件对话框 */}
      <Dialog open={newFileDialogOpen} onOpenChange={setNewFileDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>新增空文件</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Input
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              placeholder="请输入文件名..."
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewFileDialogOpen(false)}>
              取消
            </Button>
            <Button
              onClick={handleCreateEmptyFile}
              disabled={isUploading || !newFileName.trim()}
            >
              {isUploading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 文档日志对话框 */}
      <Dialog open={logDialogOpen} onOpenChange={setLogDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ScrollText className="h-5 w-5" />
              文档处理日志
            </DialogTitle>
            {logTarget && (
              <p className="text-sm text-muted-foreground truncate">
                {logTarget.title}
              </p>
            )}
          </DialogHeader>
          <div className="flex-1 min-h-0 overflow-auto">
            {isLoadingLog ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                {/* 解析并显示入库进度 */}
                {(() => {
                  // 使用 Map 来存储步骤，确保每个步骤号只有一个条目
                  const stepsMap = new Map<number, { step: number; total: number; status: string; label: string; timestamp: string }>();
                  // 匹配格式: [时间戳] [INFO] [STEP:N/M:status] label
                  const stepRegex = /\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s*\[\w+\]\s*\[STEP:(\d+)\/(\d+):(\w+)\](?:\s+([^\[\]\n]+))?/g;
                  let match;
                  while ((match = stepRegex.exec(logContent)) !== null) {
                    const timestamp = match[1];
                    const stepNum = parseInt(match[2]);
                    const total = parseInt(match[3]);
                    const status = match[4];
                    const label = match[5]?.trim() || "";
                    
                    const existing = stepsMap.get(stepNum);
                    if (existing) {
                      // 更新状态和时间戳
                      existing.status = status;
                      existing.timestamp = timestamp;
                      if (label && !existing.label) {
                        existing.label = label;
                      }
                    } else if (label) {
                      // 只有有 label 的才添加新步骤
                      stepsMap.set(stepNum, { step: stepNum, total, status, label, timestamp });
                    }
                  }
                  // 转换为数组并按步骤号排序
                  const steps = Array.from(stepsMap.values()).sort((a, b) => a.step - b.step);
                  if (steps.length > 0) {
                    return (
                      <div className="mb-4 p-4 bg-muted/30 rounded-lg border">
                        <h4 className="text-sm font-medium mb-3">入库进度</h4>
                        <div className="space-y-2">
                          {steps.map((s) => (
                            <div key={s.step} className="flex items-center gap-3">
                              <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                                {s.status === "done" && (
                                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                                )}
                                {s.status === "running" && (
                                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                                )}
                                {s.status === "error" && (
                                  <XCircle className="h-4 w-4 text-red-500" />
                                )}
                                {s.status === "skipped" && (
                                  <Circle className="h-4 w-4 text-muted-foreground" />
                                )}
                                {!["done", "running", "error", "skipped"].includes(s.status) && (
                                  <Circle className="h-4 w-4 text-muted-foreground" />
                                )}
                              </div>
                              <span className="text-xs text-muted-foreground font-mono w-20 flex-shrink-0">
                                {s.timestamp.split(" ")[1]}
                              </span>
                              <span className={`text-sm ${s.status === "done" ? "text-green-600" : s.status === "error" ? "text-red-600" : s.status === "skipped" ? "text-muted-foreground" : ""}`}>
                                {s.label}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  }
                  return null;
                })()}
                {/* 详细日志文本 */}
                <pre className="bg-muted/50 rounded-lg p-4 text-xs font-mono whitespace-pre-wrap break-words overflow-auto max-h-[40vh]">
                  {logContent || "暂无日志"}
                </pre>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLogDialogOpen(false)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
