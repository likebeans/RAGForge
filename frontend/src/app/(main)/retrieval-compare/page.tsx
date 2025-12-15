"use client";

import { useEffect, useMemo, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  OperatorListResponse,
  PlaygroundRunRequest,
  PlaygroundRunResponse,
  KnowledgeBase,
  GroundInfo,
} from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { AllModelsSelector } from "@/components/settings";
import {
  Loader2,
  Play,
  ArrowLeft,
  Search,
  Database,
  Plus,
  X,
  Eye,
  FileText,
  GitCompare,
  ChevronDown,
  Link,
  Check,
  Square,
  CheckSquare,
  StopCircle,
  Trash2,
  Settings2,
  ChevronRight,
  Sparkles,
} from "lucide-react";

// 检索器参数配置类型
type ParamConfig = {
  key: string;
  label: string;
  type: 'number' | 'boolean' | 'select' | 'slider';
  default: number | boolean | string;
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
  showWhen?: Record<string, unknown>;
};

type RetrieverConfig = {
  label: string;
  description: string;
  params: ParamConfig[];
};

// 检索器 UI 配置（参考 rag优化.md 文档）
const RETRIEVER_UI_CONFIG: Record<string, RetrieverConfig> = {
  dense: {
    label: "向量检索",
    description: "基于语义相似度的稠密向量检索",
    params: []
  },
  hybrid: {
    label: "混合检索",
    description: "向量 + BM25 加权融合",
    params: [
      { key: 'dense_weight', label: '向量权重', type: 'slider', default: 0.7, min: 0, max: 1, step: 0.1 },
      { key: 'sparse_weight', label: 'BM25权重', type: 'slider', default: 0.3, min: 0, max: 1, step: 0.1 }
    ]
  },
  fusion: {
    label: "融合检索",
    description: "RRF/加权融合（Rerank 请使用右侧选择器）",
    params: [
      { key: 'mode', label: '融合模式', type: 'select', default: 'rrf', options: ['rrf', 'weighted'] },
      { key: 'rrf_k', label: 'RRF常数', type: 'number', default: 60, min: 1, max: 100 },
      { key: 'dense_weight', label: '向量权重', type: 'slider', default: 0.7, min: 0, max: 1, step: 0.1 },
      { key: 'bm25_weight', label: 'BM25权重', type: 'slider', default: 0.3, min: 0, max: 1, step: 0.1 }
    ]
  },
  hyde: {
    label: "HyDE检索",
    description: "LLM生成假设答案进行检索",
    params: [
      { key: 'base_retriever', label: '底层检索器', type: 'select', default: 'dense', options: ['dense', 'hybrid'] },
      { key: 'num_queries', label: '假设答案数', type: 'number', default: 4, min: 1, max: 10 },
      { key: 'include_original', label: '保留原始查询', type: 'boolean', default: true }
    ]
  },
  multi_query: {
    label: "多查询检索",
    description: "LLM生成查询变体，多路召回",
    params: [
      { key: 'base_retriever', label: '底层检索器', type: 'select', default: 'dense', options: ['dense', 'hybrid'] },
      { key: 'num_queries', label: '查询变体数', type: 'number', default: 3, min: 1, max: 10 },
      { key: 'include_original', label: '保留原始查询', type: 'boolean', default: true },
      { key: 'rrf_k', label: 'RRF常数', type: 'number', default: 60, min: 1, max: 100 }
    ]
  },
  parent_document: {
    label: "父文档检索",
    description: "子块检索返回父块上下文",
    params: [
      { key: 'base_retriever', label: '底层检索器', type: 'select', default: 'dense', options: ['dense', 'hybrid'] },
      { key: 'return_parent', label: '返回父块', type: 'boolean', default: true },
      { key: 'include_child', label: '包含子块信息', type: 'boolean', default: false }
    ]
  },
  llama_dense: {
    label: "LlamaIndex向量检索",
    description: "支持多向量存储后端",
    params: [
      { key: 'store_type', label: '存储类型', type: 'select', default: 'qdrant', options: ['qdrant', 'milvus', 'es'] }
    ]
  },
  llama_bm25: {
    label: "BM25检索",
    description: "基于关键词匹配的稀疏检索（中文分词优化）",
    params: []
  },
  llama_hybrid: {
    label: "LlamaIndex混合检索",
    description: "LlamaIndex向量 + BM25混合",
    params: [
      { key: 'dense_weight', label: '向量权重', type: 'slider', default: 0.7, min: 0, max: 1, step: 0.1 },
      { key: 'bm25_weight', label: 'BM25权重', type: 'slider', default: 0.3, min: 0, max: 1, step: 0.1 }
    ]
  }
};

// 获取检索器默认参数（从 UI 配置中提取）
const getDefaultRetrieverParams = (retriever: string): Record<string, unknown> => {
  const config = RETRIEVER_UI_CONFIG[retriever];
  if (!config || !config.params || config.params.length === 0) {
    return {};
  }
  const params: Record<string, unknown> = {};
  for (const param of config.params) {
    params[param.key] = param.default;
  }
  return params;
};

