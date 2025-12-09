from app.pipeline.registry import operator_registry


class ConfigValidationError(ValueError):
    pass


# 有效的 Embedding 提供商
VALID_EMBEDDING_PROVIDERS = {
    "ollama",
    "openai",
    "gemini",
    "qwen",
    "zhipu",
    "siliconflow",
    "deepseek",
    "kimi",
}


def validate_kb_config(cfg: dict, has_documents: bool = False) -> None:
    """
    校验 KB config 中的 chunker/retriever/embedding 配置。
    
    Args:
        cfg: 知识库配置字典
        has_documents: 知识库是否已有文档（用于校验 embedding 变更）
    
    Raises:
        ConfigValidationError: 配置无效时抛出
    """
    if not isinstance(cfg, dict):
        raise ConfigValidationError("config 必须是对象")

    ingestion = cfg.get("ingestion", {}) if isinstance(cfg.get("ingestion"), dict) else {}
    chunker = ingestion.get("chunker", {}) if isinstance(ingestion.get("chunker"), dict) else {}
    retr = cfg.get("query", {}) if isinstance(cfg.get("query"), dict) else {}
    retriever = retr.get("retriever", {}) if isinstance(retr.get("retriever"), dict) else {}

    chunker_name = chunker.get("name", "simple")
    if chunker_name not in operator_registry.list("chunker"):
        raise ConfigValidationError(f"未知 chunker: {chunker_name}")

    retriever_name = retriever.get("name", "dense")
    if retriever_name not in operator_registry.list("retriever"):
        raise ConfigValidationError(f"未知 retriever: {retriever_name}")

    store = ingestion.get("store", {}) if isinstance(ingestion.get("store"), dict) else {}
    store_type = store.get("type", "qdrant").lower()
    if store_type not in {"qdrant", "milvus", "es"}:
        raise ConfigValidationError(f"未知向量存储类型: {store_type}")
    if "skip_qdrant" in store and not isinstance(store.get("skip_qdrant"), bool):
        raise ConfigValidationError("skip_qdrant 必须为布尔值")
    
    # 校验 embedding 配置
    embedding = cfg.get("embedding", {}) if isinstance(cfg.get("embedding"), dict) else {}
    if embedding:
        _validate_embedding_config(embedding, has_documents)


def _validate_embedding_config(embedding: dict, has_documents: bool = False) -> None:
    """
    校验 Embedding 配置
    
    Args:
        embedding: embedding 配置字典
        has_documents: 知识库是否已有文档
    
    Raises:
        ConfigValidationError: 配置无效时抛出
    """
    provider = embedding.get("provider")
    model = embedding.get("model")
    dim = embedding.get("dim")
    
    # 校验 provider
    if provider is not None:
        if provider not in VALID_EMBEDDING_PROVIDERS:
            raise ConfigValidationError(
                f"未知 embedding 提供商: {provider}，"
                f"有效值: {', '.join(sorted(VALID_EMBEDDING_PROVIDERS))}"
            )
    
    # 校验 model（如果指定了 provider 则 model 也必须指定）
    if provider is not None and model is None:
        raise ConfigValidationError("指定 embedding.provider 时必须同时指定 embedding.model")
    
    # 校验 dim（可选但必须是正整数）
    if dim is not None:
        if not isinstance(dim, int) or dim <= 0:
            raise ConfigValidationError("embedding.dim 必须是正整数")
        if dim > 8192:
            raise ConfigValidationError("embedding.dim 不能超过 8192")
    
    # 如果知识库已有文档，警告用户更改 embedding 配置的风险
    if has_documents and (provider is not None or model is not None):
        raise ConfigValidationError(
            "知识库已有文档，不能更改 embedding 配置。"
            "更改 embedding 模型会导致向量维度不兼容，检索将无法正常工作。"
            "如需更改，请先删除所有文档或创建新的知识库。"
        )


def validate_embedding_config_compatibility(
    old_config: dict | None,
    new_config: dict | None,
    has_documents: bool,
) -> None:
    """
    校验 embedding 配置变更的兼容性
    
    Args:
        old_config: 旧的 KB 配置
        new_config: 新的 KB 配置
        has_documents: 知识库是否已有文档
    
    Raises:
        ConfigValidationError: 配置变更不兼容时抛出
    """
    if not has_documents:
        return  # 没有文档时可以自由变更
    
    # 如果新配置中没有明确包含 embedding 键，不做校验（允许只更新其他配置）
    if "embedding" not in (new_config or {}):
        return
    
    old_embedding = (old_config or {}).get("embedding", {}) or {}
    new_embedding = (new_config or {}).get("embedding", {}) or {}
    
    # 检查 provider 或 model 是否变更
    old_provider = old_embedding.get("provider")
    new_provider = new_embedding.get("provider")
    old_model = old_embedding.get("model")
    new_model = new_embedding.get("model")
    
    if old_provider != new_provider or old_model != new_model:
        # 如果新配置明确将 embedding 设为空，意味着回退到系统默认值
        if new_provider is None and new_model is None and (old_provider or old_model):
            raise ConfigValidationError(
                "知识库已有文档，移除 embedding 配置会导致使用系统默认值，"
                "可能与现有向量维度不兼容。如需更改，请先删除所有文档。"
            )
        
        if new_provider is not None or new_model is not None:
            raise ConfigValidationError(
                "知识库已有文档，不能更改 embedding 配置。"
                "更改 embedding 模型会导致向量维度不兼容。"
                "如需更改，请先删除所有文档或创建新的知识库。"
            )
