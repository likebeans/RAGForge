/**
 * RAG Pipeline API 客户端
 */

const DEFAULT_BASE_URL = "http://localhost:8020";

export interface KnowledgeBaseConfig {
  chunking?: {
    method?: string;
    params?: Record<string, unknown>;
  };
  indexer?: {
    method?: string;
    params?: Record<string, unknown>;
  };
  enricher?: {
    method?: string;
    params?: Record<string, unknown>;
  };
  ingestion?: {
    chunker?: {
      name?: string;
      params?: Record<string, unknown>;
    };
    indexer?: {
      name?: string;
      params?: Record<string, unknown>;
    };
    enricher?: {
      name?: string;
      params?: Record<string, unknown>;
      generate_summary?: boolean;
      enrich_chunks?: boolean;
    };
    generate_summary?: boolean;
    enrich_chunks?: boolean;
  };
  embedding_provider?: string;
  embedding_model?: string;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  document_count?: number;
  config?: KnowledgeBaseConfig;
}

export interface Document {
  id: string;
  title: string;
  chunk_count: number;
  processing_status: string;  // pending/processing/completed/failed/interrupted
  created_at: string;
}

export interface DocumentDetail extends Document {
  knowledge_base_id: string;
  metadata?: Record<string, unknown> | null;
  source?: string | null;
  summary?: string | null;
  summary_status?: string | null;
  processing_log?: string | null;
}

export interface RetrieveResult {
  chunk_id: string;
  text: string;
  score: number;
  metadata?: Record<string, unknown>;
}

export interface ChunkHit extends RetrieveResult {
  knowledge_base_id?: string;
  document_id?: string;
  context_text?: string | null;
  context_before?: Record<string, unknown>[] | null;
  context_after?: Record<string, unknown>[] | null;
  hyde_queries?: string[] | null;
  hyde_queries_count?: number | null;
  generated_queries?: string[] | null;
  queries_count?: number | null;
}

