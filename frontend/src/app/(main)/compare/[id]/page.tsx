"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Slider } from "@/components/ui/slider";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Play,
  Plus,
  Trash2,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Copy,
  Layers,
  Search,
  Database,
  Brain,
  Sparkles,
  Settings2,
  BarChart3,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

// RAG Pipeline 配置选项
const CHUNKER_OPTIONS = [
  { value: "simple", label: "Simple", desc: "按段落切分" },
  { value: "sliding_window", label: "Sliding Window", desc: "滑动窗口切分" },
  { value: "recursive", label: "Recursive", desc: "递归字符切分" },
  { value: "markdown", label: "Markdown", desc: "按标题层级切分" },
  { value: "code", label: "Code", desc: "代码感知切分" },
  { value: "parent_child", label: "Parent-Child", desc: "父子分块" },
  { value: "llama_sentence", label: "LlamaIndex Sentence", desc: "句子切分" },
];

const RETRIEVER_OPTIONS = [
  { value: "dense", label: "Dense", desc: "稠密向量检索" },
  { value: "bm25", label: "BM25", desc: "稀疏检索" },
  { value: "hybrid", label: "Hybrid", desc: "混合检索" },
  { value: "fusion", label: "Fusion", desc: "RRF融合检索" },
  { value: "hyde", label: "HyDE", desc: "假设文档嵌入" },
  { value: "multi_query", label: "Multi-Query", desc: "多查询扩展" },
  { value: "self_query", label: "Self-Query", desc: "自查询检索" },
  { value: "parent_document", label: "Parent Document", desc: "父文档检索" },
  { value: "raptor", label: "RAPTOR", desc: "多层次索引" },
];

const EMBEDDING_PROVIDERS = [
  { value: "ollama", label: "Ollama" },
  { value: "openai", label: "OpenAI" },
  { value: "zhipu", label: "智谱 AI" },
  { value: "siliconflow", label: "SiliconFlow" },
  { value: "deepseek", label: "DeepSeek" },
];

const EMBEDDING_MODELS: Record<string, string[]> = {
  ollama: ["bge-m3", "nomic-embed-text", "mxbai-embed-large"],
  openai: ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
  zhipu: ["embedding-2", "embedding-3"],
  siliconflow: ["bge-large-zh-v1.5", "bge-m3"],
  deepseek: ["deepseek-embedding"],
};

const RERANK_PROVIDERS = [
  { value: "none", label: "无" },
  { value: "ollama", label: "Ollama" },
  { value: "zhipu", label: "智谱 AI" },
  { value: "siliconflow", label: "SiliconFlow" },
  { value: "cohere", label: "Cohere" },
];

const VECTOR_DB_OPTIONS = [
  { value: "qdrant", label: "Qdrant" },
  { value: "milvus", label: "Milvus" },
  { value: "elasticsearch", label: "Elasticsearch" },
];

const INDEX_TYPE_OPTIONS = [
  { value: "hnsw", label: "HNSW", desc: "高效近似搜索" },
  { value: "ivf", label: "IVF", desc: "倒排文件索引" },
  { value: "flat", label: "Flat", desc: "精确搜索" },
];

// Pipeline 配置接口
interface PipelineConfig {
  id: string;
  name: string;
  chunker: string;
  chunkSize: number;
  chunkOverlap: number;
  retriever: string;
  topK: number;
  embeddingProvider: string;
  embeddingModel: string;
  rerankProvider: string;
  vectorDb: string;
  indexType: string;
}

// 默认配置
const createDefaultConfig = (id: string, name: string): PipelineConfig => ({
  id,
  name,
  chunker: "recursive",
  chunkSize: 512,
  chunkOverlap: 50,
  retriever: "hybrid",
  topK: 5,
  embeddingProvider: "ollama",
  embeddingModel: "bge-m3",
  rerankProvider: "none",
  vectorDb: "qdrant",
  indexType: "hnsw",
});

// Ground 接口
interface Playground {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  coverId?: string;
  configs?: PipelineConfig[];
}

// 从 localStorage 获取 Playground
const getPlayground = (id: string): Playground | null => {
  if (typeof window === "undefined") return null;
  const playgrounds = JSON.parse(localStorage.getItem("playgrounds") || "[]");
  return playgrounds.find((p: Playground) => p.id === id) || null;
};

// 保存 Playground 到 localStorage
const savePlayground = (playground: Playground) => {
  const playgrounds = JSON.parse(localStorage.getItem("playgrounds") || "[]");
  const index = playgrounds.findIndex((p: Playground) => p.id === playground.id);
  if (index >= 0) {
    playgrounds[index] = playground;
  } else {
    playgrounds.push(playground);
  }
  localStorage.setItem("playgrounds", JSON.stringify(playgrounds));
};

