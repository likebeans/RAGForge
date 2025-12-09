"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  OperatorListResponse,
  PlaygroundRunRequest,
  PlaygroundRunResponse,
  GroundInfo,
  ChunkPreviewItem,
} from "@/lib/api";
import { useAppStore } from "@/lib/store";
import {
  Loader2,
  Play,
  Save,
  Upload,
  FileText,
  Trash2,
  UploadCloud,
  ArrowLeft,
  Search,
  RotateCcw,
} from "lucide-react";
import { ProviderModelSelector } from "@/components/settings";
import { useDropzone } from "react-dropzone";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";

// 切分器参数 UI 配置
type ParamConfig = {
  key: string;
  label: string;
  type: 'number' | 'boolean' | 'select' | 'slider' | 'text';
  default: number | boolean | string;
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
  showWhen?: Record<string, unknown>;
  description?: string;
  group?: string; // 参数分组
};

type ChunkerConfig = {
  label: string;
  description: string;
  params: ParamConfig[];
};

const CHUNKER_UI_CONFIG: Record<string, ChunkerConfig> = {
  simple: {
    label: '简单分段',
    description: '按自定义分隔符切分，适合结构清晰的文本',
    params: [
      { key: 'separator', label: '分段标识符', type: 'text', default: '\\n\\n',
        description: '支持: \\n\\n(段落) \\n(换行) \\t(制表) 或自定义字符' },
      { key: 'max_chars', label: '分段最大长度', type: 'number', default: 1024, min: 100, max: 5000 }
    ]
  },
  sliding_window: {
    label: '滑动窗口',
    description: '固定窗口滑动切分，保持片段重叠',
    params: [
      { key: 'window', label: '窗口大小', type: 'number', default: 800, min: 100, max: 5000 },
      { key: 'overlap', label: '重叠大小', type: 'number', default: 200, min: 0, max: 1000 }
    ]
  },
  parent_child: {
    label: '父子分块',
    description: '子块用于检索，父块用作上下文',
    params: [
      // 父块配置
      { key: 'parent_mode', label: '父块模式', type: 'select', default: 'paragraph',
        options: ['paragraph', 'full_doc'], group: '父块用作上下文',
        description: 'paragraph: 按分隔符分段; full_doc: 整个文档作为父块' },
      { key: 'parent_separator', label: '父块分隔符', type: 'text', default: '\\n\\n',
        group: '父块用作上下文', showWhen: { parent_mode: 'paragraph' },
        description: '支持: \\n\\n \\n 。 . 或自定义' },
      { key: 'parent_max_chars', label: '父块最大长度', type: 'number', default: 1024, min: 200, max: 10000,
        group: '父块用作上下文', showWhen: { parent_mode: 'paragraph' } },
      // 子块配置
      { key: 'child_separator', label: '子块分隔符', type: 'text', default: '\\n',
        group: '子块用于检索', description: '支持: \\n\\n \\n 。 . 或自定义' },
      { key: 'child_max_chars', label: '子块最大长度', type: 'number', default: 512, min: 50, max: 2000,
        group: '子块用于检索' }
    ]
  },
  recursive: {
    label: '递归字符分块',
    description: '优先保持语义边界，推荐通用文档',
    params: [
      { key: 'chunk_size', label: '块大小', type: 'number', default: 1024, min: 100, max: 5000 },
      { key: 'chunk_overlap', label: '重叠大小', type: 'number', default: 256, min: 0, max: 1000 },
      { key: 'separators', label: '分隔符优先级', type: 'text', default: '\\n\\n,\\n,。,.',
        description: '按优先级排列，用逗号分隔' },
      { key: 'keep_separator', label: '保留分隔符', type: 'boolean', default: true }
    ]
  },
  markdown: {
    label: 'Markdown 分块',
    description: '按标题层级切分，适合技术文档',
    params: [
      { key: 'chunk_size', label: '块大小', type: 'number', default: 1024, min: 100, max: 5000 },
      { key: 'chunk_overlap', label: '重叠大小', type: 'number', default: 256, min: 0, max: 1000 },
      { key: 'headers_to_split_on', label: '标题层级', type: 'text', default: '#,##,###',
        description: '要切分的标题级别，用逗号分隔' },
      { key: 'strip_headers', label: '移除标题', type: 'boolean', default: false }
    ]
  },
  markdown_section: {
    label: 'Markdown 分节',
    description: '基于 LlamaIndex 的 Markdown 分节切分',
    params: [
      { key: 'chunk_size', label: '块大小', type: 'number', default: 1200, min: 100, max: 5000 },
      { key: 'chunk_overlap', label: '重叠大小', type: 'number', default: 200, min: 0, max: 1000 }
    ]
  },
  code: {
    label: '代码分块',
    description: '按语法结构切分，保持函数/类完整',
    params: [
      { key: 'language', label: '语言', type: 'select', default: 'auto', 
        options: ['auto', 'python', 'javascript', 'typescript', 'java', 'go', 'rust'] },
      { key: 'max_chunk_size', label: '最大块大小', type: 'number', default: 2000, min: 500, max: 10000 },
      { key: 'include_imports', label: '包含导入语句', type: 'boolean', default: true }
    ]
  },
  llama_sentence: {
    label: '句子分块',
    description: '保持句子完整，基于 Token 计数',
    params: [
      { key: 'max_tokens', label: '最大 Token', type: 'number', default: 512, min: 50, max: 2000 },
      { key: 'chunk_overlap', label: '重叠 Token', type: 'number', default: 50, min: 0, max: 200 }
    ]
  },
  llama_token: {
    label: 'Token 分块',
    description: '严格按 Token 切分，精确控制长度',
    params: [
      { key: 'max_tokens', label: '最大 Token', type: 'number', default: 512, min: 50, max: 2000 },
      { key: 'chunk_overlap', label: '重叠 Token', type: 'number', default: 50, min: 0, max: 200 }
    ]
  }
};

