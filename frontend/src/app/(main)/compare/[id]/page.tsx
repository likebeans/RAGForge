"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
  DialogDescription,
} from "@/components/ui/dialog";
import {
  OperatorListResponse,
  PlaygroundRunRequest,
  PlaygroundRunResponse,
  GroundInfo,
  ChunkPreviewItem,
  KnowledgeBase,
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
  Layers,
  Sparkles,
  Database,
  Eye,
  Plus,
  X,
  CheckCircle2,
  XCircle,
  Circle,
} from "lucide-react";
import { AllModelsSelector } from "@/components/settings";
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

// 检索器参数 UI 配置
type RetrieverConfig = {
  label: string;
  description: string;
  params: ParamConfig[];
};

// 根据检索器类型获取评分标签
function getScoreLabel(retrieverType: string, reranked?: boolean): string {
  if (reranked) return "重排分数";
  switch (retrieverType) {
    case "dense":
    case "llama_dense":
    case "hyde":
      return "向量相似度";
    case "bm25":
    case "llama_bm25":
      return "BM25 分数";
    case "hybrid":
    case "llama_hybrid":
    case "fusion":
      return "混合分数";
    case "parent_document":
      return "子块匹配度";
    case "multi_query":
      return "多查询分数";
    default:
      return "相关度";
  }
}

// 判断是否为父子检索结果（有 parent_id 或 context_text）
function isParentChildResult(hit: { metadata?: Record<string, unknown>; context_text?: string | null }): boolean {
  const meta = hit.metadata || {};
  return !!(meta.parent_id || meta.child || hit.context_text);
}

const RETRIEVER_UI_CONFIG: Record<string, RetrieverConfig> = {
  dense: {
    label: '向量检索',
    description: '基于语义相似度的稠密向量检索',
    params: []
  },
  bm25: {
    label: 'BM25 检索',
    description: '基于关键词匹配的稀疏检索',
    params: []
  },
  hybrid: {
    label: '混合检索',
    description: '向量 + BM25 加权融合',
    params: [
      { key: 'dense_weight', label: '向量权重', type: 'slider', default: 0.7, min: 0, max: 1, step: 0.1 },
      { key: 'sparse_weight', label: 'BM25 权重', type: 'slider', default: 0.3, min: 0, max: 1, step: 0.1 }
    ]
  },
  fusion: {
    label: '融合检索',
    description: 'RRF/加权融合 + 可选 Rerank',
    params: [
      { key: 'mode', label: '融合模式', type: 'select', default: 'rrf', options: ['rrf', 'weighted'] },
      { key: 'rrf_k', label: 'RRF 常数', type: 'number', default: 60, min: 1, max: 100,
        showWhen: { mode: 'rrf' }, description: '论文推荐值 60' },
      { key: 'dense_weight', label: '向量权重', type: 'slider', default: 0.7, min: 0, max: 1, step: 0.1,
        showWhen: { mode: 'weighted' } },
      { key: 'sparse_weight', label: 'BM25 权重', type: 'slider', default: 0.3, min: 0, max: 1, step: 0.1,
        showWhen: { mode: 'weighted' } },
      { key: 'rerank', label: '启用 Rerank', type: 'boolean', default: false, group: 'Rerank 设置' },
      { key: 'rerank_top_n', label: 'Rerank 数量', type: 'number', default: 10, min: 1, max: 50,
        group: 'Rerank 设置', showWhen: { rerank: true } }
    ]
  },
  hyde: {
    label: 'HyDE 检索',
    description: 'LLM 生成假设答案进行检索',
    params: [
      { key: 'base_retriever', label: '底层检索器', type: 'select', default: 'dense',
        options: ['dense', 'hybrid', 'bm25'] },
      { key: 'num_queries', label: '假设答案数', type: 'number', default: 4, min: 1, max: 10,
        description: '生成的假设答案数量' },
      { key: 'include_original', label: '保留原始查询', type: 'boolean', default: true }
    ]
  },
  multi_query: {
    label: '多查询检索',
    description: 'LLM 生成查询变体，多路召回',
    params: [
      { key: 'base_retriever', label: '底层检索器', type: 'select', default: 'dense',
        options: ['dense', 'hybrid', 'bm25'] },
      { key: 'num_queries', label: '查询变体数', type: 'number', default: 3, min: 1, max: 10,
        description: '生成的查询变体数量' },
      { key: 'include_original', label: '保留原始查询', type: 'boolean', default: true },
      { key: 'rrf_k', label: 'RRF 融合常数', type: 'number', default: 60, min: 1, max: 100 }
    ]
  },
  parent_document: {
    label: '父文档检索',
    description: '子块检索返回父块上下文，需配合 parent_child 切分器',
    params: [
      { key: 'base_retriever', label: '底层检索器', type: 'select', default: 'dense',
        options: ['dense', 'hybrid', 'bm25'] },
      { key: 'return_parent', label: '返回父块', type: 'boolean', default: true },
      { key: 'include_child', label: '包含子块信息', type: 'boolean', default: false }
    ]
  },
  llama_dense: {
    label: 'LlamaIndex 向量检索',
    description: '支持多向量存储后端',
    params: [
      { key: 'store_type', label: '存储类型', type: 'select', default: 'qdrant',
        options: ['qdrant', 'milvus', 'es'] }
    ]
  },
  llama_hybrid: {
    label: 'LlamaIndex 混合检索',
    description: 'Dense + BM25 混合',
    params: [
      { key: 'dense_weight', label: '向量权重', type: 'slider', default: 0.7, min: 0, max: 1, step: 0.1 },
      { key: 'bm25_weight', label: 'BM25 权重', type: 'slider', default: 0.3, min: 0, max: 1, step: 0.1 }
    ]
  }
};

// 索引增强配置（索引方法 + 上下文增强）
type IndexerConfig = {
  label: string;
  description: string;
  params: ParamConfig[];
};

const INDEXER_UI_CONFIG: Record<string, IndexerConfig> = {
  standard: {
    label: '标准向量索引',
    description: '直接将切分后的 chunks 向量化存储',
    params: []
  },
  raptor: {
    label: 'RAPTOR 树索引',
    description: '递归聚类生成摘要树，支持多层次检索',
    params: [
      { key: 'max_levels', label: '最大层数', type: 'number', default: 3, min: 1, max: 5,
        description: '摘要树的最大层数' },
      { key: 'max_clusters', label: '最大聚类数', type: 'number', default: 10, min: 2, max: 50,
        description: '每层的最大聚类数量' },
      { key: 'retrieval_mode', label: '检索模式', type: 'select', default: 'collapsed',
        options: ['collapsed', 'tree_traversal'],
        description: 'collapsed=扁平检索, tree_traversal=树遍历' }
    ]
  }
};

// 上下文增强配置
type EnricherConfig = {
  label: string;
  description: string;
  params: ParamConfig[];
};

const ENRICHER_UI_CONFIG: Record<string, EnricherConfig> = {
  none: {
    label: '无增强',
    description: '不对 chunks 进行额外增强处理',
    params: []
  },
  chunk_context: {
    label: '块上下文增强',
    description: '为每个 chunk 添加周围上下文信息',
    params: [
      { key: 'window_size', label: '上下文窗口', type: 'number', default: 2, min: 1, max: 5,
        description: '前后各包含多少个相邻块的信息' },
      { key: 'include_headers', label: '包含标题', type: 'boolean', default: true,
        description: '是否在上下文中包含文档标题/章节信息' }
    ]
  },
  document_summary: {
    label: '文档摘要增强',
    description: '使用 LLM 生成文档摘要，附加到每个 chunk',
    params: [
      { key: 'summary_length', label: '摘要长度', type: 'select', default: 'medium',
        options: ['short', 'medium', 'long'], description: '生成摘要的目标长度' },
      { key: 'prepend_summary', label: '前置摘要', type: 'boolean', default: true,
        description: '是否将摘要添加到每个 chunk 开头' }
    ]
  }
};

// 获取索引器默认参数
function getDefaultIndexerParams(indexerName: string): Record<string, unknown> {
  const config = INDEXER_UI_CONFIG[indexerName];
  if (!config) return {};
  const params: Record<string, unknown> = {};
  for (const p of config.params) {
    params[p.key] = p.default;
  }
  return params;
}

// 获取增强器默认参数
function getDefaultEnricherParams(enricherName: string): Record<string, unknown> {
  const config = ENRICHER_UI_CONFIG[enricherName];
  if (!config) return {};
  const params: Record<string, unknown> = {};
  for (const p of config.params) {
    params[p.key] = p.default;
  }
  return params;
}

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