// 结果接口
interface CompareResult {
  configId: string;
  configName: string;
  results: Array<{
    text: string;
    score: number;
    metadata?: Record<string, unknown>;
  }>;
  answer?: string;
  latency: number;
  tokenCount?: number;
}

export default function PlaygroundDetailPage() {
  const params = useParams();
  const router = useRouter();
  const playgroundId = params.id as string;
  
  const { client, isConnected, knowledgeBases, refreshKnowledgeBases } = useAppStore();
  
  const [playground, setPlayground] = useState<Playground | null>(null);
  const [configs, setConfigs] = useState<PipelineConfig[]>([
    createDefaultConfig("config-1", "配置 A"),
  ]);
  const [selectedKbIds, setSelectedKbIds] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<CompareResult[]>([]);
  const [expandedConfigs, setExpandedConfigs] = useState<Set<string>>(new Set(["config-1"]));

  // 加载 Playground
  useEffect(() => {
    const pg = getPlayground(playgroundId);
    if (pg) {
      setPlayground(pg);
      if (pg.configs && pg.configs.length > 0) {
        setConfigs(pg.configs);
        setExpandedConfigs(new Set(pg.configs.map(c => c.id)));
      }
    }
  }, [playgroundId]);

  // 加载知识库
  useEffect(() => {
    if (isConnected && client) {
      refreshKnowledgeBases();
    }
  }, [isConnected, client, refreshKnowledgeBases]);

  // 保存配置变更
  useEffect(() => {
    if (playground) {
      savePlayground({ ...playground, configs });
    }
  }, [configs, playground]);

  // 添加新配置
  const addConfig = () => {
    const id = `config-${Date.now()}`;
    const name = `配置 ${String.fromCharCode(65 + configs.length)}`;
    setConfigs([...configs, createDefaultConfig(id, name)]);
    setExpandedConfigs(new Set([...expandedConfigs, id]));
  };

  // 删除配置
  const removeConfig = (id: string) => {
    if (configs.length <= 1) {
      toast.error("至少需要保留一个配置");
      return;
    }
    setConfigs(configs.filter(c => c.id !== id));
    const newExpanded = new Set(expandedConfigs);
    newExpanded.delete(id);
    setExpandedConfigs(newExpanded);
  };

  // 更新配置
  const updateConfig = (id: string, updates: Partial<PipelineConfig>) => {
    setConfigs(configs.map(c => c.id === id ? { ...c, ...updates } : c));
  };

  // 切换展开状态
  const toggleExpand = (id: string) => {
    const newExpanded = new Set(expandedConfigs);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedConfigs(newExpanded);
  };

  // 复制配置
  const duplicateConfig = (config: PipelineConfig) => {
    const id = `config-${Date.now()}`;
    const name = `${config.name} (副本)`;
    setConfigs([...configs, { ...config, id, name }]);
    setExpandedConfigs(new Set([...expandedConfigs, id]));
  };

  // 运行对比
  const runComparison = async () => {
    if (!query.trim()) {
      toast.error("请输入查询问题");
      return;
    }
    if (selectedKbIds.length === 0) {
      toast.error("请选择知识库");
      return;
    }
    if (!client) {
      toast.error("请先连接 API");
      return;
    }

    setIsRunning(true);
    setResults([]);

    const newResults: CompareResult[] = [];

    for (const config of configs) {
      const startTime = Date.now();
      try {
        const response = await client.retrieve(query, selectedKbIds, config.topK, config.retriever);
        const latency = Date.now() - startTime;

        newResults.push({
          configId: config.id,
          configName: config.name,
          results: response.results.map(r => ({
            text: r.text,
            score: r.score,
            metadata: r.metadata,
          })),
          latency,
        });
      } catch (error) {
        newResults.push({
          configId: config.id,
          configName: config.name,
          results: [],
          latency: Date.now() - startTime,
        });
        toast.error(`${config.name} 执行失败: ${(error as Error).message}`);
      }
    }

    setResults(newResults);
    setIsRunning(false);
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* 左侧配置面板 */}
      <div className="w-80 border-r bg-muted/20 flex flex-col shrink-0">
        <div className="p-4 border-b">
          <div className="flex items-center gap-3">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => router.push("/compare")}
              className="gap-1 text-muted-foreground hover:text-foreground -ml-2 h-7 px-2"
            >
              <ChevronLeft className="h-4 w-4" />
              返回
            </Button>
            <div>
              <h1 className="text-lg font-semibold flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                {playground?.name || "Playground"}
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">
                对比不同 RAG Pipeline 配置效果
              </p>
            </div>
          </div>
        </div>

        {/* 知识库选择 */}
        <div className="p-4 border-b">
          <Label className="text-xs font-medium text-muted-foreground">知识库</Label>
          <Select
            value={selectedKbIds[0] || ""}
            onValueChange={(v) => setSelectedKbIds([v])}
          >
            <SelectTrigger className="mt-1.5 h-8 text-sm">
              <SelectValue placeholder="选择知识库" />
            </SelectTrigger>
            <SelectContent>
              {knowledgeBases.map((kb) => (
                <SelectItem key={kb.id} value={kb.id}>
                  {kb.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 配置列表 */}
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-2">
            {configs.map((config, index) => (
              <Card key={config.id} className="overflow-hidden">
                <Collapsible
                  open={expandedConfigs.has(config.id)}
                  onOpenChange={() => toggleExpand(config.id)}
                >
                  <CollapsibleTrigger asChild>
                    <CardHeader className="p-3 cursor-pointer hover:bg-muted/50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {expandedConfigs.has(config.id) ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                          <Badge
                            variant="outline"
                            className={cn(
                              "h-5 w-5 p-0 justify-center text-xs font-bold",
                              index === 0 && "bg-blue-500/10 text-blue-600 border-blue-300",
                              index === 1 && "bg-green-500/10 text-green-600 border-green-300",
                              index === 2 && "bg-purple-500/10 text-purple-600 border-purple-300",
                              index >= 3 && "bg-orange-500/10 text-orange-600 border-orange-300"
                            )}
                          >
                            {String.fromCharCode(65 + index)}
                          </Badge>
                          <Input
                            value={config.name}
                            onChange={(e) => updateConfig(config.id, { name: e.target.value })}
                            onClick={(e) => e.stopPropagation()}
                            className="h-6 text-sm font-medium border-none bg-transparent p-0 focus-visible:ring-0"
                          />
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={(e) => {
                              e.stopPropagation();
                              duplicateConfig(config);
                            }}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-destructive hover:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              removeConfig(config.id);
                            }}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <CardContent className="p-3 pt-0 space-y-4">
                      {/* 分块配置 */}
                      <div className="space-y-2">
                        <Label className="text-xs font-medium flex items-center gap-1.5 text-muted-foreground">
                          <Layers className="h-3 w-3" />
                          分块策略
                        </Label>
                        <Select
                          value={config.chunker}
                          onValueChange={(v) => updateConfig(config.id, { chunker: v })}
                        >
                          <SelectTrigger className="h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {CHUNKER_OPTIONS.map((opt) => (
                              <SelectItem key={opt.value} value={opt.value}>
                                <div className="flex flex-col">
                                  <span>{opt.label}</span>
                                  <span className="text-xs text-muted-foreground">{opt.desc}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <Label className="text-xs text-muted-foreground">块大小</Label>
                            <Input
                              type="number"
                              value={config.chunkSize}
                              onChange={(e) => updateConfig(config.id, { chunkSize: parseInt(e.target.value) || 512 })}
                              className="h-7 text-xs"
                            />
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">重叠</Label>
                            <Input
                              type="number"
                              value={config.chunkOverlap}
                              onChange={(e) => updateConfig(config.id, { chunkOverlap: parseInt(e.target.value) || 50 })}
                              className="h-7 text-xs"
                            />
                          </div>
                        </div>
                      </div>

                      <Separator />

                      {/* 检索配置 */}
                      <div className="space-y-2">
                        <Label className="text-xs font-medium flex items-center gap-1.5 text-muted-foreground">
                          <Search className="h-3 w-3" />
                          检索策略
                        </Label>
                        <Select
                          value={config.retriever}
                          onValueChange={(v) => updateConfig(config.id, { retriever: v })}
                        >
                          <SelectTrigger className="h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {RETRIEVER_OPTIONS.map((opt) => (
                              <SelectItem key={opt.value} value={opt.value}>
                                <div className="flex flex-col">
                                  <span>{opt.label}</span>
                                  <span className="text-xs text-muted-foreground">{opt.desc}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <div>
                          <Label className="text-xs text-muted-foreground">Top-K: {config.topK}</Label>
                          <Slider
                            value={[config.topK]}
                            onValueChange={([v]: number[]) => updateConfig(config.id, { topK: v })}
                            min={1}
                            max={20}
                            step={1}
                            className="mt-1"
                          />
                        </div>
                      </div>

                      <Separator />

                      {/* Embedding 配置 */}
                      <div className="space-y-2">
                        <Label className="text-xs font-medium flex items-center gap-1.5 text-muted-foreground">
                          <Brain className="h-3 w-3" />
                          Embedding
                        </Label>
                        <Select
                          value={config.embeddingProvider}
                          onValueChange={(v) => updateConfig(config.id, { 
                            embeddingProvider: v,
                            embeddingModel: EMBEDDING_MODELS[v]?.[0] || ""
                          })}
                        >
                          <SelectTrigger className="h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {EMBEDDING_PROVIDERS.map((opt) => (
                              <SelectItem key={opt.value} value={opt.value}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Select
                          value={config.embeddingModel}
                          onValueChange={(v) => updateConfig(config.id, { embeddingModel: v })}
                        >
                          <SelectTrigger className="h-8 text-xs">
                            <SelectValue placeholder="选择模型" />
                          </SelectTrigger>
                          <SelectContent>
                            {(EMBEDDING_MODELS[config.embeddingProvider] || []).map((model) => (
                              <SelectItem key={model} value={model}>
                                {model}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <Separator />

                      {/* Rerank 配置 */}
                      <div className="space-y-2">
                        <Label className="text-xs font-medium flex items-center gap-1.5 text-muted-foreground">
                          <BarChart3 className="h-3 w-3" />
                          Rerank
                        </Label>
                        <Select
                          value={config.rerankProvider}
                          onValueChange={(v) => updateConfig(config.id, { rerankProvider: v })}
                        >
                          <SelectTrigger className="h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {RERANK_PROVIDERS.map((opt) => (
                              <SelectItem key={opt.value} value={opt.value}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <Separator />

                      {/* 向量数据库配置 */}
                      <div className="space-y-2">
                        <Label className="text-xs font-medium flex items-center gap-1.5 text-muted-foreground">
                          <Database className="h-3 w-3" />
                          向量数据库
                        </Label>
                        <div className="grid grid-cols-2 gap-2">
                          <Select
                            value={config.vectorDb}
                            onValueChange={(v) => updateConfig(config.id, { vectorDb: v })}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {VECTOR_DB_OPTIONS.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>
                                  {opt.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Select
                            value={config.indexType}
                            onValueChange={(v) => updateConfig(config.id, { indexType: v })}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {INDEX_TYPE_OPTIONS.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>
                                  {opt.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </CardContent>
                  </CollapsibleContent>
                </Collapsible>
              </Card>
            ))}

            {/* 添加配置按钮 */}
            <Button
              variant="outline"
              className="w-full h-9 text-sm border-dashed"
              onClick={addConfig}
            >
              <Plus className="h-4 w-4 mr-1" />
              添加配置
            </Button>
          </div>
        </ScrollArea>
      </div>

      {/* 右侧主内容区 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 查询输入区 */}
        <div className="p-4 border-b bg-background">
          <div className="flex gap-3">
            <Textarea
              placeholder="输入查询问题，对比不同 RAG 配置的检索结果..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="min-h-[80px] resize-none flex-1"
            />
            <Button
              onClick={runComparison}
              disabled={isRunning || !isConnected}
              className="h-auto px-6"
            >
              {isRunning ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <Play className="h-5 w-5 mr-2" />
                  运行对比
                </>
              )}
            </Button>
          </div>
        </div>

        {/* 结果对比区 */}
        <ScrollArea className="flex-1 p-4">
          {results.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <Settings2 className="h-16 w-16 mb-4 opacity-20" />
              <p className="text-lg font-medium">配置 Pipeline 并运行对比</p>
              <p className="text-sm mt-1">
                在左侧配置不同的 RAG 参数，输入查询问题后点击运行对比
              </p>
            </div>
          ) : (
            <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${results.length}, 1fr)` }}>
              {results.map((result, index) => (
                <Card key={result.configId} className="overflow-hidden">
                  <CardHeader className="p-3 bg-muted/30">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={cn(
                            "h-5 w-5 p-0 justify-center text-xs font-bold",
                            index === 0 && "bg-blue-500/10 text-blue-600 border-blue-300",
                            index === 1 && "bg-green-500/10 text-green-600 border-green-300",
                            index === 2 && "bg-purple-500/10 text-purple-600 border-purple-300",
                            index >= 3 && "bg-orange-500/10 text-orange-600 border-orange-300"
                          )}
                        >
                          {String.fromCharCode(65 + index)}
                        </Badge>
                        <span className="font-medium text-sm">{result.configName}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {result.latency}ms
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="p-3 space-y-2">
                    {result.results.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground text-sm">
                        无结果
                      </div>
                    ) : (
                      result.results.map((r, i) => (
                        <div key={i} className="p-2 rounded bg-muted/30 text-sm">
                          <div className="flex items-center justify-between mb-1">
                            <Badge variant="secondary" className="text-xs">
                              #{i + 1}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              相关度: {(r.score * 100).toFixed(1)}%
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground line-clamp-3">
                            {r.text}
                          </p>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}