// 获取切分器默认参数
function getDefaultChunkerParams(chunkerName: string): Record<string, unknown> {
  const config = CHUNKER_UI_CONFIG[chunkerName];
  if (!config) return {};
  const params: Record<string, unknown> = {};
  for (const p of config.params) {
    params[p.key] = p.default;
  }
  return params;
}

// 安全获取 metadata 的布尔值
function getMetadataBool(metadata: Record<string, unknown> | undefined, key: string): boolean | undefined {
  if (!metadata || !(key in metadata)) return undefined;
  const val = metadata[key];
  return typeof val === 'boolean' ? val : undefined;
}

// 安全获取 metadata 的字符串值
function getMetadataStr(metadata: Record<string, unknown> | undefined, key: string): string | undefined {
  if (!metadata || !(key in metadata)) return undefined;
  const val = metadata[key];
  return val != null ? String(val) : undefined;
}

type Experiment = {
  id: string;
  name: string;
  retriever: string;
  topK: number;
  chunker?: string;
  rerank?: boolean;
  chunkPreviewText?: string;
};

const makeId = () => Math.random().toString(36).slice(2, 8);

export default function GroundDetailPage() {
  const params = useParams();
  const groundId = params.id as string;
  const router = useRouter();
  const {
    client,
    isConnected,
    refreshKnowledgeBases,
    defaultModels,
    providerConfigs,
  } = useAppStore();

  const [ground, setGround] = useState<GroundInfo | null>(null);
  const [operators, setOperators] = useState<OperatorListResponse | null>(null);
  const [documents, setDocuments] = useState<{ id: string; title: string; chunk_count: number; created_at: string }[]>([]);
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState("");
  const [experiments, setExperiments] = useState<Experiment[]>([
    { id: makeId(), name: "方案 A", retriever: "hybrid", topK: 5 },
    { id: makeId(), name: "方案 B", retriever: "dense", topK: 5 },
  ]);
  const [results, setResults] = useState<Record<string, PlaygroundRunResponse>>({});
  const [isRunning, setIsRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  // 分块预览状态
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [selectedChunker, setSelectedChunker] = useState("recursive");
  const [chunkerParams, setChunkerParams] = useState<Record<string, unknown>>(
    getDefaultChunkerParams("recursive")
  );
  const [chunkPreviewResult, setChunkPreviewResult] = useState<ChunkPreviewItem[]>([]);
  const [chunkPreviewDocTitle, setChunkPreviewDocTitle] = useState("");
  const [isPreviewing, setIsPreviewing] = useState(false);
  // 预览类型: 'result' | 'chunk' | 'retrieval' | 'index'
  const [previewType, setPreviewType] = useState<"result" | "chunk">("result");

  const retrieverOptions = useMemo(() => operators?.retrievers || [], [operators]);
  const chunkerOptions = useMemo(() => operators?.chunkers || [], [operators]);

  // useDropzone 必须在条件返回之前调用，保证 Hooks 顺序一致
  const {
    getRootProps: getDialogRootProps,
    getInputProps: getDialogInputProps,
    isDragActive: isDialogDragActive,
  } = useDropzone({
    onDrop: (accepted) => setPendingFiles((prev) => [...prev, ...accepted]),
    accept: {
      "application/pdf": [".pdf"],
      "text/markdown": [".md"],
      "text/plain": [".txt"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    },
    disabled: uploading,
  });

  const loadGround = async () => {
    if (!client || !groundId) return;
    try {
      const info = await client.getGround(groundId);
      setGround(info);
      setIsLoading(false);
    } catch (error) {
      toast.error("Ground 不存在");
      router.push("/compare");
      setIsLoading(false);
    }
  };

  const loadOperators = async () => {
    if (!client) return;
    try {
      const ops = await client.listOperators();
      setOperators(ops);
    } catch (error) {
      console.error(error);
    }
  };

  const loadDocuments = async () => {
  if (!client || !ground) return;
    try {
      const res = await client.listDocuments(ground.knowledge_base_id);
      setDocuments(res.items || []);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    if (client && isConnected) {
      loadGround();
      loadOperators();
    }
  }, [client, isConnected]);

  useEffect(() => {
    if (ground) {
      loadDocuments();
    }
  }, [ground]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        正在加载 ground...
      </div>
    );
  }

  const confirmDialogUpload = async () => {
    if (!client || !ground || pendingFiles.length === 0) {
      setUploadDialogOpen(false);
      return;
    }
    setUploadDialogOpen(false);
    setUploading(true);
    try {
      for (const file of pendingFiles) {
        // 使用 Ground 专用上传 API（只保存原始内容，不做切分处理）
        await client.uploadGroundDocument(groundId, file);
      }
      toast.success("上传成功");
      loadDocuments();
    } catch (error) {
      toast.error(`上传失败: ${(error as Error).message}`);
    } finally {
      setPendingFiles([]);
      setUploading(false);
    }
  };

  // 分块预览
  const handleChunkPreview = async () => {
    if (!client || !ground || !selectedDocId) {
      toast.error("请选择要预览的文档");
      return;
    }
    setIsPreviewing(true);
    try {
      const res = await client.previewChunks(groundId, selectedDocId, selectedChunker, chunkerParams);
      setChunkPreviewResult(res.chunks);
      setChunkPreviewDocTitle(res.document_title);
      setPreviewType("chunk"); // 切换到分块预览
    } catch (error) {
      toast.error(`预览失败: ${(error as Error).message}`);
    } finally {
      setIsPreviewing(false);
    }
  };

  // 切分器切换时重置参数
  const handleChunkerChange = (newChunker: string) => {
    setSelectedChunker(newChunker);
    setChunkerParams(getDefaultChunkerParams(newChunker));
  };

  // 更新单个参数
  const updateChunkerParam = (key: string, value: unknown) => {
    setChunkerParams(prev => ({ ...prev, [key]: value }));
  };

  // 检查参数是否应该显示（根据 showWhen 条件）
  const shouldShowParam = (param: ParamConfig): boolean => {
    if (!param.showWhen) return true;
    return Object.entries(param.showWhen).every(
      ([key, expected]) => chunkerParams[key] === expected
    );
  };

  // 渲染参数输入控件
  const renderParamInput = (param: ParamConfig) => {
    const value = chunkerParams[param.key] ?? param.default;
    
    switch (param.type) {
      case 'number':
        return (
          <Input
            type="number"
            min={param.min}
            max={param.max}
            value={value as number}
            onChange={(e) => updateChunkerParam(param.key, Number(e.target.value))}
            className="h-8"
          />
        );
      case 'boolean':
        return (
          <Switch
            checked={value as boolean}
            onCheckedChange={(checked) => updateChunkerParam(param.key, checked)}
          />
        );
      case 'select':
        return (
          <Select value={value as string} onValueChange={(v) => updateChunkerParam(param.key, v)}>
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {param.options?.map((opt) => (
                <SelectItem key={opt} value={opt}>{opt}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      case 'slider':
        return (
          <div className="flex items-center gap-2">
            <Slider
              value={[value as number]}
              min={param.min}
              max={param.max}
              step={param.step || 0.1}
              onValueChange={([v]) => updateChunkerParam(param.key, v)}
              className="flex-1"
            />
            <span className="text-sm w-12 text-right">{(value as number).toFixed(1)}</span>
          </div>
        );
      case 'text':
        return (
          <Input
            type="text"
            value={value as string}
            onChange={(e) => updateChunkerParam(param.key, e.target.value)}
            className="h-8"
            placeholder={param.description}
          />
        );
      default:
        return null;
    }
  };

  // 按分组渲染参数
  const renderChunkerParams = () => {
    const config = CHUNKER_UI_CONFIG[selectedChunker];
    if (!config) return null;
    
    // 收集分组
    const groups: Record<string, ParamConfig[]> = {};
    const ungrouped: ParamConfig[] = [];
    
    config.params.forEach(p => {
      if (!shouldShowParam(p)) return;
      if (p.group) {
        if (!groups[p.group]) groups[p.group] = [];
        groups[p.group].push(p);
      } else {
        ungrouped.push(p);
      }
    });

    return (
      <>
        {/* 无分组参数 */}
        {ungrouped.map((param) => (
          <div key={param.key} className="space-y-1">
            <div className="flex items-center justify-between">
              <Label className="text-xs">{param.label}</Label>
              {param.type === 'boolean' && renderParamInput(param)}
            </div>
            {param.description && param.type !== 'text' && (
              <p className="text-xs text-muted-foreground">{param.description}</p>
            )}
            {param.type !== 'boolean' && renderParamInput(param)}
          </div>
        ))}
        
        {/* 分组参数 */}
        {Object.entries(groups).map(([groupName, params]) => (
          <div key={groupName} className="space-y-2 pt-2 border-t">
            <Label className="text-xs font-semibold text-muted-foreground">{groupName}</Label>
            {params.map((param) => (
              <div key={param.key} className="space-y-1">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">{param.label}</Label>
                  {param.type === 'boolean' && renderParamInput(param)}
                </div>
                {param.description && param.type !== 'text' && (
                  <p className="text-xs text-muted-foreground">{param.description}</p>
                )}
                {param.type !== 'boolean' && renderParamInput(param)}
              </div>
            ))}
          </div>
        ))}
      </>
    );
  };

  // 删除文档
  const handleDeleteDocument = async (docId: string) => {
    if (!client) return;
    try {
      await client.deleteDocument(docId);
      toast.success("删除成功");
      // 如果删除的是当前选中的文档，清空选中状态
      if (selectedDocId === docId) {
        setSelectedDocId("");
        setChunkPreviewResult([]);
        setChunkPreviewDocTitle("");
      }
      loadDocuments();
    } catch (error) {
      toast.error(`删除失败: ${(error as Error).message}`);
    }
  };

  const resetChunkPreview = () => {
    setSelectedDocId("");
    setChunkPreviewResult([]);
    setChunkPreviewDocTitle("");
    setPreviewType("result"); // 重置回结果预览
  };

  const runExperiments = async () => {
    if (!client || !ground) return;
    if (!query.trim()) {
      toast.error("请输入测试问题");
      return;
    }
    setIsRunning(true);
    try {
      const payloads: PlaygroundRunRequest[] = experiments.map((exp) => ({
        query,
        knowledge_base_ids: [ground.knowledge_base_id],
        top_k: exp.topK,
        retriever: exp.retriever ? { name: exp.retriever } : undefined,
        rerank: exp.rerank,
        chunker: exp.chunker,
        chunk_preview_text: exp.chunkPreviewText,
        llm_override:
          defaultModels.llm && defaultModels.llm.model && defaultModels.llm.provider
            ? {
                provider: defaultModels.llm.provider,
                model: defaultModels.llm.model,
                api_key: providerConfigs[defaultModels.llm.provider]?.apiKey,
                base_url: providerConfigs[defaultModels.llm.provider]?.baseUrl,
              }
            : undefined,
      }));
      const responses = await Promise.all(payloads.map((p) => client.runPlayground(p)));
      const next: Record<string, PlaygroundRunResponse> = {};
      responses.forEach((resp, idx) => {
        next[experiments[idx].id] = resp;
      });
      setResults(next);
    } catch (error) {
      toast.error(`运行失败: ${(error as Error).message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const saveGround = async () => {
    if (!client || !ground) return;
    setSaving(true);
    try {
      const saved = await client.saveGround(ground.ground_id);
      toast.success("已保存到主知识库");
      setGround(saved);
      refreshKnowledgeBases();
    } catch (error) {
      toast.error(`保存失败: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex h-full flex-col bg-slate-50">
      <div className="border-b bg-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push("/compare")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="font-semibold text-lg">{ground?.name || "Ground"}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {ground?.document_count || 0} 个文件
            </div>
          </div>
        </div>
        <Button
          onClick={() => saveGround()}
          disabled={ground?.saved || saving}
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
          {ground?.saved ? "已保存" : "保存到知识库"}
        </Button>
      </div>

      <div className="flex-1 overflow-hidden p-6">
        <div className="grid gap-4 lg:grid-cols-[400px_1fr] h-[calc(100vh-140px)]">
          <div className="overflow-y-auto h-full pr-2">
            <div className="space-y-4">
              <Card>
              <CardHeader>
                <CardTitle>文件上传</CardTitle>
                <CardDescription>上传用于本 ground 的文件</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2">
                  <Input type="text" readOnly value={pendingFiles.length ? `${pendingFiles.length} 个待上传` : "点击上传文件"} className="flex-1" />
                  <Button variant="outline" onClick={() => setUploadDialogOpen(true)}>
                    <Upload className="h-4 w-4 mr-2" />
                    上传
                  </Button>
                </div>
                <ScrollArea className="max-h-[200px] pr-2">
                  <div className="space-y-2">
                    {documents.map((doc) => (
                      <div key={doc.id} className="rounded border p-2 bg-muted/30 flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">{doc.title}</div>
                          <div className="text-xs text-muted-foreground">
                            {doc.chunk_count || 0} chunks · {new Date(doc.created_at).toLocaleString()}
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 text-muted-foreground hover:text-destructive shrink-0"
                          onClick={() => handleDeleteDocument(doc.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    ))}
                    {documents.length === 0 && (
                      <div className="text-sm text-muted-foreground">暂无文件，先上传吧。</div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* 分段设置卡片 */}
            <Card>
              <CardHeader>
                <CardTitle>分段设置</CardTitle>
                <CardDescription>配置文本切分策略并预览效果</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border-2 border-primary/20 p-4 space-y-4 bg-primary/5">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <FileText className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <div className="font-medium">通用</div>
                      <div className="text-xs text-muted-foreground">通用文本分块模式</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <div className="text-sm text-muted-foreground">选择文档</div>
                      <Select value={selectedDocId} onValueChange={setSelectedDocId}>
                        <SelectTrigger>
                          <SelectValue placeholder="选择要预览的文档" />
                        </SelectTrigger>
                        <SelectContent>
                          {documents.map((doc) => (
                            <SelectItem key={doc.id} value={doc.id}>
                              {doc.title}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm text-muted-foreground">切分器</div>
                      <Select value={selectedChunker} onValueChange={handleChunkerChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="选择切分器" />
                        </SelectTrigger>
                        <SelectContent>
                          {chunkerOptions.map((c) => (
                            <SelectItem key={c.name} value={c.name}>
                              {CHUNKER_UI_CONFIG[c.name]?.label || c.label || c.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  
                  {/* 动态参数配置 */}
                  {CHUNKER_UI_CONFIG[selectedChunker] && (
                    <div className="space-y-3 pt-2 border-t border-primary/10">
                      <div className="text-xs text-muted-foreground">
                        {CHUNKER_UI_CONFIG[selectedChunker].description}
                      </div>
                      <div className="space-y-3">
                        {renderChunkerParams()}
                      </div>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={handleChunkPreview}
                      disabled={isPreviewing || !selectedDocId || documents.length === 0}
                    >
                      {isPreviewing ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : (
                        <Search className="h-4 w-4 mr-2" />
                      )}
                      预览
                    </Button>
                    <Button variant="ghost" onClick={resetChunkPreview}>
                      <RotateCcw className="h-4 w-4 mr-2" />
                      重置
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 检索配置卡片 */}
            <Card>
              <CardHeader>
                <CardTitle>检索配置</CardTitle>
                <CardDescription>配置检索策略</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  placeholder="输入测试问题"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="min-h-[80px]"
                />
                {experiments.map((exp, idx) => (
                  <div key={exp.id} className="rounded border p-3 space-y-2 bg-muted/20">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">方案 {idx + 1}</Badge>
                      <Input
                        value={exp.name}
                        onChange={(e) =>
                          setExperiments((prev) =>
                            prev.map((p) => (p.id === exp.id ? { ...p, name: e.target.value } : p))
                          )
                        }
                        className="h-8"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="space-y-1">
                        <div className="text-xs text-muted-foreground">检索器</div>
                        <Select
                          value={exp.retriever}
                          onValueChange={(v: string) =>
                            setExperiments((prev) =>
                              prev.map((p) => (p.id === exp.id ? { ...p, retriever: v } : p))
                            )
                          }
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="选择检索器" />
                          </SelectTrigger>
                          <SelectContent>
                            {retrieverOptions.map((r) => (
                              <SelectItem key={r.name} value={r.name}>
                                {r.label || r.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1">
                        <div className="text-xs text-muted-foreground">Top K</div>
                        <Input
                          type="number"
                          min={1}
                          max={50}
                          value={exp.topK}
                          onChange={(e) =>
                            setExperiments((prev) =>
                              prev.map((p) => (p.id === exp.id ? { ...p, topK: Number(e.target.value) } : p))
                            )
                          }
                        />
                      </div>
                    </div>
                  </div>
                ))}
                <div className="flex justify-end">
                  <Button onClick={runExperiments} disabled={isRunning || documents.length === 0}>
                    {isRunning ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        运行中...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 mr-2" />
                        运行实验
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>模型配置</CardTitle>
                <CardDescription>选择默认 LLM 模型</CardDescription>
              </CardHeader>
              <CardContent>
                <ProviderModelSelector type="llm" />
              </CardContent>
            </Card>
            </div>
          </div>

          <div className="overflow-y-auto h-full">
            <div className="space-y-4 pr-2">
            {/* 统一预览卡片 */}
            <Card>
              <CardHeader>
                <CardTitle>结果预览</CardTitle>
                <CardDescription>
                  {previewType === "chunk"
                    ? `分块预览效果${chunkPreviewDocTitle ? ` - ${chunkPreviewDocTitle}` : ""} (${chunkPreviewResult.length} 块)`
                    : "上传文件并运行实验后在此查看"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {previewType === "chunk" ? (
                  <ScrollArea className="h-[500px]">
                    {chunkPreviewResult.length === 0 ? (
                      <div className="text-sm text-muted-foreground text-center py-12">
                        在左侧选择文档和切分器后点击"预览"
                      </div>
                    ) : (
                      <div className="space-y-4 pr-4">
                        {(() => {
                          // 检查是否为父子分块模式
                          const hasParentChild = chunkPreviewResult.some(c => 
                            getMetadataBool(c.metadata, 'child') !== undefined
                          );
                          
                          if (!hasParentChild) {
                            // 普通分块模式
                            return chunkPreviewResult.map((chunk) => (
                              <div key={chunk.index} className="rounded border p-3 bg-muted/30">
                                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                                  <span className="font-mono font-medium text-foreground">Chunk-{chunk.index}</span>
                                  <span>·</span>
                                  <span>{chunk.char_count} characters</span>
                                </div>
                                <div className="text-sm leading-relaxed whitespace-pre-wrap">{chunk.text}</div>
                                {chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
                                  <div className="mt-2 pt-2 border-t border-muted/50 flex flex-wrap gap-1.5">
                                    {Object.entries(chunk.metadata).map(([k, v]) => (
                                      <span key={k} className="text-xs bg-muted/70 px-1.5 py-0.5 rounded font-mono">
                                        {k}: {typeof v === 'boolean' ? (v ? 'true' : 'false') : String(v).slice(0, 20)}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ));
                          }
                          
                          // 父子分块模式 - 按父块分组
                          const parents = chunkPreviewResult.filter(c => getMetadataBool(c.metadata, 'child') === false);
                          const childrenByParent: Record<string, typeof chunkPreviewResult> = {};
                          
                          chunkPreviewResult.forEach(c => {
                            if (getMetadataBool(c.metadata, 'child') === true) {
                              const pid = getMetadataStr(c.metadata, 'parent_id') || 'unknown';
                              if (!childrenByParent[pid]) childrenByParent[pid] = [];
                              childrenByParent[pid].push(c);
                            }
                          });
                          
                          // 用父块索引作为父块标识的计数器
                          let parentCounter = 0;
                          
                          return parents.map((parent) => {
                            parentCounter++;
                            const parentId = getMetadataStr(parent.metadata, 'chunk_id') || String(parent.index);
                            const children = childrenByParent[parentId] || [];
                            const totalChars = parent.char_count;
                            const parentMode = getMetadataStr(parent.metadata, 'parent_mode');
                            
                            return (
                              <div key={parent.index} className="rounded-lg border bg-card">
                                {/* 父块标题 */}
                                <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
                                  <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">⋮⋮⋮</span>
                                    <span className="font-medium">Chunk-{parentCounter}</span>
                                    <span className="text-muted-foreground">·</span>
                                    <span className="text-sm text-muted-foreground">{totalChars} characters</span>
                                    {children.length > 0 && (
                                      <>
                                        <span className="text-muted-foreground">·</span>
                                        <span className="text-sm text-blue-600 dark:text-blue-400">{children.length} 子块</span>
                                      </>
                                    )}
                                  </div>
                                  {parentMode && (
                                    <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 rounded">
                                      {parentMode === 'full_doc' ? '全文' : '段落'}
                                    </span>
                                  )}
                                </div>
                                {/* 子块内容区域 */}
                                <div className="p-4">
                                  <div className="flex flex-wrap items-start gap-1 leading-relaxed">
                                    {children.length > 0 ? (
                                      children.map((child, idx) => (
                                        <span 
                                          key={child.index} 
                                          className="group inline-flex items-start gap-1 cursor-pointer"
                                        >
                                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 shrink-0 group-hover:bg-blue-200 dark:group-hover:bg-blue-800">
                                            C-{idx + 1}
                                          </span>
                                          <span className="text-sm group-hover:bg-blue-50 dark:group-hover:bg-blue-950/50 rounded px-1 -mx-1 transition-colors">
                                            {child.text}
                                          </span>
                                        </span>
                                      ))
                                    ) : (
                                      <span className="text-sm text-muted-foreground">{parent.text}</span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            );
                          });
                        })()}
                      </div>
                    )}
                  </ScrollArea>
                ) : (
                  <div className="text-sm text-muted-foreground text-center py-12">
                    运行实验后在此查看结果
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 实验结果卡片 */}
            {Object.keys(results).length > 0 && (
              Object.keys(results).map((id) => {
                const exp = experiments.find((e) => e.id === id);
                const res = results[id];
                if (!exp || !res) return null;
                return (
                  <Card key={id}>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        {exp.name}
                        <Badge variant="secondary">检索器 {res.retrieval.retriever}</Badge>
                      </CardTitle>
                      <CardDescription>时延 {Math.round(res.metrics?.total_ms || 0)} ms</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="rounded border p-3 bg-muted/30">
                        <div className="text-xs text-muted-foreground mb-1">回答</div>
                        <div className="text-sm leading-relaxed">{res.rag.answer}</div>
                        <div className="text-xs text-muted-foreground mt-2 flex gap-2 flex-wrap">
                          <Badge variant="outline">LLM: {res.rag.model.llm_model || "-"}</Badge>
                          <Badge variant="outline">Embed: {res.rag.model.embedding_model}</Badge>
                        </div>
                      </div>
                      <div className="rounded border p-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>检索结果</span>
                          <span>{res.retrieval.latency_ms.toFixed(0)} ms</span>
                        </div>
                        <div className="mt-2 space-y-2">
                          {res.retrieval.results.slice(0, 8).map((hit, idx) => (
                            <div key={hit.chunk_id || idx} className="rounded bg-muted/30 p-2">
                              <div className="flex items-center justify-between text-xs text-muted-foreground">
                                <span>#{idx + 1}</span>
                                <span>{hit.score.toFixed(4)}</span>
                              </div>
                              <div className="text-sm line-clamp-2">{hit.text}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                      {res.chunk_preview && res.chunk_preview.length > 0 && (
                        <div className="rounded border p-3">
                          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
                            <span>切分预览</span>
                            <span>{res.chunk_preview.length}</span>
                          </div>
                          <ScrollArea className="h-24 pr-2">
                            <div className="space-y-2">
                              {res.chunk_preview.slice(0, 8).map((c) => (
                                <div key={c.chunk_id} className="rounded bg-muted/30 p-2 text-sm">
                                  {c.text}
                                </div>
                              ))}
                            </div>
                          </ScrollArea>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })
            )}
            </div>
          </div>
        </div>
      </div>

      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>上传文件</DialogTitle>
          </DialogHeader>
          <div className="text-sm text-muted-foreground">文件</div>
          <div
            {...getDialogRootProps()}
            className={`rounded-lg border-2 border-dashed p-8 text-center cursor-pointer transition-colors ${
              isDialogDragActive ? "border-primary bg-primary/5" : "border-muted hover:border-muted-foreground/50"
            }`}
          >
            <input {...getDialogInputProps()} />
            <UploadCloud className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <div className="text-sm text-foreground">
              点击或拖拽文件至此区域即可上传
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              支持单次或批量上传。支持 PDF, DOCX, MD, TXT 格式。
            </div>
          </div>
          
          {pendingFiles.length > 0 && (
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">
                已选择 {pendingFiles.length} 个文件
              </div>
              <div className="max-h-[200px] overflow-auto space-y-2">
                {pendingFiles.map((file, idx) => (
                  <div
                    key={`${file.name}-${idx}`}
                    className="flex items-center justify-between rounded-lg border p-3 bg-muted/30"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <FileText className="h-5 w-5 text-muted-foreground shrink-0" />
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{file.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {(file.size / 1024).toFixed(1)} KB
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="shrink-0 text-muted-foreground hover:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation();
                        setPendingFiles((prev) => prev.filter((_, i) => i !== idx));
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => { setUploadDialogOpen(false); setPendingFiles([]); }}>取消</Button>
            <Button onClick={confirmDialogUpload} disabled={uploading || pendingFiles.length === 0}>
              {uploading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