export interface RAGResponse {
  answer: string;
  retrieval_count: number;
  model: {
    retriever: string;
    llm_provider?: string;
    llm_model?: string;
  };
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

// 对话相关类型
export interface Conversation {
  id: string;
  title?: string;
  knowledge_base_ids?: string[];
  message_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  retriever?: string;
  sources?: SourceItem[];
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface SourceItem {
  text: string;
  score: number;
  document_title?: string;
  chunk_id?: string;
  knowledge_base_id?: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

// API Key 相关类型
export interface APIKeyInfo {
  id: string;
  prefix: string;
  role: "admin" | "write" | "read";
  name?: string;
  rate_limit?: number;
  created_at: string;
  last_used_at?: string;
}

export interface CreateAPIKeyResponse {
  id: string;
  key: string;  // 仅创建时返回完整 key
  prefix: string;
  role: string;
  name?: string;
}

// 模型提供商相关类型
export interface ProviderConfig {
  name: string;
  description: string;
  base_url_required: boolean;
  api_key_required: boolean;
  default_base_url: string;
  supports: {
    llm: boolean;
    embedding: boolean;
    rerank: boolean;
  };
}

export interface ValidateProviderRequest {
  provider: string;
  api_key?: string;
  base_url?: string;
}

export interface ValidateProviderResponse {
  valid: boolean;
  message: string;
  models: {
    llm?: string[];
    embedding?: string[];
    rerank?: string[];
  };
}

export interface ModelListResponse {
  llm: string[];
  embedding: string[];
  rerank: string[];
}

export interface LLMOverride {
  provider: string;
  model: string;
  api_key?: string;
  base_url?: string;
}

export interface EmbeddingOverride {
  provider?: string;
  model?: string;
  api_key?: string;
  base_url?: string;
}

// Pipeline playground
export interface OperatorMeta {
  kind: string;
  name: string;
  label: string;
  description?: string;
  params_schema?: Record<string, unknown>;
}

export interface OperatorListResponse {
  chunkers: OperatorMeta[];
  retrievers: OperatorMeta[];
  query_transforms: OperatorMeta[];
  enrichers: OperatorMeta[];
  postprocessors: OperatorMeta[];
}

export interface ChunkPreview {
  chunk_id: string;
  text: string;
  metadata?: Record<string, unknown>;
}

export interface RetrievalPreview {
  retriever: string;
  latency_ms: number;
  rerank_applied?: boolean;
  results: ChunkHit[];
}

export interface RagPreview {
  answer: string;
  sources: ChunkHit[];
  model: {
    embedding_provider: string;
    embedding_model: string;
    llm_provider?: string;
    llm_model?: string;
    rerank_provider?: string;
    rerank_model?: string;
    retriever: string;
  };
  latency_ms: number;
}

// 分块预览
export interface ChunkPreviewItem {
  index: number;
  text: string;
  char_count: number;
  metadata?: Record<string, unknown>;  // 切分器输出的元数据（如 parent_id, child 等）
}

export interface ChunkPreviewResponse {
  document_id: string;
  document_title: string;
  chunker: string;
  total_chunks: number;
  chunks: ChunkPreviewItem[];
}

// Ground 文档上传响应
export interface GroundDocumentResponse {
  id: string;
  title: string;
  source: string | null;
  file_size: number;
}

// Ground 入库响应
export interface GroundIngestResult {
  title: string;
  document_id?: string;
  chunk_count?: number;
  success: boolean;
  error?: string;
}

export interface GroundIngestResponse {
  knowledge_base_id: string;
  knowledge_base_name: string;
  results: GroundIngestResult[];
  total: number;
  succeeded: number;
  failed: number;
}

// ============================================================
// 增强预览 API 类型
// ============================================================

export interface PreviewSummaryResponse {
  summary: string;
  content_length: number;
  summary_length: number;
}

export interface EnrichedChunkResult {
  original_text: string;
  enriched_text: string;
  status: "completed" | "failed" | "skipped";
}

export interface PreviewChunkEnrichmentResponse {
  results: EnrichedChunkResult[];
  total: number;
  succeeded: number;
  failed: number;
}

export interface BatchIngestResult {
  title: string;
  document_id?: string;
  chunk_count?: number;
  success: boolean;
  error?: string;
}

export interface BatchIngestResponse {
  results: BatchIngestResult[];
  total: number;
  succeeded: number;
  failed: number;
}

// Playground 配置类型
export interface RetrieverConfig {
  name: string;
  params?: Record<string, unknown>;
}

export interface RerankConfig {
  provider?: string;
  model?: string;
  api_key?: string;
  base_url?: string;
}

export interface PlaygroundRunRequest {
  query: string;
  knowledge_base_ids: string[];
  top_k?: number;
  score_threshold?: number;
  retriever?: RetrieverConfig;
  rerank?: boolean;
  rerank_override?: RerankConfig;
  rerank_top_k?: number;
  chunker?: string;
  chunker_params?: Record<string, unknown>;
  chunk_preview_text?: string;
  llm_override?: LLMOverride;
  embedding_override?: EmbeddingOverride;
}

export interface PlaygroundRunResponse {
  query: string;
  knowledge_base_ids: string[];
  chunk_preview?: ChunkPreview[];
  query_transform?: {
    original_query: string;
    generated_queries?: string[];
    hyde_prompts?: string[];
  };
  retrieval: RetrievalPreview;
  rag: RagPreview;
  metrics?: Record<string, number>;
}

// Ground (playground) types
export interface GroundInfo {
  ground_id: string;
  knowledge_base_id: string;
  name: string;
  description?: string;
  created_at: string;
  document_count: number;
  saved: boolean;
}

// SSE 事件类型
export type SSEEventType = "sources" | "content" | "done" | "error";

class APIClient {
  private baseUrl: string;
  private apiKey: string;

  constructor(apiKey: string, baseUrl: string = DEFAULT_BASE_URL) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    method: string,
    endpoint: string,
    data?: unknown,
    isFormData = false
  ): Promise<T> {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.apiKey}`,
    };

    if (!isFormData) {
      headers["Content-Type"] = "application/json";
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method,
      headers,
      body: isFormData ? (data as FormData) : data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      // detail 可能是字符串或对象
      let message = `HTTP ${response.status}`;
      if (error.detail) {
        message = typeof error.detail === "string" 
          ? error.detail 
          : error.detail.detail || JSON.stringify(error.detail);
      }
      throw new Error(message);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // 健康检查
  async health(): Promise<{ status: string }> {
    const response = await fetch(`${this.baseUrl}/health`);
    return response.json();
  }

  // 知识库管理
  async listKnowledgeBases(includeGround = false): Promise<{ items: KnowledgeBase[]; total: number }> {
    const query = includeGround ? "?include_ground=true" : "";
    return this.request("GET", `/v1/knowledge-bases${query}`);
  }

  async createKnowledgeBase(
    name: string,
    description?: string,
    config?: Record<string, unknown>
  ): Promise<KnowledgeBase> {
    return this.request("POST", "/v1/knowledge-bases", { name, description, config });
  }

  async deleteKnowledgeBase(id: string): Promise<void> {
    return this.request("DELETE", `/v1/knowledge-bases/${id}`);
  }

  async updateKnowledgeBase(
    id: string,
    data: {
      name?: string;
      description?: string;
      config?: Record<string, unknown>;
    }
  ): Promise<KnowledgeBase> {
    return this.request("PATCH", `/v1/knowledge-bases/${id}`, data);
  }

  // 文档管理
  async listDocuments(kbId: string): Promise<{ items: Document[]; total: number }> {
    return this.request("GET", `/v1/knowledge-bases/${kbId}/documents`);
  }

  async uploadDocument(kbId: string, title: string, content: string): Promise<Document> {
    return this.request("POST", `/v1/knowledge-bases/${kbId}/documents`, { title, content });
  }

  async uploadFile(kbId: string, file: File): Promise<Document> {
    const formData = new FormData();
    formData.append("file", file);
    return this.request("POST", `/v1/knowledge-bases/${kbId}/documents/upload`, formData, true);
  }

  async deleteDocument(docId: string): Promise<void> {
    return this.request("DELETE", `/v1/documents/${docId}`);
  }

  async getDocument(docId: string): Promise<DocumentDetail> {
    return this.request("GET", `/v1/documents/${docId}`);
  }

  async interruptDocument(docId: string): Promise<{ status: string; document_id: string }> {
    return this.request("POST", `/v1/documents/${docId}/interrupt`);
  }

  // 检索
  async retrieve(
    query: string,
    kbIds: string[],
    topK = 5,
    retriever = "hybrid"
  ): Promise<{ results: RetrieveResult[]; model: Record<string, unknown> }> {
    return this.request("POST", "/v1/retrieve", {
      query,
      knowledge_base_ids: kbIds,
      top_k: topK,
      retriever_override: retriever !== "dense" ? { name: retriever } : undefined,
    });
  }

  // RAG 生成
  async rag(
    query: string,
    kbIds: string[],
    topK = 5,
    retriever = "hybrid"
  ): Promise<RAGResponse> {
    return this.request("POST", "/v1/rag", {
      query,
      knowledge_base_ids: kbIds,
      top_k: topK,
      retriever_override: retriever !== "dense" ? { name: retriever } : undefined,
    });
  }

  // OpenAI 兼容接口
  async chatCompletions(
    messages: ChatMessage[],
    kbIds: string[],
    topK = 5
  ): Promise<{ choices: { message: ChatMessage }[]; usage: Record<string, number> }> {
    return this.request("POST", "/v1/chat/completions", {
      model: "gpt-4",
      messages,
      knowledge_base_ids: kbIds,
      top_k: topK,
    });
  }

  // 对话管理
  async listConversations(
    page = 1,
    pageSize = 20
  ): Promise<{ items: Conversation[]; total: number; page: number; page_size: number }> {
    return this.request("GET", `/v1/conversations?page=${page}&page_size=${pageSize}`);
  }

  async createConversation(
    title?: string,
    kbIds?: string[]
  ): Promise<Conversation> {
    return this.request("POST", "/v1/conversations", {
      title,
      knowledge_base_ids: kbIds,
    });
  }

  async getConversation(id: string): Promise<ConversationDetail> {
    return this.request("GET", `/v1/conversations/${id}`);
  }

  async updateConversation(
    id: string,
    title?: string,
    kbIds?: string[]
  ): Promise<Conversation> {
    return this.request("PATCH", `/v1/conversations/${id}`, {
      title,
      knowledge_base_ids: kbIds,
    });
  }

  async deleteConversation(id: string): Promise<void> {
    return this.request("DELETE", `/v1/conversations/${id}`);
  }

  async addMessage(
    conversationId: string,
    role: "user" | "assistant",
    content: string,
    retriever?: string,
    sources?: SourceItem[]
  ): Promise<Message> {
    return this.request("POST", `/v1/conversations/${conversationId}/messages`, {
      role,
      content,
      retriever,
      sources,
    });
  }

  // SSE 流式 RAG
  streamRAG(
    query: string,
    kbIds: string[],
    retriever = "hybrid",
    topK = 5,
    onSources: (sources: SourceItem[]) => void,
    onContent: (chunk: string) => void,
    onDone: () => void,
    onError: (error: string) => void,
    options?: { llmOverride?: LLMOverride }
  ): AbortController {
    const controller = new AbortController();
    const { llmOverride } = options || {};

    const run = async () => {
      try {
        const response = await fetch(`${this.baseUrl}/v1/rag/stream`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${this.apiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query,
            knowledge_base_ids: kbIds,
            retriever,
            top_k: topK,
            llm_override: llmOverride,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const error = await response.json().catch(() => ({ detail: response.statusText }));
          throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";
        let currentEventType = "content"; // 默认事件类型

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEventType = line.slice(7).trim();
              continue;
            }
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              
              // 根据事件类型显式处理
              if (currentEventType === "done" || data === "[DONE]") {
                onDone();
                return;
              }
              
              if (currentEventType === "error") {
                try {
                  const parsed = JSON.parse(data);
                  onError(parsed.error || data);
                } catch {
                  onError(data);
                }
                return;
              }
              
              if (currentEventType === "sources") {
                try {
                  const parsed = JSON.parse(data);
                  if (Array.isArray(parsed)) {
                    onSources(parsed);
                  }
                } catch {
                  console.warn("Failed to parse sources:", data);
                }
                continue;
              }
              
              // content 事件或默认处理
              if (data && currentEventType === "content") {
                const text = data.replace(/\\n/g, "\n").replace(/\\r/g, "\r");
                if (text) onContent(text);
              }
            }
          }
        }
        onDone();
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          onError((error as Error).message);
        }
      }
    };

    run();
    return controller;
  }

  // API Key 管理（需要 admin 角色）
  async listAPIKeys(): Promise<{ items: APIKeyInfo[] }> {
    return this.request("GET", "/v1/api-keys");
  }

  async createAPIKey(
    role: "admin" | "write" | "read",
    name?: string,
    rateLimit?: number
  ): Promise<CreateAPIKeyResponse> {
    return this.request("POST", "/v1/api-keys", {
      role,
      name,
      rate_limit: rateLimit,
    });
  }

  async deleteAPIKey(keyId: string): Promise<void> {
    return this.request("DELETE", `/v1/api-keys/${keyId}`);
  }

  // 获取当前 Key 信息
  async getCurrentKeyInfo(): Promise<{ role: string; tenant_id: string }> {
    return this.request("GET", "/v1/me");
  }

  // 模型提供商管理
  async listProviders(): Promise<Record<string, ProviderConfig>> {
    return this.request("GET", "/v1/model-providers/");
  }

  async validateProvider(
    provider: string,
    apiKey?: string,
    baseUrl?: string
  ): Promise<ValidateProviderResponse> {
    return this.request("POST", "/v1/model-providers/validate", {
      provider,
      api_key: apiKey,
      base_url: baseUrl,
    });
  }

  async getProviderModels(
    provider: string,
    apiKey?: string,
    baseUrl?: string
  ): Promise<ModelListResponse> {
    let endpoint = `/v1/model-providers/${provider}/models`;
    const params = new URLSearchParams();
    if (apiKey) params.append("api_key", apiKey);
    if (baseUrl) params.append("base_url", baseUrl);
    if (params.toString()) endpoint += `?${params.toString()}`;
    return this.request("GET", endpoint);
  }

  // Pipeline playground
  async listOperators(): Promise<OperatorListResponse> {
    return this.request("GET", "/v1/pipeline/operators");
  }

  async runPlayground(payload: PlaygroundRunRequest): Promise<PlaygroundRunResponse> {
    return this.request("POST", "/v1/pipeline/playground/run", payload);
  }

  // Grounds
  async listGrounds(): Promise<{ items: GroundInfo[]; total: number }> {
    return this.request("GET", "/v1/grounds");
  }

  async createGround(name?: string, description?: string): Promise<GroundInfo> {
    return this.request("POST", "/v1/grounds", { name, description });
  }

  async getGround(groundId: string): Promise<GroundInfo> {
    return this.request("GET", `/v1/grounds/${groundId}`);
  }

  async deleteGround(groundId: string): Promise<void> {
    return this.request("DELETE", `/v1/grounds/${groundId}`);
  }

  async saveGround(groundId: string): Promise<GroundInfo> {
    return this.request("POST", `/v1/grounds/${groundId}/save`);
  }

  // 分块预览
  async previewChunks(
    groundId: string,
    documentId: string,
    chunker: string = "recursive",
    chunkerParams?: Record<string, unknown>
  ): Promise<ChunkPreviewResponse> {
    return this.request("POST", `/v1/grounds/${groundId}/chunk-preview`, {
      document_id: documentId,
      chunker,
      chunker_params: chunkerParams,
    });
  }

  // Ground 专用文档上传（只保存原始内容，不做切分处理）
  async uploadGroundDocument(groundId: string, file: File): Promise<GroundDocumentResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return this.request("POST", `/v1/grounds/${groundId}/documents/upload`, formData, true);
  }

  /**
   * 将 Ground 中的文档入库到新知识库
   */
  async ingestGround(
    groundId: string,
    targetKbName: string,
    options?: {
      targetKbDescription?: string;
      chunker?: { name: string; params?: Record<string, unknown> };
      indexer?: { name: string; params?: Record<string, unknown> };
      enricher?: { name: string; params?: Record<string, unknown> };
      generateSummary?: boolean;
      enrichChunks?: boolean;
      embeddingProvider?: string;
      embeddingModel?: string;
      embeddingApiKey?: string;
      embeddingBaseUrl?: string;
      // LLM 配置（用于文档增强）
      llmProvider?: string;
      llmModel?: string;
      llmApiKey?: string;
      llmBaseUrl?: string;
    }
  ): Promise<GroundIngestResponse> {
    return this.request("POST", `/v1/grounds/${groundId}/ingest`, {
      target_kb_name: targetKbName,
      target_kb_description: options?.targetKbDescription,
      chunker: options?.chunker,
      indexer: options?.indexer,
      enricher: options?.enricher,
      generate_summary: options?.generateSummary ?? false,
      enrich_chunks: options?.enrichChunks ?? false,
      embedding_provider: options?.embeddingProvider,
      embedding_model: options?.embeddingModel,
      embedding_api_key: options?.embeddingApiKey,
      embedding_base_url: options?.embeddingBaseUrl,
      llm_provider: options?.llmProvider,
      llm_model: options?.llmModel,
      llm_api_key: options?.llmApiKey,
      llm_base_url: options?.llmBaseUrl,
    });
  }

  // ============================================================
  // 增强预览 API
  // ============================================================

  /**
   * 预览文档摘要
   */
  async previewSummary(
    content: string,
    title?: string,
    options?: {
      maxTokens?: number;
      summaryLength?: "short" | "medium" | "long";
    }
  ): Promise<PreviewSummaryResponse> {
    return this.request("POST", "/v1/enrichment/preview-summary", {
      content,
      title,
      summary_length: options?.summaryLength,
      max_tokens: options?.maxTokens ?? 300,
    });
  }

  /**
   * 预览 Chunk 增强
   * @param llmConfig 可选的 LLM 配置，优先级高于环境变量
   */
  async previewChunkEnrichment(
    chunks: string[],
    docTitle?: string,
    docSummary?: string,
    maxTokens: number = 512,
    llmConfig?: {
      provider: string;
      model: string;
      api_key?: string;
      base_url?: string;
    }
  ): Promise<PreviewChunkEnrichmentResponse> {
    return this.request("POST", "/v1/enrichment/preview-chunk-enrichment", {
      chunks,
      doc_title: docTitle,
      doc_summary: docSummary,
      max_tokens: maxTokens,
      llm_config: llmConfig,
    });
  }

  /**
   * 高级批量入库（支持自定义配置）
   */
  async advancedBatchIngest(
    kbId: string,
    documents: Array<{
      title: string;
      content: string;
      metadata?: Record<string, unknown>;
      source?: string;
    }>,
    options?: {
      chunker?: { name: string; params?: Record<string, unknown> };
      generateSummary?: boolean;
      enrichChunks?: boolean;
      embeddingProvider?: string;
      embeddingModel?: string;
    }
  ): Promise<BatchIngestResponse> {
    return this.request("POST", `/v1/knowledge-bases/${kbId}/documents/advanced-batch`, {
      documents,
      chunker: options?.chunker,
      generate_summary: options?.generateSummary ?? false,
      enrich_chunks: options?.enrichChunks ?? false,
      embedding_provider: options?.embeddingProvider,
      embedding_model: options?.embeddingModel,
    });
  }
}

export function createClient(apiKey: string, baseUrl?: string): APIClient {
  return new APIClient(apiKey, baseUrl);
}

export type { APIClient };
