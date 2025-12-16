"""
服务层内部参数模型

定义 Service 层函数的参数对象，与 API Schema 解耦。
提供参数验证、默认值和描述信息。

使用示例：
    from app.schemas.internal import RAGParams, RetrieveParams
    
    params = RAGParams(query="问题", kb_ids=["kb1"])
    result = await generate_rag_response(session, tenant_id, params)
"""

from pydantic import BaseModel, Field

from app.schemas.config import EmbeddingOverrideConfig, LLMConfig, RerankConfig, RetrieverConfig
from app.pipeline.postprocessors.context_window import ContextWindowConfig


class LLMParams(BaseModel):
    """LLM 调用参数"""
    
    system_prompt: str | None = Field(
        default=None,
        description="系统提示词，用于指导 LLM 的行为和角色"
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="温度参数，控制生成随机性（0-2，越低越确定性）"
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=8192,
        description="最大生成 token 数"
    )


class RetrieveParams(BaseModel):
    """
    检索服务参数
    
    用于 retrieve_chunks 函数，控制检索行为和结果过滤。
    注意：kbs 列表由调用方单独传入（已验证的知识库对象）。
    """
    
    query: str = Field(
        ...,
        min_length=1,
        description="查询语句"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="返回结果数量"
    )
    score_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="分数阈值，过滤低于此分数的结果"
    )
    metadata_filter: dict | None = Field(
        default=None,
        description="元数据过滤条件，精确匹配"
    )
    retriever_override: RetrieverConfig | None = Field(
        default=None,
        description="临时覆盖知识库配置的检索器"
    )
    context_window: ContextWindowConfig | None = Field(
        default=None,
        description="上下文窗口配置，None 表示使用默认配置"
    )
    rerank: bool = Field(
        default=False,
        description="是否启用 Rerank 后处理（使用配置的 Rerank 提供商）"
    )
    rerank_top_k: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Rerank 后返回的结果数量，默认等于 top_k"
    )
    rerank_override: RerankConfig | None = Field(
        default=None,
        description="临时覆盖 Rerank 配置（provider/model/api_key/base_url）"
    )
    embedding_override: EmbeddingOverrideConfig | None = Field(
        default=None,
        description="临时覆盖 Embedding 配置（provider/model/api_key/base_url），优先级：请求 > 知识库 > 环境变量"
    )
    
    def to_retriever_override_dict(self) -> dict | None:
        """转换 retriever_override 为 dict 格式"""
        if self.retriever_override is None:
            return None
        return {
            "name": self.retriever_override.name,
            "params": self.retriever_override.params or {},
        }


class RAGParams(BaseModel):
    """
    RAG 生成服务参数
    
    用于 generate_rag_response 函数，包含检索参数和 LLM 参数。
    """
    
    # 检索参数
    query: str = Field(
        ...,
        min_length=1,
        description="用户问题"
    )
    kb_ids: list[str] = Field(
        ...,
        min_length=1,
        description="要搜索的知识库 ID 列表"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="检索结果数量"
    )
    score_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="分数阈值，过滤低于此分数的检索结果"
    )
    retriever_override: RetrieverConfig | None = Field(
        default=None,
        description="临时覆盖知识库配置的检索器"
    )
    
    # LLM 参数
    system_prompt: str | None = Field(
        default=None,
        description="自定义系统提示词（覆盖默认 RAG 提示词）"
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="LLM 温度参数（0-2，越低越确定性）"
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=8192,
        description="LLM 最大生成 token 数"
    )
    llm_override: LLMConfig | None = Field(
        default=None,
        description="临时覆盖默认 LLM 配置"
    )
    embedding_override: EmbeddingOverrideConfig | None = Field(
        default=None,
        description="临时覆盖 Embedding 配置（仅 api_key/base_url 用于检索认证）"
    )
    
    # 控制选项
    include_sources: bool = Field(
        default=True,
        description="是否在响应中包含检索来源"
    )
    
    def to_retriever_override_dict(self) -> dict | None:
        """转换 retriever_override 为 dict 格式"""
        if self.retriever_override is None:
            return None
        return {
            "name": self.retriever_override.name,
            "params": self.retriever_override.params or {},
        }


class IngestionParams(BaseModel):
    """
    文档摄取服务参数
    
    用于 ingest_document 函数，控制文档处理行为。
    """
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="文档标题"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="文档内容（纯文本）"
    )
    metadata: dict | None = Field(
        default=None,
        description="扩展元数据，可包含任意键值对"
    )
    source: str | None = Field(
        default=None,
        description="来源类型，如 'pdf', 'url', 'manual' 等"
    )
    generate_doc_summary: bool = Field(
        default=True,
        description="是否自动生成文档摘要（调用 LLM）"
    )
    enrich_chunks: bool = Field(
        default=False,
        description="是否增强 chunks（添加上下文信息，调用 LLM）"
    )
    llm_config: dict | None = Field(
        default=None,
        description="LLM 配置（用于文档增强），优先级高于环境变量。包含 provider/model/api_key/base_url"
    )
    enricher_config: dict | None = Field(
        default=None,
        description="增强器配置，包含 name 和 params（如 context_window, include_headers）"
    )
    indexer_config: dict | None = Field(
        default=None,
        description="索引器配置，包含 name 和 params（如 max_depth, max_clusters, retrieval_mode）"
    )
    existing_doc_id: str | None = Field(
        default=None,
        description="已存在的文档 ID（用于后台异步入库场景，跳过创建文档记录步骤）"
    )
    # ACL 相关字段
    sensitivity_level: str = Field(
        default="internal",
        description="敏感度级别: public/internal/restricted"
    )
    acl_users: list[str] | None = Field(
        default=None,
        description="ACL 白名单用户列表"
    )
    acl_roles: list[str] | None = Field(
        default=None,
        description="ACL 白名单角色列表"
    )
    acl_groups: list[str] | None = Field(
        default=None,
        description="ACL 白名单用户组列表"
    )


class RetryChunksParams(BaseModel):
    """
    重试失败 Chunks 参数
    
    用于 retry_failed_chunks 函数。
    """
    
    kb_id: str = Field(
        ...,
        description="知识库 ID"
    )
    batch_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="每批处理的 chunk 数量"
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="最大重试次数"
    )