// 获取检索器默认参数
function getDefaultRetrieverParams(retrieverName: string): Record<string, unknown> {
  const config = RETRIEVER_UI_CONFIG[retrieverName];
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
    setDefaultModel,
    providerConfigs,
    providerCatalog,
    setProviderCatalog,
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
  const [results, setResults] = useState<{ current?: PlaygroundRunResponse }>({});
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
  // 预览类型: 'result' | 'chunk' | 'enrich' | 'retrieval'
  const [previewType, setPreviewType] = useState<"result" | "chunk" | "enrich" | "retrieval">("result");
  // 检索器设置状态
  const [selectedRetriever, setSelectedRetriever] = useState("hybrid");
  const [retrieverParams, setRetrieverParams] = useState<Record<string, unknown>>(
    getDefaultRetrieverParams("hybrid")
  );
  const [topK, setTopK] = useState(5);
  // 索引增强设置状态
  const [selectedIndexer, setSelectedIndexer] = useState("standard");
  const [indexerParams, setIndexerParams] = useState<Record<string, unknown>>(
    getDefaultIndexerParams("standard")
  );
  const [selectedEnricher, setSelectedEnricher] = useState("none");
  const [enricherParams, setEnricherParams] = useState<Record<string, unknown>>(
    getDefaultEnricherParams("none")
  );
  // Embedding 模型配置
  const [embedProvider, setEmbedProvider] = useState(defaultModels.embedding?.provider || "");
  const [embedModel, setEmbedModel] = useState(defaultModels.embedding?.model || "");
  // 入库 Dialog 状态
  const [ingestDialogOpen, setIngestDialogOpen] = useState(false);
  const [newKbName, setNewKbName] = useState("");
  const [newKbDesc, setNewKbDesc] = useState("");
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestProgress, setIngestProgress] = useState<{
    step: number;
    steps: { label: string; status: 'pending' | 'running' | 'done' | 'error' }[];
  } | null>(null);
  // 入库后的知识库状态（用于检索）
  const [ingestedKbId, setIngestedKbId] = useState<string | null>(null);
  const [ingestedKbName, setIngestedKbName] = useState<string>("");
  // 入库时的配置快照（用于检测配置变更）
  const [ingestedConfig, setIngestedConfig] = useState<{
    chunker: string;
    chunkerParams: Record<string, unknown>;
    indexer: string;
    indexerParams: Record<string, unknown>;
    enricher: string;
    enricherParams: Record<string, unknown>;
  } | null>(null);
  // 知识库选择器 Dialog 状态
  const [kbSelectorOpen, setKbSelectorOpen] = useState(false);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [isLoadingKbs, setIsLoadingKbs] = useState(false);
  // 增强预览状态
  const [isPreviewingEnrich, setIsPreviewingEnrich] = useState(false);
  const [enrichPreviewStep, setEnrichPreviewStep] = useState<string>(""); // 当前处理步骤
  const [summaryPreview, setSummaryPreview] = useState<string | null>(null);
  const [chunkEnrichPreview, setChunkEnrichPreview] = useState<Array<{ original: string; enriched: string }>>([]);
  // 检索结果详情 Dialog 状态
  const [chunkDetailOpen, setChunkDetailOpen] = useState(false);
  const [selectedChunkHit, setSelectedChunkHit] = useState<{
    hit: PlaygroundRunResponse["retrieval"]["results"][0];
    index: number;
    retrieverType: string;
  } | null>(null);
  
  // Pipeline 配置类型（最多4个）
  type PipelineConfig = {
    id: string;
    name: string; // 显示名称: "1", "2", "3", "4"
    // 分段配置
    chunker: string;
    chunkerParams: Record<string, unknown>;
    // 索引配置
    indexer: string;
    indexerParams: Record<string, unknown>;
    // 增强配置
    enricher: string;
    enricherParams: Record<string, unknown>;
    // 检索配置
    retriever: string;
    retrieverParams: Record<string, unknown>;
    topK: number;
    // 模型配置
    embedProvider: string;
    embedModel: string;
    // 入库状态
    ingestedKbId: string | null;
    ingestedKbName: string;
    isIngesting: boolean;
  };

  // 检索对比状态（最多4个槽位）
  type CompareSlot = {
    id: string;
    kbId: string | null;
    kbName: string;
    retriever: string;
    retrieverParams: Record<string, unknown>;
    topK: number;
    results: PlaygroundRunResponse["retrieval"]["results"] | null;
    isLoading: boolean;
    error: string | null;
  };
  const [compareQuery, setCompareQuery] = useState("");
  const [compareSlots, setCompareSlots] = useState<CompareSlot[]>([
    { id: "slot-1", kbId: null, kbName: "", retriever: "hybrid", retrieverParams: getDefaultRetrieverParams("hybrid"), topK: 5, results: null, isLoading: false, error: null },
    { id: "slot-2", kbId: null, kbName: "", retriever: "dense", retrieverParams: getDefaultRetrieverParams("dense"), topK: 5, results: null, isLoading: false, error: null },
  ]);
  const [compareKbSelectorOpen, setCompareKbSelectorOpen] = useState(false);
  const [compareKbSelectorSlotIndex, setCompareKbSelectorSlotIndex] = useState<number>(0);
  const [isComparingAll, setIsComparingAll] = useState(false);

  // Pipeline 状态管理（最多4个）
  const createDefaultPipeline = (index: number): PipelineConfig => ({
    id: `pipeline-${index}`,
    name: String(index + 1),
    chunker: "recursive",
    chunkerParams: getDefaultChunkerParams("recursive"),
    indexer: "standard",
    indexerParams: getDefaultIndexerParams("standard"),
    enricher: "none",
    enricherParams: getDefaultEnricherParams("none"),
    retriever: "hybrid",
    retrieverParams: getDefaultRetrieverParams("hybrid"),
    topK: 5,
    embedProvider: defaultModels.embedding?.provider || "",
    embedModel: defaultModels.embedding?.model || "",
    ingestedKbId: null,
    ingestedKbName: "",
    isIngesting: false,
  });
  
  const [pipelines, setPipelines] = useState<PipelineConfig[]>([createDefaultPipeline(0)]);
  const [currentPipelineIndex, setCurrentPipelineIndex] = useState(0);
  const [pipelinesLoaded, setPipelinesLoaded] = useState(false);
  
  // localStorage key for pipelines
  const pipelinesStorageKey = `ground_pipelines_${groundId}`;
  
  // 从 localStorage 加载 Pipeline 配置
  useEffect(() => {
    if (!groundId || pipelinesLoaded) return;
    try {
      const saved = localStorage.getItem(pipelinesStorageKey);
      if (saved) {
        const savedPipelines = JSON.parse(saved) as PipelineConfig[];
        if (savedPipelines.length > 0) {
          setPipelines(savedPipelines);
          // 恢复第一个 Pipeline 的配置到 UI
          const firstPipeline = savedPipelines[0];
          setSelectedChunker(firstPipeline.chunker);
          setChunkerParams(firstPipeline.chunkerParams);
          setSelectedIndexer(firstPipeline.indexer);
          setIndexerParams(firstPipeline.indexerParams);
          setSelectedEnricher(firstPipeline.enricher);
          setEnricherParams(firstPipeline.enricherParams);
          setSelectedRetriever(firstPipeline.retriever);
          setRetrieverParams(firstPipeline.retrieverParams);
          setTopK(firstPipeline.topK);
          setEmbedProvider(firstPipeline.embedProvider);
          setEmbedModel(firstPipeline.embedModel);
        }
      }
    } catch (e) {
      console.error("Failed to load pipelines from localStorage:", e);
    }
    setPipelinesLoaded(true);
  }, [groundId, pipelinesLoaded]);
  
  // 保存 Pipeline 配置到 localStorage
  useEffect(() => {
    if (!groundId || !pipelinesLoaded) return;
    try {
      localStorage.setItem(pipelinesStorageKey, JSON.stringify(pipelines));
    } catch (e) {
      console.error("Failed to save pipelines to localStorage:", e);
    }
  }, [pipelines, groundId, pipelinesLoaded, pipelinesStorageKey]);
  
  // 实时同步 UI 状态到当前 Pipeline（当用户修改配置时自动保存）
  useEffect(() => {
    if (!pipelinesLoaded) return;
    setPipelines(prev => prev.map((p, i) => 
      i === currentPipelineIndex ? {
        ...p,
        chunker: selectedChunker,
        chunkerParams: chunkerParams,
        indexer: selectedIndexer,
        indexerParams: indexerParams,
        enricher: selectedEnricher,
        enricherParams: enricherParams,
        retriever: selectedRetriever,
        retrieverParams: retrieverParams,
        topK: topK,
        embedProvider: embedProvider,
        embedModel: embedModel,
      } : p
    ));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    selectedChunker, chunkerParams,
    selectedIndexer, indexerParams,
    selectedEnricher, enricherParams,
    selectedRetriever, retrieverParams,
    topK, embedProvider, embedModel,
    currentPipelineIndex, pipelinesLoaded
  ]);
  
  // 获取当前 Pipeline
  const currentPipeline = pipelines[currentPipelineIndex];
  
  // 更新当前 Pipeline 配置
  const updateCurrentPipeline = (updates: Partial<PipelineConfig>) => {
    setPipelines(prev => prev.map((p, i) => 
      i === currentPipelineIndex ? { ...p, ...updates } : p
    ));
  };
  
  // 添加新 Pipeline
  const addPipeline = () => {
    if (pipelines.length >= 4) {
      toast.error("最多只能创建 4 个 Pipeline");
      return;
    }
    const newPipeline = createDefaultPipeline(pipelines.length);
    setPipelines(prev => [...prev, newPipeline]);
    setCurrentPipelineIndex(pipelines.length);
    toast.success(`已创建 Pipeline ${pipelines.length + 1}`);
  };
  
  // 删除 Pipeline
  const deletePipeline = (index: number) => {
    if (pipelines.length <= 1) {
      toast.error("至少需要保留一个 Pipeline");
      return;
    }
    setPipelines(prev => {
      const newPipelines = prev.filter((_, i) => i !== index);
      // 重新编号
      return newPipelines.map((p, i) => ({ ...p, id: `pipeline-${i}`, name: String(i + 1) }));
    });
    // 调整当前索引
    if (currentPipelineIndex >= index && currentPipelineIndex > 0) {
      setCurrentPipelineIndex(currentPipelineIndex - 1);
    }
    toast.success("已删除 Pipeline");
  };
  
  // 切换 Pipeline 时同步 UI 状态
  const switchPipeline = (index: number) => {
    if (index === currentPipelineIndex) return;
    // 保存当前配置到当前 Pipeline
    updateCurrentPipeline({
      chunker: selectedChunker,
      chunkerParams: chunkerParams,
      indexer: selectedIndexer,
      indexerParams: indexerParams,
      enricher: selectedEnricher,
      enricherParams: enricherParams,
      retriever: selectedRetriever,
      retrieverParams: retrieverParams,
      topK: topK,
      embedProvider: embedProvider,
      embedModel: embedModel,
    });
    // 切换到目标 Pipeline
    setCurrentPipelineIndex(index);
    // 恢复目标 Pipeline 的配置到 UI
    const targetPipeline = pipelines[index];
    setSelectedChunker(targetPipeline.chunker);
    setChunkerParams(targetPipeline.chunkerParams);
    setSelectedIndexer(targetPipeline.indexer);
    setIndexerParams(targetPipeline.indexerParams);
    setSelectedEnricher(targetPipeline.enricher);
    setEnricherParams(targetPipeline.enricherParams);
    setSelectedRetriever(targetPipeline.retriever);
    setRetrieverParams(targetPipeline.retrieverParams);
    setTopK(targetPipeline.topK);
    setEmbedProvider(targetPipeline.embedProvider);
    setEmbedModel(targetPipeline.embedModel);
  };
  
  // 获取所有已入库的知识库 ID
  const getIngestedKbIds = () => {
    return pipelines
      .filter(p => p.ingestedKbId)
      .map(p => p.ingestedKbId as string);
  };

  const retrieverOptions = useMemo(() => operators?.retrievers || [], [operators]);
  const chunkerOptions = useMemo(() => operators?.chunkers || [], [operators]);
  
  // 根据分段设置和索引设置过滤可用的检索器
  const filteredRetrieverOptions = useMemo(() => {
    return retrieverOptions.filter((r) => {
      // parent_document 检索器只在使用 parent_child 切分器时可用
      if (r.name === 'parent_document' && selectedChunker !== 'parent_child') {
        return false;
      }
      // raptor 检索器只在使用 raptor 索引器时可用
      if (r.name === 'raptor' && selectedIndexer !== 'raptor') {
        return false;
      }
      // llama_dense/llama_bm25/llama_hybrid 需要特定存储后端配置，暂时保留
      return true;
    });
  }, [retrieverOptions, selectedChunker, selectedIndexer]);
  
  // 记录上一次的 chunker/indexer，用于检测变化
  const prevChunkerRef = useRef(selectedChunker);
  const prevIndexerRef = useRef(selectedIndexer);
  
  // 智能联动：当 chunker/indexer 变化时，自动推荐匹配的检索器
  useEffect(() => {
    const chunkerChanged = prevChunkerRef.current !== selectedChunker;
    const indexerChanged = prevIndexerRef.current !== selectedIndexer;
    
    // 更新 ref
    prevChunkerRef.current = selectedChunker;
    prevIndexerRef.current = selectedIndexer;
    
    // 只在 chunker 或 indexer 真正变化时才触发联动
    if (!chunkerChanged && !indexerChanged) return;
    
    let recommendedRetriever: string | null = null;
    
    // parent_child 切分器 -> parent_document 检索器
    if (chunkerChanged && selectedChunker === 'parent_child') {
      recommendedRetriever = 'parent_document';
    }
    // raptor 索引器 -> raptor 检索器
    if (indexerChanged && selectedIndexer === 'raptor') {
      recommendedRetriever = 'raptor';
    }
    
    if (recommendedRetriever && filteredRetrieverOptions.some(r => r.name === recommendedRetriever)) {
      const oldLabel = RETRIEVER_UI_CONFIG[selectedRetriever]?.label || selectedRetriever;
      const newLabel = RETRIEVER_UI_CONFIG[recommendedRetriever]?.label || recommendedRetriever;
      setSelectedRetriever(recommendedRetriever);
      setRetrieverParams(getDefaultRetrieverParams(recommendedRetriever));
      toast.info(`已自动切换检索器: "${oldLabel}" → "${newLabel}"`);
    }
  }, [selectedChunker, selectedIndexer, filteredRetrieverOptions]);
  
  // 当设置变化导致当前检索器不可用时，自动切换到默认检索器
  useEffect(() => {
    const isCurrentRetrieverAvailable = filteredRetrieverOptions.some(r => r.name === selectedRetriever);
    
    if (!isCurrentRetrieverAvailable && filteredRetrieverOptions.length > 0) {
      // 优先选择 hybrid，否则选第一个可用的
      const defaultRetriever = filteredRetrieverOptions.find(r => r.name === 'hybrid') || filteredRetrieverOptions[0];
      const oldLabel = RETRIEVER_UI_CONFIG[selectedRetriever]?.label || selectedRetriever;
      const newLabel = RETRIEVER_UI_CONFIG[defaultRetriever.name]?.label || defaultRetriever.name;
      setSelectedRetriever(defaultRetriever.name);
      setRetrieverParams(getDefaultRetrieverParams(defaultRetriever.name));
      toast.info(`"${oldLabel}" 不适用于当前配置，已切换为 "${newLabel}"`);
    }
  }, [filteredRetrieverOptions]);

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

  // ========== localStorage 持久化设置 ==========
  const STORAGE_KEY = `ground-settings-${groundId}`;
  const isInitializedRef = useRef(false);

  // 从 localStorage 恢复设置（仅在初始化时执行一次）
  useEffect(() => {
    if (!groundId || isInitializedRef.current) return;
    
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const settings = JSON.parse(saved);
        // 恢复分段设置
        if (settings.chunker) {
          setSelectedChunker(settings.chunker);
          setChunkerParams(settings.chunkerParams || getDefaultChunkerParams(settings.chunker));
        }
        // 恢复检索设置
        if (settings.retriever) {
          setSelectedRetriever(settings.retriever);
          setRetrieverParams(settings.retrieverParams || getDefaultRetrieverParams(settings.retriever));
        }
        if (settings.topK) setTopK(settings.topK);
        // 恢复增强设置
        if (settings.enricher) {
          setSelectedEnricher(settings.enricher);
          setEnricherParams(settings.enricherParams || getDefaultEnricherParams(settings.enricher));
        }
        // 恢复索引设置
        if (settings.indexer) {
          setSelectedIndexer(settings.indexer);
          setIndexerParams(settings.indexerParams || getDefaultIndexerParams(settings.indexer));
        }
        // 恢复 Embedding 模型
        if (settings.embedProvider) setEmbedProvider(settings.embedProvider);
        if (settings.embedModel) setEmbedModel(settings.embedModel);
        // 恢复选中的文档
        if (settings.selectedDocId) setSelectedDocId(settings.selectedDocId);
        // 恢复入库状态
        if (settings.ingestedKbId) {
          setIngestedKbId(settings.ingestedKbId);
          setIngestedKbName(settings.ingestedKbName || "");
        }
        
        console.log("[Ground] 已从本地缓存恢复设置");
      }
    } catch (e) {
      console.warn("[Ground] 恢复本地设置失败:", e);
    }
    isInitializedRef.current = true;
  }, [groundId]);

  // 保存设置到 localStorage（设置变化时自动保存）
  useEffect(() => {
    if (!groundId || !isInitializedRef.current) return;
    
    const settings = {
      chunker: selectedChunker,
      chunkerParams,
      retriever: selectedRetriever,
      retrieverParams,
      topK,
      enricher: selectedEnricher,
      enricherParams,
      indexer: selectedIndexer,
      indexerParams,
      embedProvider,
      embedModel,
      selectedDocId,
      ingestedKbId,
      ingestedKbName,
      savedAt: Date.now(),
    };
    
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (e) {
      console.warn("[Ground] 保存本地设置失败:", e);
    }
  }, [
    groundId,
    selectedChunker,
    chunkerParams,
    selectedRetriever,
    retrieverParams,
    topK,
    selectedEnricher,
    enricherParams,
    selectedIndexer,
    indexerParams,
    embedProvider,
    embedModel,
    selectedDocId,
    ingestedKbId,
    ingestedKbName,
  ]);

  // 配置变更检测：当分段或索引设置改变时，清除入库状态
  useEffect(() => {
    if (!ingestedConfig || !ingestedKbId) return;
    
    // 比较当前配置与入库时的配置
    const hasChanged = 
      ingestedConfig.chunker !== selectedChunker ||
      JSON.stringify(ingestedConfig.chunkerParams) !== JSON.stringify(chunkerParams) ||
      ingestedConfig.indexer !== selectedIndexer ||
      JSON.stringify(ingestedConfig.indexerParams) !== JSON.stringify(indexerParams) ||
      ingestedConfig.enricher !== selectedEnricher ||
      JSON.stringify(ingestedConfig.enricherParams) !== JSON.stringify(enricherParams);
    
    if (hasChanged) {
      toast.warning(`配置已变更，需要重新入库`, { duration: 3000 });
      setIngestedKbId(null);
      setIngestedKbName("");
      setIngestedConfig(null);
    }
  }, [selectedChunker, chunkerParams, selectedIndexer, indexerParams, selectedEnricher, enricherParams]);

  // 加载知识库列表
  const loadKnowledgeBases = async () => {
    if (!client) return;
    setIsLoadingKbs(true);
    try {
      const res = await client.listKnowledgeBases();
      setKnowledgeBases(res.items);
    } catch (error) {
      console.error("加载知识库列表失败:", error);
    } finally {
      setIsLoadingKbs(false);
    }
  };

  // 选择已有知识库
  const handleSelectKnowledgeBase = (kb: KnowledgeBase) => {
    setIngestedKbId(kb.id);
    setIngestedKbName(kb.name);
    // 设置配置快照（使用当前配置）
    setIngestedConfig({
      chunker: selectedChunker,
      chunkerParams,
      indexer: selectedIndexer,
      indexerParams,
      enricher: selectedEnricher,
      enricherParams,
    });
    setKbSelectorOpen(false);
    toast.success(`已选择知识库: ${kb.name}`);
  };

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

  // 检索器切换时重置参数
  const handleRetrieverChange = (newRetriever: string) => {
    setSelectedRetriever(newRetriever);
    setRetrieverParams(getDefaultRetrieverParams(newRetriever));
  };

  // 更新检索器参数
  const updateRetrieverParam = (key: string, value: unknown) => {
    setRetrieverParams(prev => ({ ...prev, [key]: value }));
  };

  // 检查检索器参数是否应该显示
  const shouldShowRetrieverParam = (param: ParamConfig): boolean => {
    if (!param.showWhen) return true;
    return Object.entries(param.showWhen).every(
      ([key, expected]) => retrieverParams[key] === expected
    );
  };

  // 渲染检索器参数输入控件
  const renderRetrieverParamInput = (param: ParamConfig) => {
    const value = retrieverParams[param.key] ?? param.default;
    
    switch (param.type) {
      case 'number':
        return (
          <Input
            type="number"
            min={param.min}
            max={param.max}
            value={value as number}
            onChange={(e) => updateRetrieverParam(param.key, Number(e.target.value))}
            className="h-8"
          />
        );
      case 'boolean':
        return (
          <Switch
            checked={value as boolean}
            onCheckedChange={(checked) => updateRetrieverParam(param.key, checked)}
          />
        );
      case 'select':
        return (
          <Select value={value as string} onValueChange={(v) => updateRetrieverParam(param.key, v)}>
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
              onValueChange={([v]) => updateRetrieverParam(param.key, v)}
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
            onChange={(e) => updateRetrieverParam(param.key, e.target.value)}
            className="h-8"
            placeholder={param.description}
          />
        );
      default:
        return null;
    }
  };

  // 渲染检索器参数（按分组）
  const renderRetrieverParams = () => {
    const config = RETRIEVER_UI_CONFIG[selectedRetriever];
    if (!config || config.params.length === 0) {
      return (
        <div className="text-xs text-muted-foreground py-2">
          该检索器无需配置参数
        </div>
      );
    }
    
    // 收集分组
    const groups: Record<string, ParamConfig[]> = {};
    const ungrouped: ParamConfig[] = [];
    
    config.params.forEach(p => {
      if (!shouldShowRetrieverParam(p)) return;
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
              {param.type === 'boolean' && renderRetrieverParamInput(param)}
            </div>
            {param.description && param.type !== 'text' && (
              <p className="text-xs text-muted-foreground">{param.description}</p>
            )}
            {param.type !== 'boolean' && renderRetrieverParamInput(param)}
          </div>
        ))}
        
        {/* 分组参数 */}
        {Object.entries(groups).map(([groupName, params]) => (
          <div key={groupName} className="space-y-2 pt-2 border-t border-primary/10">
            <Label className="text-xs font-semibold text-muted-foreground">{groupName}</Label>
            {params.map((param) => (
              <div key={param.key} className="space-y-1">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">{param.label}</Label>
                  {param.type === 'boolean' && renderRetrieverParamInput(param)}
                </div>
                {param.description && param.type !== 'text' && (
                  <p className="text-xs text-muted-foreground">{param.description}</p>
                )}
                {param.type !== 'boolean' && renderRetrieverParamInput(param)}
              </div>
            ))}
          </div>
        ))}
      </>
    );
  };

  // 索引器切换时重置参数
  const handleIndexerChange = (newIndexer: string) => {
    setSelectedIndexer(newIndexer);
    setIndexerParams(getDefaultIndexerParams(newIndexer));
  };

  // 更新索引器参数
  const updateIndexerParam = (key: string, value: unknown) => {
    setIndexerParams(prev => ({ ...prev, [key]: value }));
  };

  // 增强器切换时重置参数
  const handleEnricherChange = (newEnricher: string) => {
    setSelectedEnricher(newEnricher);
    setEnricherParams(getDefaultEnricherParams(newEnricher));
  };

  // 更新增强器参数
  const updateEnricherParam = (key: string, value: unknown) => {
    setEnricherParams(prev => ({ ...prev, [key]: value }));
  };

  // 渲染通用参数输入控件（带自定义 onChange）
  const renderGenericParamInput = (
    param: ParamConfig,
    value: unknown,
    onChange: (key: string, value: unknown) => void
  ) => {
    const currentValue = value ?? param.default;
    
    switch (param.type) {
      case 'number':
        return (
          <Input
            type="number"
            min={param.min}
            max={param.max}
            value={currentValue as number}
            onChange={(e) => onChange(param.key, Number(e.target.value))}
            className="h-8"
          />
        );
      case 'boolean':
        return (
          <Switch
            checked={currentValue as boolean}
            onCheckedChange={(checked) => onChange(param.key, checked)}
          />
        );
      case 'select':
        return (
          <Select value={currentValue as string} onValueChange={(v) => onChange(param.key, v)}>
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
              value={[currentValue as number]}
              min={param.min}
              max={param.max}
              step={param.step || 0.1}
              onValueChange={([v]) => onChange(param.key, v)}
              className="flex-1"
            />
            <span className="text-sm w-12 text-right">{(currentValue as number).toFixed(1)}</span>
          </div>
        );
      default:
        return null;
    }
  };

  // 渲染索引器参数
  const renderIndexerParams = () => {
    const config = INDEXER_UI_CONFIG[selectedIndexer];
    if (!config || config.params.length === 0) {
      return null;
    }
    
    return (
      <div className="space-y-3 pt-2 border-t border-purple-500/10">
        {config.params.map((param) => (
          <div key={param.key} className="space-y-1">
            <div className="flex items-center justify-between">
              <Label className="text-xs">{param.label}</Label>
              {param.type === 'boolean' && renderGenericParamInput(param, indexerParams[param.key], updateIndexerParam)}
            </div>
            {param.description && (
              <p className="text-xs text-muted-foreground">{param.description}</p>
            )}
            {param.type !== 'boolean' && renderGenericParamInput(param, indexerParams[param.key], updateIndexerParam)}
          </div>
        ))}
      </div>
    );
  };

  // 渲染增强器参数
  const renderEnricherParams = () => {
    const config = ENRICHER_UI_CONFIG[selectedEnricher];
    if (!config || config.params.length === 0) {
      return null;
    }
    
    return (
      <div className="space-y-3 pt-2 border-t border-purple-500/10">
        {config.params.map((param) => (
          <div key={param.key} className="space-y-1">
            <div className="flex items-center justify-between">
              <Label className="text-xs">{param.label}</Label>
              {param.type === 'boolean' && renderGenericParamInput(param, enricherParams[param.key], updateEnricherParam)}
            </div>
            {param.description && (
              <p className="text-xs text-muted-foreground">{param.description}</p>
            )}
            {param.type !== 'boolean' && renderGenericParamInput(param, enricherParams[param.key], updateEnricherParam)}
          </div>
        ))}
      </div>
    );
  };

  // Embedding 模型变更处理
  const handleEmbedProviderChange = (provider: string) => {
    setEmbedProvider(provider);
    setEmbedModel("");
    setDefaultModel("embedding", provider ? { provider, model: "" } : null);
  };

  const handleEmbedModelChange = (model: string) => {
    setEmbedModel(model);
    if (embedProvider) {
      setDefaultModel("embedding", { provider: embedProvider, model });
    }
  };

  // 增强预览
  const handleEnrichPreview = async () => {
    if (!client || !ground) return;
    
    // 检查是否选择了增强方式
    if (selectedEnricher === "none") {
      toast.error("请先选择增强方式");
      return;
    }
    
    // 检查是否有分块预览结果（需要先进行分块预览）
    if (chunkPreviewResult.length === 0) {
      toast.error("请先在「分段设置」中预览分块结果");
      return;
    }
    
    setIsPreviewingEnrich(true);
    setEnrichPreviewStep("准备中...");
    setSummaryPreview(null);
    setChunkEnrichPreview([]);
    setPreviewType("enrich"); // 立即切换到增强预览视图，显示加载状态
    
    try {
      const needsSummary = selectedEnricher === "document_summary";
      const needsChunkEnrich = selectedEnricher === "chunk_context";
      const summaryLength =
        typeof (enricherParams as Record<string, unknown>).summary_length === "string" &&
        ["short", "medium", "long"].includes(
          (enricherParams as Record<string, unknown>).summary_length as string
        )
          ? ((enricherParams as Record<string, unknown>).summary_length as "short" | "medium" | "long")
          : undefined;
      
      // 获取用于预览的文档内容（使用分块预览的文档）
      const selectedDoc = documents.find(d => d.id === selectedDocId);
      const docTitle = selectedDoc?.title || chunkPreviewDocTitle || "未知文档";
      
      // 合并所有 chunk 内容作为文档内容
      const fullContent = chunkPreviewResult.map(c => c.text).join("\n\n");
      
      // 1. 预览摘要
      if (needsSummary) {
        setEnrichPreviewStep("正在生成文档摘要...(LLM 处理中，请耐心等待)");
        const summaryResult = await client.previewSummary(fullContent, docTitle, {
          summaryLength,
        });
        setSummaryPreview(summaryResult.summary);
        setEnrichPreviewStep("文档摘要生成完成");
      }
      
      // 2. 预览 Chunk 增强（取前 3 个 chunks）
      if (needsChunkEnrich) {
        setEnrichPreviewStep("正在增强 Chunk 上下文...(LLM 处理中，请耐心等待)");
        const chunksToEnrich = chunkPreviewResult.slice(0, 3).map(c => c.text);
        // 如果有摘要，使用摘要；否则用空字符串
        const docSummary =
          summaryPreview ||
          (needsSummary
            ? (await client.previewSummary(fullContent, docTitle, { summaryLength })).summary
            : "");
        
        const enrichResult = await client.previewChunkEnrichment(
          chunksToEnrich,
          docTitle,
          docSummary
        );
        
        setChunkEnrichPreview(
          enrichResult.results.map((result) => ({
            original: result.original_text,
            enriched: result.enriched_text,
          }))
        );
        setEnrichPreviewStep("Chunk 增强完成");
      }
      
      setEnrichPreviewStep("");
      toast.success("增强预览完成");
    } catch (error) {
      toast.error(`预览失败: ${(error as Error).message}`);
      setEnrichPreviewStep("");
    } finally {
      setIsPreviewingEnrich(false);
      setEnrichPreviewStep("");
    }
  };

  // 打开入库 Dialog
  const handleOpenIngestDialog = () => {
    if (documents.length === 0) {
      toast.error("请先上传文档");
      return;
    }
    if (!embedProvider || !embedModel) {
      toast.error("请先选择 Embedding 模型");
      return;
    }
    // 默认名称使用 "kb-" 前缀，避免与 Ground 名称冲突
    const defaultName = ground?.name ? `kb-${ground.name.replace(/^ground-/, "")}` : "";
    setNewKbName(defaultName);
    setNewKbDesc("");
    setIngestDialogOpen(true);
  };

  // 执行入库
  const handleIngestToKb = async () => {
    if (!client || !ground) return;
    if (!newKbName.trim()) {
      toast.error("请输入知识库名称");
      return;
    }
    
    // 使用当前 Pipeline 的配置（而不是全局 UI 状态）
    const pipelineConfig = currentPipeline;
    const pipelineEmbedProvider = pipelineConfig.embedProvider;
    const pipelineEmbedModel = pipelineConfig.embedModel;
    
    if (!pipelineEmbedProvider || !pipelineEmbedModel) {
      toast.error("请选择 Embedding 模型");
      return;
    }

    // 关闭对话框并显示 loading 状态
    setIngestDialogOpen(false);
    setIsIngesting(true);
    toast.info("正在创建知识库并入库文档...");
    
    // 使用当前 Pipeline 的 chunker 配置
    const chunkerConfig = {
      name: pipelineConfig.chunker,
      params: pipelineConfig.chunkerParams,
    };
    
    // 使用当前 Pipeline 的 indexer 配置
    const indexerConfig = {
      name: pipelineConfig.indexer || 'base',
      params: pipelineConfig.indexerParams || {},
    };
    
    // 使用当前 Pipeline 的 enricher 配置
    const enricherConfig = pipelineConfig.enricher ? {
      name: pipelineConfig.enricher,
      params: pipelineConfig.enricherParams,
    } : undefined;
    
    // 获取 Embedding 配置（必需）
    const embeddingProviderConfig = providerConfigs[pipelineEmbedProvider];
    const embeddingApiKey = embeddingProviderConfig?.apiKey;
    const embeddingBaseUrl = embeddingProviderConfig?.baseUrl;
    
    // 获取 LLM 配置（用于文档增强）- 仅在启用增强时传递
    const needsLLM = pipelineConfig.enricher === "document_summary" || pipelineConfig.enricher === "chunk_context";
    const llmProvider = needsLLM && defaultModels.llm?.provider ? defaultModels.llm.provider : undefined;
    const llmModel = needsLLM && defaultModels.llm?.model ? defaultModels.llm.model : undefined;
    const llmProviderConfig = llmProvider ? providerConfigs[llmProvider] : undefined;
    const llmApiKey = llmProviderConfig?.apiKey;
    const llmBaseUrl = llmProviderConfig?.baseUrl;
    
    try {
      // 调用 ingestGround API（后端会快速返回，实际入库在后台进行）
      const result = await client.ingestGround(
        ground.ground_id,
        newKbName.trim(),
        {
          targetKbDescription: newKbDesc.trim() || undefined,
          chunker: chunkerConfig,
          indexer: indexerConfig,
          enricher: enricherConfig,
          generateSummary: pipelineConfig.enricher === "document_summary",
          enrichChunks: pipelineConfig.enricher === "chunk_context",
          embeddingProvider: pipelineEmbedProvider,
          embeddingModel: pipelineEmbedModel,
          embeddingApiKey,
          embeddingBaseUrl,
          llmProvider,
          llmModel,
          llmApiKey,
          llmBaseUrl,
        }
      );
      
      setIsIngesting(false);
      
      // 保存入库结果
      const kbId = result.knowledge_base_id;
      setIngestedKbId(kbId);
      setIngestedKbName(result.knowledge_base_name);
      
      // 更新当前 Pipeline 的入库知识库ID
      const updatedPipeline = { ...currentPipeline, ingestedKbId: kbId };
      const updatedPipelines = [...pipelines];
      updatedPipelines[currentPipelineIndex] = updatedPipeline;
      setPipelines(updatedPipelines);
      
      // 保存入库时的配置快照（用于检测配置变更）
      setIngestedConfig({
        chunker: pipelineConfig.chunker,
        chunkerParams: pipelineConfig.chunkerParams,
        indexer: pipelineConfig.indexer,
        indexerParams: pipelineConfig.indexerParams,
        enricher: pipelineConfig.enricher,
        enricherParams: pipelineConfig.enricherParams,
      });
      
      // 显示成功提示并跳转
      toast.success(`知识库「${result.knowledge_base_name}」创建成功，文档正在后台入库...`);
      
      // 跳转到知识库详情页（文档列表会显示"处理中"状态）
      router.push(`/knowledge-bases/${kbId}`);
      
    } catch (error) {
      setIsIngesting(false);
      toast.error(`入库失败: ${(error as Error).message}`);
    }
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
    if (!ingestedKbId) {
      toast.error("请先完成入库操作");
      return;
    }
    if (!query.trim()) {
      toast.error("请输入测试问题");
      return;
    }
    setIsRunning(true);
    try {
      // 构建检索器配置，包含参数
      const retrieverConfig: { name: string; params?: Record<string, unknown> } = {
        name: selectedRetriever,
      };
      // 仅当有参数时添加 params
      if (Object.keys(retrieverParams).length > 0) {
        retrieverConfig.params = retrieverParams;
      }
      
      const payload: PlaygroundRunRequest = {
        query,
        knowledge_base_ids: [ingestedKbId],
        top_k: topK,
        retriever: retrieverConfig,
        rerank: retrieverParams.rerank as boolean | undefined,
        llm_override:
          defaultModels.llm && defaultModels.llm.model && defaultModels.llm.provider
            ? {
                provider: defaultModels.llm.provider,
                model: defaultModels.llm.model,
                api_key: providerConfigs[defaultModels.llm.provider]?.apiKey,
                base_url: providerConfigs[defaultModels.llm.provider]?.baseUrl,
              }
            : undefined,
      };
      
      const response = await client.runPlayground(payload);
      setResults({ current: response });
      setPreviewType("retrieval"); // 切换到检索结果视图
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

  // ==================== 检索对比功能 ====================
  
  // 更新槽位配置
  const updateCompareSlot = (index: number, updates: Partial<typeof compareSlots[0]>) => {
    setCompareSlots(prev => prev.map((slot, i) => i === index ? { ...slot, ...updates } : slot));
  };
  
  // 添加对比槽位（最多4个）
  const addCompareSlot = () => {
    if (compareSlots.length >= 4) {
      toast.warning("最多支持 4 个对比槽位");
      return;
    }
    const newId = `slot-${compareSlots.length + 1}`;
    setCompareSlots(prev => [...prev, {
      id: newId,
      kbId: null,
      kbName: "",
      retriever: "hybrid",
      retrieverParams: getDefaultRetrieverParams("hybrid"),
      topK: 5,
      results: null,
      isLoading: false,
      error: null,
    }]);
  };
  
  // 移除对比槽位
  const removeCompareSlot = (index: number) => {
    if (compareSlots.length <= 1) {
      toast.warning("至少保留 1 个对比槽位");
      return;
    }
    setCompareSlots(prev => prev.filter((_, i) => i !== index));
  };
  
  // 打开知识库选择器
  const openCompareKbSelector = (slotIndex: number) => {
    setCompareKbSelectorSlotIndex(slotIndex);
    loadKnowledgeBases();
    setCompareKbSelectorOpen(true);
  };
  
  // 选择知识库
  const selectCompareKb = (kb: KnowledgeBase) => {
    updateCompareSlot(compareKbSelectorSlotIndex, {
      kbId: kb.id,
      kbName: kb.name,
    });
    setCompareKbSelectorOpen(false);
  };
  
  // 运行单个槽位的检索
  const runCompareSlot = async (index: number) => {
    const slot = compareSlots[index];
    if (!client || !slot.kbId || !compareQuery.trim()) {
      toast.error("请选择知识库并输入查询内容");
      return;
    }
    
    updateCompareSlot(index, { isLoading: true, error: null, results: null });
    
    try {
      const payload: PlaygroundRunRequest = {
        query: compareQuery,
        knowledge_base_ids: [slot.kbId],
        retriever: { name: slot.retriever, params: slot.retrieverParams },
        top_k: slot.topK,
        rerank: slot.retrieverParams.rerank as boolean | undefined,
        llm_override:
          defaultModels.llm && defaultModels.llm.model && defaultModels.llm.provider
            ? {
                provider: defaultModels.llm.provider,
                model: defaultModels.llm.model,
                api_key: providerConfigs[defaultModels.llm.provider]?.apiKey,
                base_url: providerConfigs[defaultModels.llm.provider]?.baseUrl,
              }
            : undefined,
      };
      
      const response = await client.runPlayground(payload);
      updateCompareSlot(index, { 
        results: response.retrieval.results,
        isLoading: false,
      });
    } catch (error) {
      updateCompareSlot(index, { 
        error: (error as Error).message,
        isLoading: false,
      });
    }
  };
  
  // 运行所有槽位的检索
  const runAllCompareSlots = async () => {
    if (!compareQuery.trim()) {
      toast.error("请输入查询内容");
      return;
    }
    
    const slotsWithKb = compareSlots.filter(s => s.kbId);
    if (slotsWithKb.length === 0) {
      toast.error("请至少选择一个知识库");
      return;
    }
    
    setIsComparingAll(true);
    
    // 并行执行所有检索
    await Promise.all(
      compareSlots.map((slot, index) => {
        if (slot.kbId) {
          return runCompareSlot(index);
        }
        return Promise.resolve();
      })
    );
    
    setIsComparingAll(false);
  };
  
  // 更新槽位检索器并重置参数
  const updateSlotRetriever = (index: number, retriever: string) => {
    updateCompareSlot(index, {
      retriever,
      retrieverParams: getDefaultRetrieverParams(retriever),
    });
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
          {/* Pipeline 按钮 */}
          <div className="flex items-center gap-1 ml-2">
            {pipelines.map((pipeline, index) => (
              <Button
                key={pipeline.id}
                variant={index === currentPipelineIndex ? "default" : "outline"}
                size="sm"
                className="h-7 w-7 p-0 relative"
                onClick={() => switchPipeline(index)}
              >
                {pipeline.name}
                {pipeline.ingestedKbId && (
                  <span className="absolute -top-1 -right-1 h-2 w-2 bg-green-500 rounded-full" />
                )}
              </Button>
            ))}
            {pipelines.length < 4 && (
              <Button
                variant="outline"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={addPipeline}
              >
                <Plus className="h-3.5 w-3.5" />
              </Button>
            )}
            {pipelines.length > 1 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                onClick={() => deletePipeline(currentPipelineIndex)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => {
              // 跳转到检索对比，并传递所有已入库的知识库
              const kbIds = getIngestedKbIds();
              if (kbIds.length === 0) {
                router.push(`/retrieval-compare?ground=${groundId}`);
              } else {
                router.push(`/retrieval-compare?ground=${groundId}&kbs=${kbIds.join(",")}`);
              }
            }}
          >
            <Search className="h-4 w-4 mr-2" />
            检索对比
            {getIngestedKbIds().length > 0 && (
              <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                {getIngestedKbIds().length}
              </Badge>
            )}
          </Button>
          <Button
            onClick={() => saveGround()}
            disabled={ground?.saved || saving}
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            {ground?.saved ? "已保存" : "保存到知识库"}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden p-6">
        <div className="grid gap-4 lg:grid-cols-[400px_1fr] h-[calc(100vh-140px)]">
          <div className="overflow-y-auto h-full pr-2">
            <div className="space-y-4">
              <Card className="overflow-hidden">
              <CardHeader>
                <CardTitle>文件上传</CardTitle>
                <CardDescription>上传用于本 ground 的文件</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 overflow-hidden">
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
                      <div key={doc.id} className="rounded border p-2 bg-muted/30 flex items-start justify-between gap-2 overflow-hidden">
                        <div className="flex-1 min-w-0 overflow-hidden">
                          <div className="font-medium truncate max-w-full">{doc.title}</div>
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

            {/* 索引增强设置卡片 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  索引增强
                  <Badge variant="outline" className="text-xs font-normal">入库时生效</Badge>
                </CardTitle>
                <CardDescription>配置索引方法和上下文增强，将在文档入库时应用</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-600 dark:text-amber-400">
                  💡 索引增强配置将在「入库到知识库」时生效，需要 LLM 资源。暂不支持预览。
                </div>
                {/* 索引方法 */}
                <div className="rounded-lg border-2 border-purple-500/20 p-4 space-y-4 bg-purple-500/5">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-purple-500/10 flex items-center justify-center">
                      <Layers className="h-4 w-4 text-purple-500" />
                    </div>
                    <div>
                      <div className="font-medium">索引方法</div>
                      <div className="text-xs text-muted-foreground">选择如何组织向量索引</div>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Select value={selectedIndexer} onValueChange={handleIndexerChange}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择索引方法" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(INDEXER_UI_CONFIG).map(([key, config]) => (
                          <SelectItem key={key} value={key}>
                            {config.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {INDEXER_UI_CONFIG[selectedIndexer] && (
                    <div className="text-xs text-muted-foreground">
                      {INDEXER_UI_CONFIG[selectedIndexer].description}
                    </div>
                  )}
                  
                  {renderIndexerParams()}
                </div>

                {/* 上下文增强 */}
                <div className="rounded-lg border-2 border-orange-500/20 p-4 space-y-4 bg-orange-500/5">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-orange-500/10 flex items-center justify-center">
                      <Sparkles className="h-4 w-4 text-orange-500" />
                    </div>
                    <div>
                      <div className="font-medium">上下文增强</div>
                      <div className="text-xs text-muted-foreground">增强 chunk 的上下文信息</div>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Select value={selectedEnricher} onValueChange={handleEnricherChange}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择增强方式" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(ENRICHER_UI_CONFIG).map(([key, config]) => (
                          <SelectItem key={key} value={key}>
                            {config.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {ENRICHER_UI_CONFIG[selectedEnricher] && (
                    <div className="text-xs text-muted-foreground">
                      {ENRICHER_UI_CONFIG[selectedEnricher].description}
                    </div>
                  )}
                  
                  {renderEnricherParams()}
                  
                  {/* 预览按钮 */}
                  {selectedEnricher !== "none" && (
                    <div className="pt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleEnrichPreview}
                        disabled={isPreviewingEnrich || chunkPreviewResult.length === 0}
                        className="w-full"
                      >
                        {isPreviewingEnrich ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <Eye className="h-4 w-4 mr-2" />
                        )}
                        预览增强效果
                      </Button>
                      {chunkPreviewResult.length === 0 && (
                        <p className="text-xs text-muted-foreground text-center mt-1">
                          请先在「分段设置」中预览分块
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Embedding 模型选择 */}
                <div className="rounded-lg border-2 border-green-500/20 p-4 space-y-4 bg-green-500/5">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-green-500/10 flex items-center justify-center">
                      <Database className="h-4 w-4 text-green-500" />
                    </div>
                    <div>
                      <div className="font-medium">Embedding 模型</div>
                      <div className="text-xs text-muted-foreground">选择向量化模型用于入库</div>
                    </div>
                  </div>
                  
                  <AllModelsSelector
                    type="embedding"
                    value={embedProvider && embedModel ? { provider: embedProvider, model: embedModel } : undefined}
                    onChange={(val) => {
                      if (val) {
                        setEmbedProvider(val.provider);
                        setEmbedModel(val.model);
                        setDefaultModel("embedding", val);
                      } else {
                        setEmbedProvider("");
                        setEmbedModel("");
                        setDefaultModel("embedding", null);
                      }
                    }}
                    placeholder="选择 Embedding 模型"
                  />
                </div>

                {/* 入库按钮 */}
                <div className="pt-2">
                  <Button
                    className="w-full"
                    size="lg"
                    onClick={handleOpenIngestDialog}
                    disabled={documents.length === 0 || !embedProvider || !embedModel}
                  >
                    <Database className="h-4 w-4 mr-2" />
                    入库到知识库
                  </Button>
                  {documents.length === 0 && (
                    <p className="text-xs text-muted-foreground text-center mt-2">请先上传文档</p>
                  )}
                  {documents.length > 0 && (!embedProvider || !embedModel) && (
                    <p className="text-xs text-muted-foreground text-center mt-2">请选择 Embedding 模型</p>
                  )}
                </div>
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
                    : previewType === "enrich"
                    ? `增强预览效果${summaryPreview ? " - 含文档摘要" : ""}${chunkEnrichPreview.length > 0 ? ` + ${chunkEnrichPreview.length} 个 Chunk 增强` : ""}`
                    : previewType === "retrieval" && results.current
                    ? `检索结果 - ${RETRIEVER_UI_CONFIG[results.current.retrieval.retriever]?.label || results.current.retrieval.retriever} (${results.current.retrieval.results.length} 条)`
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
                                  <div className="space-y-2">
                                    {children.length > 0 ? (
                                      children.map((child, idx) => (
                                        <div 
                                          key={child.index} 
                                          className="group flex items-start gap-2 cursor-pointer"
                                        >
                                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 shrink-0 group-hover:bg-blue-200 dark:group-hover:bg-blue-800">
                                            C-{idx + 1}
                                          </span>
                                          <span className="text-sm break-all group-hover:bg-blue-50 dark:group-hover:bg-blue-950/50 rounded px-1 -mx-1 transition-colors min-w-0">
                                            {child.text}
                                          </span>
                                        </div>
                                      ))
                                    ) : (
                                      <span className="text-sm text-muted-foreground break-all">{parent.text}</span>
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
                ) : previewType === "enrich" ? (
                  <ScrollArea className="h-[500px]">
                    {isPreviewingEnrich ? (
                      <div className="flex flex-col items-center justify-center py-16 space-y-4">
                        <div className="relative">
                          <div className="w-12 h-12 border-4 border-orange-200 rounded-full animate-spin border-t-orange-500" />
                        </div>
                        <div className="text-sm font-medium text-orange-600">
                          {enrichPreviewStep || "处理中..."}
                        </div>
                        <div className="text-xs text-muted-foreground max-w-xs text-center">
                          LLM 正在处理，请耐心等待。根据文档长度，可能需要 5-30 秒
                        </div>
                      </div>
                    ) : !summaryPreview && chunkEnrichPreview.length === 0 ? (
                      <div className="text-sm text-muted-foreground text-center py-12">
                        在左侧选择增强方式后点击"预览增强效果"
                      </div>
                    ) : (
                      <div className="space-y-4 pr-4">
                        {/* 文档摘要 */}
                        {summaryPreview && (
                          <div className="rounded-lg border-2 border-orange-500/30 bg-orange-50 dark:bg-orange-950/20 p-4">
                            <div className="flex items-center gap-2 text-sm font-medium text-orange-600 dark:text-orange-400 mb-3">
                              <FileText className="h-4 w-4" />
                              文档摘要
                            </div>
                            <div className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                              {summaryPreview}
                            </div>
                          </div>
                        )}
                        
                        {/* Chunk 增强对比 */}
                        {chunkEnrichPreview.length > 0 && (
                          <div className="space-y-3">
                            <div className="flex items-center gap-2 text-sm font-medium text-orange-600 dark:text-orange-400">
                              <Sparkles className="h-4 w-4" />
                              Chunk 增强对比（前 {chunkEnrichPreview.length} 个）
                            </div>
                            {chunkEnrichPreview.map((item, idx) => (
                              <div key={idx} className="rounded-lg border p-3 space-y-3">
                                <div className="text-xs font-medium text-muted-foreground">
                                  Chunk #{idx + 1}
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                  <div className="rounded bg-muted/50 p-3">
                                    <div className="text-xs text-muted-foreground mb-2 font-medium">原文</div>
                                    <div className="text-sm leading-relaxed whitespace-pre-wrap">{item.original}</div>
                                  </div>
                                  <div className="rounded bg-orange-100 dark:bg-orange-900/30 p-3">
                                    <div className="text-xs text-orange-600 dark:text-orange-400 mb-2 font-medium">增强后</div>
                                    <div className="text-sm leading-relaxed whitespace-pre-wrap">{item.enriched}</div>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </ScrollArea>
                ) : previewType === "retrieval" && results.current ? (
                  <ScrollArea className="h-[500px]">
                    <div className="space-y-4 pr-4">
                      {/* RAG 回答 */}
                      <div className="rounded border p-3 bg-muted/30">
                        <div className="text-xs text-muted-foreground mb-1 font-medium">RAG 回答</div>
                        <div className="text-sm leading-relaxed">{results.current.rag.answer}</div>
                        <div className="text-xs text-muted-foreground mt-2 flex gap-2 flex-wrap">
                          <Badge variant="outline">LLM: {results.current.rag.model.llm_model || "-"}</Badge>
                          <Badge variant="outline">Embed: {results.current.rag.model.embedding_model}</Badge>
                          <Badge variant="outline">时延: {Math.round(results.current.metrics?.total_ms || 0)} ms</Badge>
                        </div>
                      </div>
                      {/* 检索结果列表 */}
                      <div className="text-sm font-medium text-muted-foreground mb-3">
                        {results.current.retrieval.results.length} 个召回段落
                      </div>
                      <div className="space-y-3">
                        {results.current.retrieval.results.map((hit, idx) => {
                          const meta = hit.metadata || {};
                          const filename = (meta.original_filename as string) || (meta.title as string) || "未知文件";
                          const chunkIndex = meta.chunk_index ?? meta.chunk_id ?? idx;
                          const charCount = hit.text?.length || 0;
                          const retrieverType = results.current!.retrieval.retriever;
                          const reranked = results.current!.retrieval.rerank_applied;
                          const scoreLabel = getScoreLabel(retrieverType, reranked);
                          const isParentChild = isParentChildResult(hit);
                          
                          return (
                            <div 
                              key={hit.chunk_id || idx} 
                              className="rounded-lg border bg-card hover:border-blue-300 transition-colors"
                            >
                              {/* 卡片头部：Chunk 信息 + 评分 */}
                              <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/20">
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                  <span className="font-mono">Chunk-{String(chunkIndex).padStart(2, "0")}</span>
                                  <span className="text-muted-foreground/50">·</span>
                                  <span>{charCount} 字符</span>
                                  {isParentChild && (
                                    <>
                                      <span className="text-muted-foreground/50">·</span>
                                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 bg-purple-50 text-purple-600 border-purple-200">
                                        {meta.child ? "子块" : "父块"}
                                      </Badge>
                                    </>
                                  )}
                                </div>
                                <Badge 
                                  variant="outline" 
                                  className="text-xs font-mono bg-blue-50 text-blue-600 border-blue-200"
                                >
                                  {scoreLabel} {hit.score.toFixed(2)}
                                </Badge>
                              </div>
                              
                              {/* 内容区域 */}
                              <div className="p-3">
                                {/* 文本内容（截断显示） */}
                                <div className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                                  {hit.text}
                                </div>
                              </div>
                              
                              {/* 底部：文件名 + 打开按钮 */}
                              <div className="flex items-center justify-between px-3 py-2 border-t bg-muted/10">
                                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                  <FileText className="h-3.5 w-3.5" />
                                  <span className="truncate max-w-[200px]">{filename}</span>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 gap-1"
                                  onClick={() => {
                                    setSelectedChunkHit({ hit, index: idx, retrieverType });
                                    setChunkDetailOpen(true);
                                  }}
                                >
                                  打开
                                  <Eye className="h-3 w-3" />
                                </Button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </ScrollArea>
                ) : (
                  <div className="text-sm text-muted-foreground text-center py-12">
                    运行实验后在此查看结果
                  </div>
                )}
              </CardContent>
            </Card>
            </div>
          </div>
        </div>
      </div>

      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="max-w-lg overflow-hidden">
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
            <div className="space-y-2 min-w-0">
              <div className="text-sm text-muted-foreground">
                已选择 {pendingFiles.length} 个文件
              </div>
              <div className="max-h-[200px] overflow-auto space-y-2">
                {pendingFiles.map((file, idx) => (
                  <div
                    key={`${file.name}-${idx}`}
                    className="flex items-center justify-between gap-2 rounded-lg border p-3 bg-muted/30"
                  >
                    <div className="flex items-center gap-3 min-w-0 flex-1 overflow-hidden">
                      <FileText className="h-5 w-5 text-muted-foreground shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium truncate max-w-full">{file.name}</div>
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

      {/* 入库 Dialog */}
      <Dialog open={ingestDialogOpen} onOpenChange={setIngestDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>创建知识库并入库</DialogTitle>
            <DialogDescription>
              将当前文档以配置的分段和索引增强设置入库到新知识库
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>知识库名称</Label>
              <Input
                placeholder="输入知识库名称"
                value={newKbName}
                onChange={(e) => setNewKbName(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                知识库名称不能与 Playground 名称相同（如 {ground?.name}）
              </p>
            </div>
            <div className="space-y-2">
              <Label>描述（可选）</Label>
              <Textarea
                placeholder="输入知识库描述"
                value={newKbDesc}
                onChange={(e) => setNewKbDesc(e.target.value)}
                rows={3}
              />
            </div>
            {/* 配置摘要 */}
            <div className="rounded-lg border p-3 space-y-2 text-sm">
              <div className="font-medium text-muted-foreground">当前配置</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">切分器:</span>{" "}
                  <Badge variant="secondary">{CHUNKER_UI_CONFIG[selectedChunker]?.label || selectedChunker}</Badge>
                </div>
                <div>
                  <span className="text-muted-foreground">索引:</span>{" "}
                  <Badge variant="secondary">{INDEXER_UI_CONFIG[selectedIndexer]?.label || selectedIndexer}</Badge>
                </div>
                <div>
                  <span className="text-muted-foreground">增强:</span>{" "}
                  <Badge variant="secondary">{ENRICHER_UI_CONFIG[selectedEnricher]?.label || selectedEnricher}</Badge>
                </div>
                <div>
                  <span className="text-muted-foreground">Embedding:</span>{" "}
                  <Badge variant="secondary">{embedModel || "未选择"}</Badge>
                </div>
              </div>
              <div className="text-xs text-muted-foreground pt-1">
                文档数量: {documents.length} 个
              </div>
            </div>
            {/* 入库进度指示器 */}
            {ingestProgress && (
              <div className="rounded-lg border p-3 space-y-3 bg-muted/30">
                <div className="font-medium text-sm">入库进度</div>
                <div className="space-y-2">
                  {ingestProgress.steps.map((step, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm">
                      {step.status === 'done' ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      ) : step.status === 'running' ? (
                        <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                      ) : step.status === 'error' ? (
                        <XCircle className="h-4 w-4 text-red-500" />
                      ) : (
                        <Circle className="h-4 w-4 text-muted-foreground" />
                      )}
                      <span className={
                        step.status === 'done' ? 'text-green-600' :
                        step.status === 'running' ? 'text-blue-600 font-medium' :
                        step.status === 'error' ? 'text-red-600' :
                        'text-muted-foreground'
                      }>
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIngestDialogOpen(false)} disabled={isIngesting}>
              取消
            </Button>
            <Button onClick={handleIngestToKb} disabled={isIngesting || !newKbName.trim()}>
              {isIngesting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              创建并入库
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 检索结果详情 Dialog */}
      <Dialog open={chunkDetailOpen} onOpenChange={setChunkDetailOpen}>
        <DialogContent className={`!max-w-none ${selectedChunkHit && isParentChildResult(selectedChunkHit.hit) ? 'w-[95vw] h-[90vh]' : 'w-[85vw] h-[85vh]'}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              段落详情
              {selectedChunkHit && (
                <span className="text-xs font-normal text-muted-foreground">
                  #{selectedChunkHit.index + 1}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>
          
          {selectedChunkHit && (() => {
            const { hit, retrieverType } = selectedChunkHit;
            const meta = hit.metadata || {};
            const filename = (meta.original_filename as string) || (meta.title as string) || "未知文件";
            const chunkIndex = meta.chunk_index ?? meta.chunk_id ?? selectedChunkHit.index;
            const scoreLabel = getScoreLabel(retrieverType, results.current?.retrieval.rerank_applied);
            const hasParentContext = isParentChildResult(hit);
            
            // 获取子块列表（用于父子检索显示）
            const childChunks = hasParentContext && results.current 
              ? results.current.retrieval.results.filter(r => {
                  const rMeta = r.metadata || {};
                  return rMeta.parent_id === meta.parent_id && rMeta.child;
                })
              : [];
            
            if (hasParentContext) {
              // 父子检索模式：左侧父段，右侧子段列表
              return (
                <div className="grid grid-cols-2 gap-8 w-full">
                  {/* 左侧：父段内容 */}
                  <div className="space-y-3 min-w-0">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="font-mono">父分段-{String(chunkIndex).padStart(2, "0")}</span>
                        <span className="text-muted-foreground/50">·</span>
                        <FileText className="h-3 w-3" />
                        <span className="truncate max-w-[150px]">{filename}</span>
                      </div>
                      <Badge 
                        variant="outline" 
                        className="text-xs font-mono bg-blue-50 text-blue-600 border-blue-200"
                      >
                        {scoreLabel} {hit.score.toFixed(2)}
                      </Badge>
                    </div>
                    
                    <ScrollArea className="h-[calc(75vh-100px)] rounded-lg border bg-muted/20 p-4">
                      <div className="text-sm leading-relaxed whitespace-pre-wrap">
                        {hit.context_text || hit.text}
                      </div>
                    </ScrollArea>
                  </div>
                  
                  {/* 右侧：命中子段列表 */}
                  <div className="space-y-3 min-w-0">
                    <div className="text-xs text-muted-foreground font-medium">
                      命中 {childChunks.length > 0 ? childChunks.length : 1} 个子段落
                    </div>
                    
                    <ScrollArea className="h-[calc(75vh-100px)]">
                      {(childChunks.length > 0 ? childChunks : [hit]).map((child, cidx) => {
                        const childMeta = child.metadata || {};
                        const childIndex = childMeta.child_index ?? cidx;
                        return (
                          <div 
                            key={child.chunk_id || cidx} 
                            className="rounded-lg border bg-purple-50/50 dark:bg-purple-950/20 p-3 mb-2"
                          >
                            <div className="flex items-center justify-between mb-2">
                              <Badge 
                                variant="outline" 
                                className="text-[10px] px-1.5 py-0 h-4 bg-purple-100 text-purple-700 border-purple-300"
                              >
                                C-{String(childIndex)}
                              </Badge>
                              <span className="text-[10px] text-muted-foreground font-mono">
                                {scoreLabel} {child.score.toFixed(2)}
                              </span>
                            </div>
                            <div className="text-sm leading-relaxed whitespace-pre-wrap">
                              {child.text}
                            </div>
                          </div>
                        );
                      })}
                    </ScrollArea>
                  </div>
                </div>
              );
            } else {
              // 普通检索模式
              return (
                <div className="space-y-4">
                  {/* 头部信息 */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="font-mono">分段-{String(chunkIndex).padStart(2, "0")}</span>
                      <span className="text-muted-foreground/50">·</span>
                      <FileText className="h-3 w-3" />
                      <span className="truncate max-w-[200px]">{filename}</span>
                    </div>
                    <Badge 
                      variant="outline" 
                      className="text-xs font-mono bg-blue-50 text-blue-600 border-blue-200"
                    >
                      {scoreLabel} {hit.score.toFixed(2)}
                    </Badge>
                  </div>
                  
                  {/* 内容区域 */}
                  <ScrollArea className="h-[calc(75vh-100px)] rounded-lg border bg-muted/20 p-4">
                    <div className="text-sm leading-relaxed whitespace-pre-wrap">
                      {hit.text}
                    </div>
                  </ScrollArea>
                </div>
              );
            }
          })()}
        </DialogContent>
      </Dialog>

      {/* 知识库选择器 Dialog */}
      <Dialog open={kbSelectorOpen} onOpenChange={setKbSelectorOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>选择知识库</DialogTitle>
            <DialogDescription>
              选择一个已有的知识库进行检索测试
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {isLoadingKbs ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">加载中...</span>
              </div>
            ) : knowledgeBases.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Database className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>暂无可用的知识库</p>
                <p className="text-xs mt-1">请先在「索引增强设置」中入库文档</p>
              </div>
            ) : (
              <ScrollArea className="h-[300px]">
                <div className="space-y-2 pr-4">
                  {knowledgeBases.map((kb) => (
                    <div
                      key={kb.id}
                      className={`p-3 rounded-lg border cursor-pointer transition-colors hover:bg-accent ${
                        ingestedKbId === kb.id
                          ? "border-primary bg-primary/5"
                          : "border-border"
                      }`}
                      onClick={() => handleSelectKnowledgeBase(kb)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Database className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{kb.name}</span>
                        </div>
                        {ingestedKbId === kb.id && (
                          <Badge variant="default" className="text-xs">
                            当前
                          </Badge>
                        )}
                      </div>
                      {kb.description && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {kb.description}
                        </p>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        {kb.document_count !== undefined && (
                          <span>{kb.document_count} 个文档</span>
                        )}
                        <span>{new Date(kb.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