// 对比槽位类型
type CompareSlot = {
  id: string;
  kbId: string | null;
  kbName: string;
  retriever: string;
  retrieverParams: Record<string, unknown>;
  topK: number;
  rerankModel: { provider: string; model: string } | null;
  results: PlaygroundRunResponse["retrieval"]["results"] | null;
  hydeQueries: string[] | null; // HyDE 假设答案
  generatedQueries: string[] | null; // MultiQuery 生成的查询变体
  isLoading: boolean;
  error: string | null;
};

function RetrievalCompareContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const groundId = searchParams.get("ground");
  const kbsParam = searchParams.get("kbs"); // 从 URL 获取知识库 ID 列表

  const { client, isConnected, defaultModels, providerConfigs } = useAppStore();

  // 操作符列表
  const [operators, setOperators] = useState<OperatorListResponse | null>(null);

  // 知识库相关
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [isLoadingKbs, setIsLoadingKbs] = useState(false);

  // 检索对比状态
  const [compareQuery, setCompareQuery] = useState("");
  const [compareSlots, setCompareSlots] = useState<CompareSlot[]>([
    { id: "slot-1", kbId: null, kbName: "", retriever: "hybrid", retrieverParams: getDefaultRetrieverParams("hybrid"), topK: 5, rerankModel: null, results: null, hydeQueries: null, generatedQueries: null, isLoading: false, error: null },
    { id: "slot-2", kbId: null, kbName: "", retriever: "dense", retrieverParams: getDefaultRetrieverParams("dense"), topK: 5, rerankModel: null, results: null, hydeQueries: null, generatedQueries: null, isLoading: false, error: null },
  ]);
  const [compareKbSelectorOpen, setCompareKbSelectorOpen] = useState(false);
  const [compareKbSelectorSlotIndex, setCompareKbSelectorSlotIndex] = useState<number>(0);
  const [isComparingAll, setIsComparingAll] = useState(false);

  // 结果详情弹窗
  const [selectedChunkHit, setSelectedChunkHit] = useState<{
    hit: PlaygroundRunResponse["retrieval"]["results"][0];
    index: number;
    retrieverType: string;
  } | null>(null);
  const [chunkDetailOpen, setChunkDetailOpen] = useState(false);

  // Ground 相关状态
  const [groundList, setGroundList] = useState<GroundInfo[]>([]);
  const [currentGround, setCurrentGround] = useState<GroundInfo | null>(null);
  const [groundSelectorOpen, setGroundSelectorOpen] = useState(false);
  const [isLoadingGrounds, setIsLoadingGrounds] = useState(false);

  // 知识库加载 Dialog 状态
  const [kbLoadDialogOpen, setKbLoadDialogOpen] = useState(false);
  const [selectedKbsToLoad, setSelectedKbsToLoad] = useState<string[]>([]);
  const [pendingGround, setPendingGround] = useState<GroundInfo | null>(null);
  
  // 自动加载标志（防止重复加载）
  const [autoLoaded, setAutoLoaded] = useState(false);
  
  // 结束对比 Dialog 状态
  const [endCompareDialogOpen, setEndCompareDialogOpen] = useState(false);
  const [kbsToKeep, setKbsToKeep] = useState<string[]>([]);
  const [isEndingCompare, setIsEndingCompare] = useState(false);

  // 检索器选项
  const retrieverOptions = useMemo(() => {
    if (!operators?.retrievers) return [];
    return operators.retrievers;
  }, [operators]);

  // 加载操作符列表
  useEffect(() => {
    if (client && isConnected) {
      client.listOperators().then(setOperators).catch(() => {});
    }
  }, [client, isConnected]);

  // 加载当前 Ground 信息
  useEffect(() => {
    if (client && isConnected && groundId) {
      client.getGround(groundId).then(setCurrentGround).catch(() => {});
    }
  }, [client, isConnected, groundId]);
  
  // 自动加载知识库到对比槽位（从 URL kbs 参数）
  useEffect(() => {
    if (!client || !isConnected || !kbsParam || autoLoaded) return;
    
    const kbIds = kbsParam.split(",").filter(id => id.trim());
    if (kbIds.length === 0) return;
    
    // 加载知识库列表并匹配
    const loadAndSetKbs = async () => {
      try {
        const result = await client.listKnowledgeBases();
        setKnowledgeBases(result.items);
        
        // 找到匹配的知识库
        const matchedKbs = kbIds
          .map(id => result.items.find(kb => kb.id === id))
          .filter((kb): kb is KnowledgeBase => kb !== undefined)
          .slice(0, 4); // 最多 4 个
        
        if (matchedKbs.length > 0) {
          // 创建对应的槽位
          const newSlots: CompareSlot[] = matchedKbs.map((kb, index) => ({
            id: `slot-${index + 1}`,
            kbId: kb.id,
            kbName: kb.name,
            retriever: "hybrid",
            retrieverParams: getDefaultRetrieverParams("hybrid"),
            topK: 5,
            rerankModel: null,
            results: null,
            hydeQueries: null,
            generatedQueries: null,
            isLoading: false,
            error: null,
          }));
          setCompareSlots(newSlots);
          toast.success(`已自动加载 ${matchedKbs.length} 个知识库`);
        }
      } catch {
        console.error("Failed to auto-load knowledge bases");
      }
      setAutoLoaded(true);
    };
    
    loadAndSetKbs();
  }, [client, isConnected, kbsParam, autoLoaded]);

  // 加载 Ground 列表
  const loadGroundList = async () => {
    if (!client) return;
    setIsLoadingGrounds(true);
    try {
      const result = await client.listGrounds();
      setGroundList(result.items);
    } catch {
      toast.error("加载 Playground 列表失败");
    } finally {
      setIsLoadingGrounds(false);
    }
  };

  // 切换 Ground（从已有绑定切换到其他 Ground）
  const selectGround = (ground: GroundInfo) => {
    setCurrentGround(ground);
    setGroundSelectorOpen(false);
    // 更新 URL 参数
    router.push(`/retrieval-compare?ground=${ground.ground_id}`);
  };

  // 选择 Ground 并打开知识库加载 Dialog（用于首次关联）
  const selectGroundAndLoadKbs = async (ground: GroundInfo) => {
    setPendingGround(ground);
    setGroundSelectorOpen(false);
    // 加载知识库列表
    await loadKnowledgeBases();
    // 如果 Ground 已保存，预选其对应的知识库
    if (ground.saved && ground.knowledge_base_id) {
      setSelectedKbsToLoad([ground.knowledge_base_id]);
    } else {
      setSelectedKbsToLoad([]);
    }
    setKbLoadDialogOpen(true);
  };

  // 确认加载知识库到对比槽位
  const confirmLoadKbs = () => {
    if (!pendingGround) return;
    
    // 获取选中的知识库信息
    const selectedKbs = knowledgeBases.filter(kb => selectedKbsToLoad.includes(kb.id));
    
    if (selectedKbs.length === 0) {
      toast.warning("请至少选择一个知识库");
      return;
    }
    
    // 创建对比槽位（最多4个）
    const retrievers = ["hybrid", "dense", "fusion", "llama_bm25"];
    const newSlots: CompareSlot[] = selectedKbs.slice(0, 4).map((kb, index) => ({
      id: `slot-${index + 1}`,
      kbId: kb.id,
      kbName: kb.name,
      retriever: retrievers[index % retrievers.length],
      retrieverParams: getDefaultRetrieverParams(retrievers[index % retrievers.length]),
      topK: 5,
      rerankModel: null,
      results: null,
      hydeQueries: null,
      generatedQueries: null,
      isLoading: false,
      error: null,
    }));
    
    setCompareSlots(newSlots);
    setCurrentGround(pendingGround);
    setKbLoadDialogOpen(false);
    setPendingGround(null);
    setSelectedKbsToLoad([]);
    
    // 更新 URL
    router.push(`/retrieval-compare?ground=${pendingGround.ground_id}`);
    toast.success(`已加载 ${selectedKbs.length} 个知识库到对比槽位`);
  };

  // 切换知识库选中状态
  const toggleKbSelection = (kbId: string) => {
    setSelectedKbsToLoad(prev => {
      if (prev.includes(kbId)) {
        return prev.filter(id => id !== kbId);
      } else if (prev.length < 4) {
        return [...prev, kbId];
      } else {
        toast.warning("最多选择 4 个知识库");
        return prev;
      }
    });
  };

  // 全选/取消全选知识库
  const toggleSelectAllKbs = () => {
    if (selectedKbsToLoad.length === Math.min(knowledgeBases.length, 4)) {
      setSelectedKbsToLoad([]);
    } else {
      setSelectedKbsToLoad(knowledgeBases.slice(0, 4).map(kb => kb.id));
    }
  };

  // 加载知识库列表
  const loadKnowledgeBases = async () => {
    if (!client) return;
    setIsLoadingKbs(true);
    try {
      const result = await client.listKnowledgeBases();
      setKnowledgeBases(result.items);
    } catch {
      toast.error("加载知识库列表失败");
    } finally {
      setIsLoadingKbs(false);
    }
  };

  // ==================== 检索对比功能 ====================

  // 更新槽位配置
  const updateCompareSlot = (index: number, updates: Partial<CompareSlot>) => {
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
      rerankModel: null,
      results: null,
      hydeQueries: null,
      generatedQueries: null,
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
      // Debug: 检查 rerank 配置
      if (slot.rerankModel) {
        const rerankOverride = {
          provider: slot.rerankModel.provider,
          model: slot.rerankModel.model,
          api_key: providerConfigs[slot.rerankModel.provider]?.apiKey,
          base_url: providerConfigs[slot.rerankModel.provider]?.baseUrl,
        };
        console.log("DEBUG rerank override 将发送:", JSON.stringify(rerankOverride));
      }
      const payload: PlaygroundRunRequest = {
        query: compareQuery,
        knowledge_base_ids: [slot.kbId],
        retriever: { name: slot.retriever, params: slot.retrieverParams },
        top_k: slot.topK,
        rerank: slot.rerankModel ? true : (slot.retrieverParams.rerank as boolean | undefined),
        rerank_override: slot.rerankModel ? {
          provider: slot.rerankModel.provider,
          model: slot.rerankModel.model,
          api_key: providerConfigs[slot.rerankModel.provider]?.apiKey,
          base_url: providerConfigs[slot.rerankModel.provider]?.baseUrl,
        } : undefined,
        llm_override:
          defaultModels.llm && defaultModels.llm.model && defaultModels.llm.provider
            ? {
                provider: defaultModels.llm.provider,
                model: defaultModels.llm.model,
                api_key: providerConfigs[defaultModels.llm.provider]?.apiKey,
                base_url: providerConfigs[defaultModels.llm.provider]?.baseUrl,
              }
            : undefined,
        // 注意：embedding_override 在检索时不传递，因为必须使用知识库入库时的 Embedding 模型
      };

      const response = await client.runPlayground(payload);
      // 提取 HyDE 假设答案或 MultiQuery 生成的查询变体
      const firstResult = response.retrieval.results?.[0];
      const hydeQueries = (firstResult as unknown as Record<string, unknown>)?.hyde_queries as string[] | undefined;
      const generatedQueries = (firstResult as unknown as Record<string, unknown>)?.generated_queries as string[] | undefined;
      updateCompareSlot(index, {
        results: response.retrieval.results,
        hydeQueries: hydeQueries || null,
        generatedQueries: generatedQueries || null,
        isLoading: false,
      });
    } catch (error) {
      let errorMessage = (error as Error).message || "未知错误";
      // 尝试解析后端返回的错误详情
      if (error instanceof Error && error.message === "Failed to fetch") {
        errorMessage = "请求超时或网络错误，请检查后端服务是否正常";
      }
      console.error(`检索对比槽位 ${index + 1} 错误:`, error);
      updateCompareSlot(index, {
        error: errorMessage,
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

  // 获取当前对比中使用的知识库列表
  const getCompareKbs = () => {
    return compareSlots
      .filter(s => s.kbId)
      .map(s => ({ id: s.kbId!, name: s.kbName || s.kbId! }));
  };

  // 打开结束对比 Dialog
  const openEndCompareDialog = () => {
    const kbs = getCompareKbs();
    // 默认全部保留
    setKbsToKeep(kbs.map(kb => kb.id));
    setEndCompareDialogOpen(true);
  };

  // 切换保留的知识库
  const toggleKbToKeep = (kbId: string) => {
    setKbsToKeep(prev => 
      prev.includes(kbId) 
        ? prev.filter(id => id !== kbId) 
        : [...prev, kbId]
    );
  };

  // 执行结束对比
  const executeEndCompare = async () => {
    if (!client || !groundId) return;
    
    setIsEndingCompare(true);
    try {
      const allKbs = getCompareKbs();
      const kbsToDelete = allKbs.filter(kb => !kbsToKeep.includes(kb.id));
      
      // 删除不保留的知识库
      for (const kb of kbsToDelete) {
        try {
          await client.deleteKnowledgeBase(kb.id);
        } catch {
          // 忽略单个删除失败
        }
      }
      
      // 从 localStorage 读取并更新 Pipeline 配置
      const pipelinesKey = `ground_pipelines_${groundId}`;
      const savedPipelines = localStorage.getItem(pipelinesKey);
      if (savedPipelines) {
        try {
          const pipelines = JSON.parse(savedPipelines) as { ingestedKbId: string | null }[];
          // 删除不保留的知识库（Pipeline 中的）
          for (const pipeline of pipelines) {
            if (pipeline.ingestedKbId && !kbsToKeep.includes(pipeline.ingestedKbId)) {
              try {
                await client.deleteKnowledgeBase(pipeline.ingestedKbId);
              } catch {
                // 忽略
              }
            }
          }
        } catch {
          // 忽略解析错误
        }
        // 清除 localStorage
        localStorage.removeItem(pipelinesKey);
      }
      
      // 删除 Ground
      try {
        await client.deleteGround(groundId);
      } catch {
        // 忽略
      }
      
      const keptCount = kbsToKeep.length;
      const deletedCount = kbsToDelete.length;
      
      toast.success(`已结束对比。保留 ${keptCount} 个知识库，删除 ${deletedCount} 个临时知识库`);
      setEndCompareDialogOpen(false);
      
      // 跳转到知识库列表
      router.push("/knowledge-bases");
    } catch (error) {
      toast.error(`结束对比失败: ${(error as Error).message}`);
    } finally {
      setIsEndingCompare(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* 顶部导航 */}
      <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
        <div className="flex items-center gap-4">
          {groundId ? (
            <Button variant="ghost" size="icon" onClick={() => router.push(`/compare/${groundId}`)}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
          ) : (
            <div className="w-10 h-10 flex items-center justify-center">
              <Search className="h-5 w-5 text-muted-foreground" />
            </div>
          )}
          <div>
            <h1 className="text-lg font-semibold flex items-center gap-2">
              检索对比
              {groundId ? (
                <Badge 
                  variant="outline" 
                  className="font-normal text-xs cursor-pointer hover:bg-muted transition-colors"
                  onClick={() => {
                    loadGroundList();
                    setGroundSelectorOpen(true);
                  }}
                >
                  <GitCompare className="h-3 w-3 mr-1" />
                  来自 {currentGround?.name || "Playground"}
                  <ChevronDown className="h-3 w-3 ml-1" />
                </Badge>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => {
                    loadGroundList();
                    setGroundSelectorOpen(true);
                  }}
                >
                  <Link className="h-3 w-3 mr-1" />
                  关联 Playground
                </Button>
              )}
            </h1>
            <p className="text-sm text-muted-foreground">对比不同知识库和检索策略的检索结果</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {groundId && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={openEndCompareDialog}
              className="text-orange-600 border-orange-300 hover:bg-orange-50"
            >
              <StopCircle className="h-4 w-4 mr-1" />
              结束对比
            </Button>
          )}
          {compareSlots.length < 4 && (
            <Button variant="outline" size="sm" onClick={addCompareSlot}>
              <Plus className="h-4 w-4 mr-1" />
              添加对比
            </Button>
          )}
          <Button 
            onClick={runAllCompareSlots} 
            disabled={isComparingAll || !compareQuery.trim() || compareSlots.every(s => !s.kbId)}
          >
            {isComparingAll ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                对比中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                运行对比
              </>
            )}
          </Button>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6 max-w-7xl mx-auto">
          {/* 查询输入 */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Search className="h-4 w-4" />
                查询问题
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="输入查询问题进行检索对比..."
                value={compareQuery}
                onChange={(e) => setCompareQuery(e.target.value)}
                className="min-h-[100px]"
              />
            </CardContent>
          </Card>
          
          {/* 对比槽位 */}
          <div className={`grid gap-4 ${compareSlots.length === 1 ? "grid-cols-1" : compareSlots.length === 2 ? "grid-cols-2" : compareSlots.length === 3 ? "grid-cols-3" : "grid-cols-4"}`}>
            {compareSlots.map((slot, index) => (
              <Card key={slot.id} className="relative">
                {/* 移除按钮 */}
                {compareSlots.length > 1 && (
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="absolute top-2 right-2 h-6 w-6"
                    onClick={() => removeCompareSlot(index)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
                
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">对比 {index + 1}</CardTitle>
                </CardHeader>
                
                <CardContent className="space-y-4">
                  {/* 知识库选择 */}
                  <div className="space-y-1.5">
                    <div className="text-xs font-medium text-muted-foreground">知识库</div>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="w-full justify-start h-9"
                      onClick={() => openCompareKbSelector(index)}
                    >
                      <Database className="h-3.5 w-3.5 mr-2 shrink-0" />
                      <span className="truncate">{slot.kbName || "选择知识库"}</span>
                    </Button>
                  </div>
                  
                  {/* 检索器 + Rerank 模型选择 */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <div className="text-xs font-medium text-muted-foreground">检索器</div>
                      <Select value={slot.retriever} onValueChange={(v) => updateSlotRetriever(index, v)}>
                        <SelectTrigger className="h-10">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {retrieverOptions.map((r) => (
                            <SelectItem key={r.name} value={r.name}>
                              {RETRIEVER_UI_CONFIG[r.name]?.label || r.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <div className="text-xs font-medium text-muted-foreground">Rerank (可选)</div>
                      <AllModelsSelector
                        type="rerank"
                        value={slot.rerankModel ?? undefined}
                        onChange={(val) => updateCompareSlot(index, { rerankModel: val })}
                        placeholder="不使用"
                        label=""
                      />
                    </div>
                  </div>
                  
                  {/* 检索器参数配置 */}
                  {RETRIEVER_UI_CONFIG[slot.retriever]?.params?.length > 0 && (
                    <Collapsible defaultOpen={false}>
                      <CollapsibleTrigger className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors w-full">
                        <Settings2 className="h-3 w-3" />
                        <span>检索器参数</span>
                        <ChevronRight className="h-3 w-3 ml-auto transition-transform data-[state=open]:rotate-90" />
                      </CollapsibleTrigger>
                      <CollapsibleContent className="pt-3 space-y-3">
                        {RETRIEVER_UI_CONFIG[slot.retriever].params.map((param) => (
                          <div key={param.key} className="space-y-1.5">
                            <div className="flex items-center justify-between">
                              <Label className="text-xs text-muted-foreground">{param.label}</Label>
                              {param.type === 'slider' && (
                                <span className="text-xs font-medium tabular-nums">
                                  {(slot.retrieverParams[param.key] as number ?? param.default).toFixed(1)}
                                </span>
                              )}
                            </div>
                            {param.type === 'number' && (
                              <Input
                                type="number"
                                min={param.min}
                                max={param.max}
                                value={slot.retrieverParams[param.key] as number ?? param.default}
                                onChange={(e) => updateCompareSlot(index, {
                                  retrieverParams: { ...slot.retrieverParams, [param.key]: Number(e.target.value) }
                                })}
                                className="h-8 text-xs"
                              />
                            )}
                            {param.type === 'slider' && (
                              <Slider
                                value={[slot.retrieverParams[param.key] as number ?? param.default as number]}
                                min={param.min ?? 0}
                                max={param.max ?? 1}
                                step={param.step ?? 0.1}
                                onValueChange={([v]) => updateCompareSlot(index, {
                                  retrieverParams: { ...slot.retrieverParams, [param.key]: v }
                                })}
                                className="py-1"
                              />
                            )}
                            {param.type === 'boolean' && (
                              <div className="flex items-center gap-2">
                                <Switch
                                  checked={slot.retrieverParams[param.key] as boolean ?? param.default as boolean}
                                  onCheckedChange={(v) => updateCompareSlot(index, {
                                    retrieverParams: { ...slot.retrieverParams, [param.key]: v }
                                  })}
                                />
                              </div>
                            )}
                            {param.type === 'select' && param.options && (
                              <Select
                                value={slot.retrieverParams[param.key] as string ?? param.default as string}
                                onValueChange={(v) => updateCompareSlot(index, {
                                  retrieverParams: { ...slot.retrieverParams, [param.key]: v }
                                })}
                              >
                                <SelectTrigger className="h-8 text-xs">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {param.options.map((opt) => (
                                    <SelectItem key={opt} value={opt} className="text-xs">{opt}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </div>
                        ))}
                      </CollapsibleContent>
                    </Collapsible>
                  )}
                  
                  {/* Top K */}
                  <div className="space-y-1.5">
                    <div className="text-xs font-medium text-muted-foreground">返回数量 (Top K)</div>
                    <Input
                      type="number"
                      min={1}
                      max={20}
                      value={slot.topK}
                      onChange={(e) => updateCompareSlot(index, { topK: Number(e.target.value) })}
                      className="h-9"
                    />
                  </div>
                  
                  {/* 单独运行按钮 */}
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="w-full"
                    onClick={() => runCompareSlot(index)}
                    disabled={slot.isLoading || !slot.kbId || !compareQuery.trim()}
                  >
                    {slot.isLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      "运行检索"
                    )}
                  </Button>
                  
                  {/* 结果展示 */}
                  <div className="border-t pt-4">
                    <div className="text-xs font-medium text-muted-foreground mb-2">
                      检索结果 {slot.results ? `(${slot.results.length} 条)` : ""}
                    </div>
                    {/* HyDE 假设答案或 MultiQuery 查询变体显示 */}
                    {(slot.hydeQueries && slot.hydeQueries.length > 0) && (
                      <Collapsible className="mb-3">
                        <CollapsibleTrigger className="flex items-center gap-2 text-xs text-primary hover:underline">
                          <Sparkles className="h-3 w-3" />
                          <span>LLM 生成的假设答案 ({slot.hydeQueries.length})</span>
                          <ChevronRight className="h-3 w-3" />
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2 space-y-2">
                          {slot.hydeQueries.map((query, idx) => (
                            <div key={idx} className="p-2 rounded border bg-primary/5 text-xs">
                              <div className="flex items-center gap-1 text-primary font-medium mb-1">
                                <Badge variant="outline" className="text-[10px] h-4">#{idx + 1}</Badge>
                              </div>
                              <div className="text-muted-foreground whitespace-pre-wrap line-clamp-4">{query}</div>
                            </div>
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    )}
                    {(slot.generatedQueries && slot.generatedQueries.length > 0) && (
                      <Collapsible className="mb-3">
                        <CollapsibleTrigger className="flex items-center gap-2 text-xs text-primary hover:underline">
                          <Sparkles className="h-3 w-3" />
                          <span>LLM 生成的查询变体 ({slot.generatedQueries.length})</span>
                          <ChevronRight className="h-3 w-3" />
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2 space-y-2">
                          {slot.generatedQueries.map((query, idx) => (
                            <div key={idx} className="p-2 rounded border bg-primary/5 text-xs">
                              <div className="flex items-center gap-1 text-primary font-medium mb-1">
                                <Badge variant="outline" className="text-[10px] h-4">#{idx + 1}</Badge>
                              </div>
                              <div className="text-muted-foreground">{query}</div>
                            </div>
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    )}
                    {slot.error ? (
                      <div className="text-xs text-destructive bg-destructive/10 rounded p-2">{slot.error}</div>
                    ) : slot.results ? (
                      <ScrollArea className="h-[300px]">
                        <div className="space-y-2 pr-2">
                          {slot.results.map((hit, idx) => {
                            const filename = String(hit.metadata?.source || hit.metadata?.file_name || "未知文件");
                            return (
                              <div 
                                key={idx} 
                                className="p-3 rounded-lg border bg-background cursor-pointer hover:bg-muted/50 transition-colors"
                                onClick={() => {
                                  setSelectedChunkHit({ hit, index: idx, retrieverType: slot.retriever });
                                  setChunkDetailOpen(true);
                                }}
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <Badge variant="secondary" className="text-xs">#{idx + 1}</Badge>
                                  <span className="text-xs text-muted-foreground font-medium">
                                    {(hit.score * 100).toFixed(1)}%
                                  </span>
                                </div>
                                <div className="text-sm line-clamp-3 text-muted-foreground mb-2">{hit.text}</div>
                                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                  <FileText className="h-3 w-3" />
                                  <span className="truncate">{filename}</span>
                                </div>
                              </div>
                            );
                          })}
                          {slot.results.length === 0 && (
                            <div className="text-xs text-muted-foreground text-center py-8">无结果</div>
                          )}
                        </div>
                      </ScrollArea>
                    ) : (
                      <div className="text-xs text-muted-foreground text-center py-8">
                        {slot.kbId ? "点击运行检索查看结果" : "请先选择知识库"}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* 知识库选择器 Dialog */}
      <Dialog open={compareKbSelectorOpen} onOpenChange={setCompareKbSelectorOpen}>
        <DialogContent className="max-w-md overflow-hidden">
          <DialogHeader>
            <DialogTitle>选择知识库</DialogTitle>
            <DialogDescription>选择要进行检索对比的知识库</DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[400px]">
            <div className="space-y-2">
              {isLoadingKbs ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : knowledgeBases.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-8">暂无可用知识库</div>
              ) : (
                knowledgeBases.map((kb) => (
                  <div
                    key={kb.id}
                    className="p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => selectCompareKb(kb)}
                  >
                    <div className="flex items-center gap-2">
                      <Database className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="font-medium truncate">{kb.name}</div>
                        {kb.description && (
                          <div className="text-xs text-muted-foreground truncate">{kb.description}</div>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {/* 结果详情 Dialog */}
      <Dialog open={chunkDetailOpen} onOpenChange={setChunkDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              检索结果详情
            </DialogTitle>
            <DialogDescription>
              {selectedChunkHit && (
                <span>
                  #{selectedChunkHit.index + 1} · {RETRIEVER_UI_CONFIG[selectedChunkHit.retrieverType]?.label || selectedChunkHit.retrieverType} · 
                  得分: {selectedChunkHit.hit.score < 0
                    ? `${selectedChunkHit.hit.score.toFixed(4)} (不相关)`
                    : selectedChunkHit.hit.score <= 1 
                      ? `${(selectedChunkHit.hit.score * 100).toFixed(2)}%` 
                      : selectedChunkHit.hit.score.toFixed(4)}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          {selectedChunkHit && (
            <ScrollArea className="max-h-[60vh]">
              <div className="space-y-4">
                <div>
                  <div className="text-sm font-medium mb-2">文本内容</div>
                  <div className="p-3 rounded-lg bg-muted/50 text-sm whitespace-pre-wrap">
                    {selectedChunkHit.hit.text}
                  </div>
                </div>
                {selectedChunkHit.hit.metadata && Object.keys(selectedChunkHit.hit.metadata).length > 0 && (
                  <div>
                    <div className="text-sm font-medium mb-2">元数据</div>
                    <div className="p-3 rounded-lg bg-muted/50 text-xs font-mono overflow-x-auto">
                      <pre>{JSON.stringify(selectedChunkHit.hit.metadata, null, 2) as string}</pre>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          )}
        </DialogContent>
      </Dialog>

      {/* Playground 选择器 Dialog */}
      <Dialog open={groundSelectorOpen} onOpenChange={setGroundSelectorOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{groundId ? "切换 Playground" : "关联 Playground"}</DialogTitle>
            <DialogDescription>
              {groundId ? "选择要切换的 Playground 实验" : "选择一个 Playground 并加载其知识库到对比槽位"}
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[400px]">
            <div className="space-y-2">
              {isLoadingGrounds ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : groundList.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-8">暂无 Playground 实验</div>
              ) : (
                groundList.map((ground) => (
                  <div
                    key={ground.ground_id}
                    className={`p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors ${
                      groundId === ground.ground_id ? "border-primary bg-primary/5" : ""
                    }`}
                    onClick={() => groundId ? selectGround(ground) : selectGroundAndLoadKbs(ground)}
                  >
                    <div className="flex items-center gap-2">
                      <GitCompare className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">{ground.name}</div>
                        {ground.description && (
                          <div className="text-xs text-muted-foreground truncate">{ground.description}</div>
                        )}
                      </div>
                      {ground.saved && (
                        <Badge variant="outline" className="text-xs shrink-0">已保存</Badge>
                      )}
                      {groundId === ground.ground_id && (
                        <Badge variant="secondary" className="text-xs shrink-0">当前</Badge>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {/* 知识库加载 Dialog */}
      <Dialog open={kbLoadDialogOpen} onOpenChange={(open) => {
        setKbLoadDialogOpen(open);
        if (!open) {
          setPendingGround(null);
          setSelectedKbsToLoad([]);
        }
      }}>
        <DialogContent className="max-w-lg overflow-hidden">
          <DialogHeader>
            <DialogTitle>选择要加载的知识库</DialogTitle>
            <DialogDescription>
              选择要加载到对比槽位的知识库（最多 4 个）
              {pendingGround && (
                <span className="block mt-1">
                  关联 Playground: <span className="font-medium">{pendingGround.name}</span>
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* 全选按钮 */}
            <div className="flex items-center justify-between">
              <Button
                variant="outline"
                size="sm"
                onClick={toggleSelectAllKbs}
                disabled={knowledgeBases.length === 0}
              >
                {selectedKbsToLoad.length === Math.min(knowledgeBases.length, 4) ? "取消全选" : "全选（最多4个）"}
              </Button>
              <span className="text-sm text-muted-foreground">
                已选 {selectedKbsToLoad.length} / {Math.min(knowledgeBases.length, 4)}
              </span>
            </div>
            
            <div className="h-[300px] overflow-hidden rounded-md border">
              <ScrollArea className="h-full">
                <div className="space-y-2 p-2">
                {isLoadingKbs ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : knowledgeBases.length === 0 ? (
                  <div className="text-sm text-muted-foreground text-center py-8">暂无知识库</div>
                ) : (
                  knowledgeBases.map((kb) => {
                    const isSelected = selectedKbsToLoad.includes(kb.id);
                    const isFromGround = pendingGround?.saved && pendingGround.knowledge_base_id === kb.id;
                    return (
                      <div
                        key={kb.id}
                        className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                          isSelected 
                            ? "border-primary bg-primary/5" 
                            : "hover:bg-muted/50"
                        }`}
                        onClick={() => toggleKbSelection(kb.id)}
                      >
                        <div className="flex items-center gap-2">
                          {isSelected ? (
                            <CheckSquare className="h-4 w-4 text-primary shrink-0" />
                          ) : (
                            <Square className="h-4 w-4 text-muted-foreground shrink-0" />
                          )}
                          <Database className="h-4 w-4 text-muted-foreground shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{kb.name}</div>
                            {kb.description && (
                              <div className="text-xs text-muted-foreground truncate">{kb.description}</div>
                            )}
                          </div>
                          {isFromGround && (
                            <Badge variant="outline" className="text-xs shrink-0">来自此 Playground</Badge>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
                </div>
              </ScrollArea>
            </div>
            
            {/* 操作按钮 */}
            <div className="flex justify-end gap-2 shrink-0 pt-2">
              <Button
                variant="outline"
                onClick={() => {
                  setKbLoadDialogOpen(false);
                  setPendingGround(null);
                  setSelectedKbsToLoad([]);
                }}
              >
                取消
              </Button>
              <Button
                onClick={confirmLoadKbs}
                disabled={selectedKbsToLoad.length === 0}
              >
                <Check className="h-4 w-4 mr-1" />
                确认加载 ({selectedKbsToLoad.length})
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 结束对比 Dialog */}
      <Dialog open={endCompareDialogOpen} onOpenChange={setEndCompareDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <StopCircle className="h-5 w-5 text-orange-500" />
              结束对比
            </DialogTitle>
            <DialogDescription>
              选择要保留的知识库，未选中的知识库将被删除。Playground 实验也将被清理。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* 知识库列表 */}
            <div className="space-y-2">
              <div className="text-sm font-medium">当前对比中的知识库：</div>
              {getCompareKbs().length === 0 ? (
                <div className="text-sm text-muted-foreground py-4 text-center">
                  暂无知识库
                </div>
              ) : (
                getCompareKbs().map((kb) => {
                  const isKeeping = kbsToKeep.includes(kb.id);
                  return (
                    <div
                      key={kb.id}
                      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                        isKeeping 
                          ? "border-green-500 bg-green-50" 
                          : "border-red-300 bg-red-50/50"
                      }`}
                      onClick={() => toggleKbToKeep(kb.id)}
                    >
                      <div className="flex items-center gap-2">
                        {isKeeping ? (
                          <CheckSquare className="h-4 w-4 text-green-600 shrink-0" />
                        ) : (
                          <Square className="h-4 w-4 text-red-400 shrink-0" />
                        )}
                        <Database className="h-4 w-4 text-muted-foreground shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">{kb.name}</div>
                        </div>
                        <Badge 
                          variant={isKeeping ? "default" : "destructive"} 
                          className="text-xs shrink-0"
                        >
                          {isKeeping ? "保留" : "删除"}
                        </Badge>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
            
            {/* 操作提示 */}
            <div className="text-xs text-muted-foreground p-2 bg-muted rounded">
              <div className="flex items-center gap-1">
                <Trash2 className="h-3 w-3" />
                <span>将删除 {getCompareKbs().length - kbsToKeep.length} 个知识库和 Playground 实验</span>
              </div>
            </div>
            
            {/* 操作按钮 */}
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setEndCompareDialogOpen(false)}
                disabled={isEndingCompare}
              >
                取消
              </Button>
              <Button
                variant="destructive"
                onClick={executeEndCompare}
                disabled={isEndingCompare}
              >
                {isEndingCompare ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    处理中...
                  </>
                ) : (
                  <>
                    <StopCircle className="h-4 w-4 mr-1" />
                    确认结束
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// 使用 Suspense 包装以支持 useSearchParams
export default function RetrievalComparePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    }>
      <RetrievalCompareContent />
    </Suspense>
  );
}
