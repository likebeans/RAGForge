"""
应用配置管理

使用 pydantic-settings 实现类型安全的配置管理：
- 支持从环境变量读取配置
- 支持从 .env 文件读取配置
- 提供默认值，确保开发环境开箱即用
- 配置项有完整的类型注解，IDE 可提供智能提示

配置优先级（从高到低）：
    1. 环境变量
    2. .env 文件
    3. 代码中的默认值

使用示例：
    from app.config import get_settings
    settings = get_settings()
    print(settings.database_url)
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    全局配置类
    
    所有配置项都可以通过环境变量覆盖，环境变量名与字段名相同（不区分大小写）。
    例如：DATABASE_URL 环境变量会覆盖 database_url 字段。
    """
    
    # ==================== 应用基础配置 ====================
    app_name: str = "RAG Pipeline Service"  # 应用名称，显示在 API 文档中
    environment: str = "dev"                 # 运行环境：dev/staging/prod
    log_level: str = "INFO"                  # 日志级别：DEBUG/INFO/WARNING/ERROR
    log_json: bool | None = None             # 日志格式：True=JSON，None=自动（prod用JSON）
    timezone: str = "Asia/Shanghai"          # 时区设置，默认中国时区
    
    # ==================== 数据库配置 ====================
    # PostgreSQL 连接字符串
    # 格式：postgresql+asyncpg://用户名:密码@主机:端口/数据库名
    # asyncpg 是异步 PostgreSQL 驱动，支持 async/await
    database_url: str = "postgresql+asyncpg://kb:kb@localhost:5435/kb"
    
    # ==================== API 认证配置 ====================
    api_key_prefix: str = "kb_sk_"           # API Key 前缀，用于识别和验证
    api_rate_limit_per_minute: int = 120     # 每分钟请求限制数
    api_rate_limit_window_seconds: int = 60  # 限流时间窗口（秒）
    
    # ==================== 管理员配置 ====================
    # 管理员 Token，用于访问 /admin/* 接口
    # 生产环境必须设置，建议使用随机生成的长字符串
    admin_token: str | None = None
    
    # ==================== Redis 配置（限流 + 缓存） ====================
    redis_url: str | None = None  # Redis 连接 URL，如 redis://localhost:6379/0
    # 未配置时使用内存限流（单实例模式）
    
    # 查询缓存配置
    redis_cache_enabled: bool = True  # 是否启用 Redis 查询缓存（需要 redis_url 配置）
    redis_cache_ttl: int = 300  # 查询缓存 TTL（秒），默认 5 分钟
    redis_cache_key_prefix: str = "rag:cache:"  # 缓存键前缀
    
    # 配置缓存配置
    redis_config_cache_ttl: int = 600  # KB 配置缓存 TTL（秒），默认 10 分钟
    
    # ==================== 向量数据库配置 (Qdrant) ====================
    qdrant_url: str = "http://localhost:6333"  # Qdrant 服务地址
    qdrant_api_key: str | None = None          # Qdrant API Key（云服务需要）
    qdrant_collection_prefix: str = "kb_"      # Collection 名称前缀，用于 collection 隔离模式
    qdrant_shared_collection: str = "kb_shared"  # 共享 Collection 名称，用于 partition 隔离模式
    
    # 自动隔离策略阈值：向量数超过此值自动切换到 collection 模式
    isolation_auto_threshold: int = 10000
    
    # ==================== 模型提供商 API 配置 ====================
    # 支持的提供商: openai / ollama / gemini / qwen / kimi / deepseek / zhipu
    # 
    # Ollama（本地部署）
    ollama_base_url: str = "http://localhost:11434"
    
    # OpenAI / Azure OpenAI
    openai_api_key: str | None = None
    openai_api_base: str | None = None  # 自定义端点，如 Azure
    openai_model: str = "gpt-3.5-turbo"  # 用于 HyDE/self_query 等需要对话模型的能力
    
    # Google Gemini
    gemini_api_key: str | None = None
    gemini_api_base: str = "https://generativelanguage.googleapis.com/v1beta"
    
    # 阿里云通义千问 (Qwen / DashScope)
    qwen_api_key: str | None = None
    qwen_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # 月之暗面 Kimi (Moonshot)
    kimi_api_key: str | None = None
    kimi_api_base: str = "https://api.moonshot.cn/v1"
    
    # DeepSeek
    deepseek_api_key: str | None = None
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    
    # 智谱 AI (Zhipu / GLM)
    zhipu_api_key: str | None = None
    zhipu_api_base: str = "https://open.bigmodel.cn/api/paas/v4"
    
    # Silicon Flow（硅基流动，聚合多种开源模型）
    siliconflow_api_key: str | None = None
    siliconflow_api_base: str = "https://api.siliconflow.cn/v1"
    
    # ==================== LLM 配置（对话模型） ====================
    # 用于 HyDE、Document Summary、Chunk Enrichment 等
    # provider: openai / ollama / gemini / qwen / kimi / deepseek / zhipu / siliconflow
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:14b"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    
    # ==================== Embedding 配置（向量化模型） ====================
    # provider: openai / ollama / gemini / qwen / zhipu / siliconflow
    embedding_provider: str = "ollama"
    embedding_model: str = "bge-m3"
    embedding_dim: int = 1024
    embedding_batch_size: int = 100
    # 常见维度：
    # - OpenAI text-embedding-3-small: 1536
    # - OpenAI text-embedding-3-large: 3072
    # - BGE-M3/BGE-Large-zh: 1024
    # - Qwen text-embedding-v3: 1024
    # - Gemini text-embedding-004: 768

    # ==================== Rerank 配置（重排模型） ====================
    # provider: ollama / cohere / zhipu / siliconflow / vllm / none
    rerank_provider: str = "ollama"
    rerank_model: str = "qllama/bge-reranker-large"
    rerank_top_k: int = 10  # 重排后返回的数量
    
    # Cohere Rerank（商业服务）
    cohere_api_key: str | None = None
    
    # vLLM Rerank（自部署 cross-encoder）
    vllm_rerank_base_url: str | None = None  # 如 http://192.168.1.235:8050
    
    # ==================== Milvus/Elasticsearch 配置 ====================
    milvus_host: str | None = None
    milvus_port: int | None = None
    milvus_user: str | None = None
    milvus_password: str | None = None
    milvus_secure: bool = False

    es_hosts: str | None = None  # 逗号分隔 hosts，例如 http://localhost:9200
    es_username: str | None = None
    es_password: str | None = None
    es_index_prefix: str = "kb_"
    es_index_mode: str = "shared"  # shared | per_kb
    es_request_timeout: int = 10
    es_bulk_batch_size: int = 500
    es_analyzer: str = "standard"  # 可选：ik_max_word 等
    es_refresh: str = "false"      # bulk refresh 策略：false/true/wait_for/auto
    es_max_retries: int = 2        # ES 请求重试次数
    
    # ==================== BM25 配置（内存实现，生产建议 ES/OpenSearch） ====================
    bm25_enabled: bool = True  # 可关闭内存 BM25，避免多实例不一致
    bm25_backend: str = "memory"  # memory / es

    # ==================== HyDE 配置 ====================
    hyde_enabled: bool = False          # 是否启用 HyDE（需要 LLM）
    hyde_num_queries: int = 4           # 生成的假设答案数量
    hyde_include_original: bool = True  # 是否保留原始查询
    hyde_max_tokens: int = 256          # 假设答案最大 token 数
    
    # ==================== Document Summary 配置 ====================
    doc_summary_enabled: bool = False      # 是否启用文档摘要（需要 LLM）
    doc_summary_min_tokens: int = 500      # 触发摘要生成的最小 token 数
    doc_summary_max_tokens: int = 500      # 摘要最大 token 数（qwen3 thinking 需要更多）
    doc_summary_model: str | None = None   # 摘要使用的模型，None 使用默认 openai_model
    
    # ==================== Chunk Enrichment 配置 ====================
    # 注意：Chunk Enrichment 默认关闭，因为会显著增加 LLM 调用成本
    chunk_enrichment_enabled: bool = False   # 是否启用 Chunk 增强（默认关闭）
    chunk_enrichment_max_tokens: int = 800   # 增强文本最大 token 数（qwen3 thinking 需要更多）
    chunk_enrichment_context_chunks: int = 1 # 上下文 chunk 数量（前后各 N 个）
    chunk_enrichment_model: str | None = None  # 增强使用的模型，None 使用默认 openai_model

    model_config = {
        "env_file": ".env",           # 从 .env 文件加载配置
        "env_file_encoding": "utf-8",  # .env 文件编码
        "extra": "ignore",
    }
    
    def get_llm_config(self) -> dict:
        """获取 LLM 配置（api_key, base_url, model）"""
        return self._get_provider_config(self.llm_provider, self.llm_model)
    
    def get_embedding_config(self) -> dict:
        """获取 Embedding 配置"""
        return self._get_provider_config(self.embedding_provider, self.embedding_model)
    
    def get_rerank_config(self) -> dict:
        """获取 Rerank 配置"""
        if self.rerank_provider == "none":
            return {"provider": "none"}
        if self.rerank_provider == "cohere":
            return {
                "provider": "cohere",
                "api_key": self.cohere_api_key,
                "model": self.rerank_model,
            }
        if self.rerank_provider == "vllm":
            return {
                "provider": "vllm",
                "base_url": self.vllm_rerank_base_url,
                "model": self.rerank_model,
            }
        return self._get_provider_config(self.rerank_provider, self.rerank_model)
    
    def _get_provider_config(self, provider: str, model: str) -> dict:
        """根据提供商获取配置"""
        provider = provider.lower()
        
        if provider == "ollama":
            return {
                "provider": "ollama",
                "base_url": self.ollama_base_url,
                "model": model,
            }
        elif provider == "openai":
            return {
                "provider": "openai",
                "api_key": self.openai_api_key,
                "base_url": self.openai_api_base,
                "model": model,
            }
        elif provider == "gemini":
            return {
                "provider": "gemini",
                "api_key": self.gemini_api_key,
                "base_url": self.gemini_api_base,
                "model": model,
            }
        elif provider == "qwen":
            return {
                "provider": "qwen",
                "api_key": self.qwen_api_key,
                "base_url": self.qwen_api_base,
                "model": model,
            }
        elif provider == "kimi":
            return {
                "provider": "kimi",
                "api_key": self.kimi_api_key,
                "base_url": self.kimi_api_base,
                "model": model,
            }
        elif provider == "deepseek":
            return {
                "provider": "deepseek",
                "api_key": self.deepseek_api_key,
                "base_url": self.deepseek_api_base,
                "model": model,
            }
        elif provider == "zhipu":
            return {
                "provider": "zhipu",
                "api_key": self.zhipu_api_key,
                "base_url": self.zhipu_api_base,
                "model": model,
            }
        elif provider == "siliconflow":
            return {
                "provider": "siliconflow",
                "api_key": self.siliconflow_api_key,
                "base_url": self.siliconflow_api_base,
                "model": model,
            }
        else:
            raise ValueError(f"未知的模型提供商: {provider}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    获取配置单例
    
    使用 @lru_cache 装饰器缓存配置实例，确保整个应用只创建一次 Settings 对象。
    这样做的好处：
    1. 避免重复解析 .env 文件
    2. 所有模块共享同一个配置实例
    3. 配置不可变，更加安全
    
    Returns:
        Settings: 全局配置实例
    """
    return Settings()
