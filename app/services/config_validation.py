from app.pipeline.registry import operator_registry


class ConfigValidationError(ValueError):
    pass


def validate_kb_config(cfg: dict) -> None:
    """
    校验 KB config 中的 chunker/retriever 配置，确保算子已注册。
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
