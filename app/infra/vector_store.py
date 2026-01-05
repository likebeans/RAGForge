"""
向量数据库模块 (Vector Store)

封装 Qdrant 向量数据库的操作，提供：
- 向量存储（upsert）
- 相似度搜索（search）
- 多租户隔离（支持 Partition 和 Collection 两种模式）

隔离策略：
- partition: 所有租户共享一个 Collection，按 tenant_id 过滤（节省资源，适合小客户）
- collection: 每个租户独立 Collection（性能更好，适合中大客户）
- auto: 根据数据量自动选择（<10K 用 partition）

特性：
- 使用 AsyncQdrantClient，不阻塞事件循环
- 使用真实 Embedding（OpenAI/确定性哈希）
- 支持批量操作
"""

from __future__ import annotations

import logging
import time
import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Iterable, Literal
from contextvars import ContextVar

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.config import get_settings
from app.infra.embeddings import get_embedding, get_embeddings, get_embeddings_with_config
from app.infra.metrics import metrics_collector

logger = logging.getLogger(__name__)


# 隔离策略类型
IsolationStrategy = Literal["partition", "collection", "auto"]

# 常见 Embedding 模型维度映射
EMBEDDING_DIM_MAP: dict[str, int] = {
    # OpenAI
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    # OpenAI 兼容/常见别名
    "text-embedding-3-small-v1": 1536,
    "text-embedding-3-large-v1": 3072,
    # BGE 系列
    "bge-m3": 1024,
    "bge-large-zh": 1024,
    "bge-large-zh-v1.5": 1024,
    "bge-base-zh": 768,
    "bge-small-zh": 512,
    # 常见开源 embedding（Ollama 等）
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    # Qwen 系列 (通过 SiliconFlow)
    "Qwen/Qwen3-Embedding-8B": 4096,
    "Qwen/Qwen3-Embedding-4B": 2560,
    "Qwen/Qwen3-Embedding-0.6B": 1024,
    "text-embedding-v3": 1024,
    "text-embedding-v2": 1536,
    "qwen3-embedding": 4096,
    # Gemini
    "text-embedding-004": 768,
    "embedding-001": 768,
    # 智谱
    "embedding-2": 1024,
    "embedding-3": 2048,
    # DeepSeek
    "deepseek-embedding": 1024,
    "deepseek-embed": 1024,
    # SiliconFlow 其他模型
    "BAAI/bge-m3": 1024,
    "BAAI/bge-large-zh-v1.5": 1024,
    "netease-youdao/bce-embedding-base_v1": 768,
    "Pro/BAAI/bge-m3": 1024,
}

# ACL 过滤上下文（每个请求独立）
_acl_filter_ctx: ContextVar[dict | None] = ContextVar("acl_filter_ctx", default=None)


def _slugify_model(model: str | None) -> str:
    """将模型名转为向量字段安全字符串"""
    if not model:
        return "default"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_").lower()
    return slug or "default"


def get_vector_field_name(model: str | None, dim: int | None) -> str:
    """
    根据模型名和维度生成向量字段名，保证同一 collection 可容纳不同模型的向量。
    
    生成规则：
    - 如果没有模型名或维度，返回 "default"
    - 如果维度是常见的默认维度（1024），使用简化名称
    - 否则包含完整的模型名和维度信息
    """
    if not model and not dim:
        return "default"
    
    base = _slugify_model(model)
    
    # 对于常见的默认维度，使用简化名称
    if dim == 1024 and base in ("bge_m3", "text_embedding_v3", "default"):
        return f"vec_{base}"
    
    # 对于其他情况，包含维度信息以避免冲突
    return f"vec_{base}_{dim}" if dim else f"vec_{base}"


def _lookup_embedding_dim(model: str | None) -> int | None:
    """查找模型维度（不回退默认值）。"""
    if not model:
        return None
    # 直接匹配
    if model in EMBEDDING_DIM_MAP:
        return EMBEDDING_DIM_MAP[model]
    model_lower = model.lower()
    # 不区分大小写匹配
    for key, dim in EMBEDDING_DIM_MAP.items():
        if key.lower() == model_lower:
            return dim
    # 部分匹配（模型名可能带前缀/版本）
    for key, dim in EMBEDDING_DIM_MAP.items():
        key_lower = key.lower()
        if key_lower in model_lower or model_lower in key_lower:
            return dim
    return None


def _register_embedding_dim(model: str | None, dim: int | None) -> None:
    """将实际维度写入映射表（避免后续维度不一致）。"""
    if not model or not dim:
        return
    mapped = _lookup_embedding_dim(model)
    if mapped is None:
        EMBEDDING_DIM_MAP[model] = dim
        return
    if mapped != dim:
        logger.warning(
            f"embedding 维度映射不一致: model={model} mapped={mapped} actual={dim}, 使用实际维度"
        )
        EMBEDDING_DIM_MAP[model] = dim


def _resolve_embedding_dim(
    model: str | None,
    vector_dim: int | None,
    default_dim: int,
) -> int:
    """优先使用实际向量维度，必要时回退到已知映射或默认值。"""
    mapped = _lookup_embedding_dim(model)
    if vector_dim:
        if mapped is None or mapped != vector_dim:
            _register_embedding_dim(model, vector_dim)
        return vector_dim
    return mapped if mapped is not None else default_dim


def set_acl_filter_ctx(acl_filter: dict | None):
    """在当前上下文设置 ACL 过滤条件"""
    return _acl_filter_ctx.set(acl_filter)


def reset_acl_filter_ctx(token) -> None:
    """重置当前上下文的 ACL 过滤条件"""
    _acl_filter_ctx.reset(token)


def get_acl_filter_ctx() -> dict | None:
    """获取当前上下文的 ACL 过滤条件"""
    return _acl_filter_ctx.get()


def get_embedding_dim(model: str | None, default: int = 1024) -> int:
    """根据模型名称获取向量维度"""
    dim = _lookup_embedding_dim(model)
    return dim if dim is not None else default


@dataclass
class VectorRecord:
    """向量记录：封装向量数据库中的一条记录"""
    chunk_id: str           # 片段 ID
    tenant_id: str          # 租户 ID
    knowledge_base_id: str  # 知识库 ID
    text: str               # 原始文本
    metadata: dict          # 元数据


@lru_cache(maxsize=1)
def _get_async_client() -> AsyncQdrantClient:
    """获取异步 Qdrant 客户端（单例）"""
    settings = get_settings()
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=10.0,
        prefer_grpc=False,
        # 测试/开发环境避免版本检测与 http+api_key 警告
        check_compatibility=False,
    )


class AsyncQdrantVectorStore:
    """
    异步 Qdrant 向量存储
    
    多租户隔离策略：
    - partition: 所有租户共享一个 Collection，按 tenant_id payload 过滤
    - collection: 每个租户独立 Collection（{prefix}{tenant_id}）
    - auto: 根据配置阈值自动选择
    
    注意：所有方法都是异步的，需要使用 await 调用
    """

    def __init__(self, client: AsyncQdrantClient | None = None):
        self._client = client
        self._settings = get_settings()
        self.dim = self._settings.embedding_dim
        self.collection_prefix = self._settings.qdrant_collection_prefix
        self.shared_collection = self._settings.qdrant_shared_collection
        self.auto_threshold = self._settings.isolation_auto_threshold
        self._collection_cache: set[str] = set()  # 缓存已创建的 collection
        # 租户隔离策略缓存：{tenant_id: "partition" | "collection"}
        self._tenant_strategy_cache: dict[str, str] = {}

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = _get_async_client()
        return self._client

    def _collection_name_for_tenant(self, tenant_id: str) -> str:
        """Collection 隔离模式下的 Collection 名称"""
        return f"{self.collection_prefix}{tenant_id}"

    def _get_effective_strategy(self, tenant_id: str, strategy: IsolationStrategy) -> str:
        """
        获取有效的隔离策略
        
        Args:
            tenant_id: 租户 ID
            strategy: 配置的策略 (partition/collection/auto)
        
        Returns:
            实际使用的策略 ("partition" 或 "collection")
        """
        if strategy in ("partition", "collection"):
            return strategy
        
        # auto 模式：检查缓存
        if tenant_id in self._tenant_strategy_cache:
            return self._tenant_strategy_cache[tenant_id]
        
        # auto 模式默认用 partition，可通过 migrate_to_collection 升级
        return "partition"

    async def _ensure_collection(
        self,
        tenant_id: str,
        strategy: IsolationStrategy = "auto",
        embedding_dim: int | None = None,
        vector_name: str | None = None,
        ensure_vector: bool = True,
    ) -> tuple[str, str, str]:
        """
        确保 Collection 存在（带缓存）
        
        Args:
            tenant_id: 租户 ID
            strategy: 隔离策略
            embedding_dim: 向量维度（可选，不提供则使用默认值）
        
        Returns:
            (collection_name, effective_strategy)
        """
        effective = self._get_effective_strategy(tenant_id, strategy)
        dim = embedding_dim or self.dim
        vector_name = vector_name or get_vector_field_name(None, dim)
        
        if effective == "partition":
            # 保持单 collection，使用多向量字段区分模型
            name = self.shared_collection
        else:
            name = self._collection_name_for_tenant(tenant_id)
        
        # 检查缓存
        if name in self._collection_cache:
            # 确保向量字段存在
            if ensure_vector:
                try:
                    vector_name = await self._ensure_vector_field(name, vector_name, dim)
                except Exception as exc:
                    # 无法追加向量字段时，回退到按维度分 collection
                    fallback = f"{name}_{dim}"
                    logger.warning(f"{name} 向量字段不可用，回退到 {fallback}: {exc}")
                    name = fallback
                    vector_name = await self._ensure_named_collection(name, dim, vector_name)
            return name, effective, vector_name
        
        # 如果 collection 已存在，确保字段存在
        try:
            await self.client.get_collection(name)
            self._collection_cache.add(name)
            if ensure_vector:
                try:
                    vector_name = await self._ensure_vector_field(name, vector_name, dim)
                except Exception as exc:
                    fallback = f"{name}_{dim}"
                    logger.warning(f"{name} 向量字段不可用，回退到 {fallback}: {exc}")
                    name = fallback
                    vector_name = await self._ensure_named_collection(name, dim, vector_name)
            return name, effective, vector_name
        except Exception:
            pass
        
        # 创建 collection，默认包含当前向量字段
        try:
            await self.client.create_collection(
                collection_name=name,
                vectors_config={vector_name: models.VectorParams(size=dim, distance=models.Distance.COSINE)},
            )
            self._collection_cache.add(name)
            logger.info(f"创建 Collection: {name} (策略: {effective}, 维度: {dim}, 向量字段: {vector_name})")
        except Exception as e:
            # 可能被并发请求创建
            logger.debug(f"Collection 可能已存在: {e}")
            self._collection_cache.add(name)
            if ensure_vector:
                try:
                    vector_name = await self._ensure_vector_field(name, vector_name, dim)
                except Exception as exc:
                    fallback = f"{name}_{dim}"
                    logger.warning(f"{name} 向量字段不可用，回退到 {fallback}: {exc}")
                    name = fallback
                    vector_name = await self._ensure_named_collection(name, dim, vector_name)
        
        return name, effective, vector_name

    async def _ensure_named_collection(self, name: str, dim: int, vector_name: str) -> str:
        """确保指定名称的 collection 存在（创建时包含给定向量字段）。"""
        try:
            await self.client.get_collection(name)
            self._collection_cache.add(name)
            return await self._ensure_vector_field(name, vector_name, dim)
        except Exception:
            pass
        await self.client.create_collection(
            collection_name=name,
            vectors_config={vector_name: models.VectorParams(size=dim, distance=models.Distance.COSINE)},
        )
        self._collection_cache.add(name)
        return vector_name

    async def _ensure_vector_field(self, collection: str, vector_name: str, dim: int) -> str:
        """
        确保 collection 中存在指定的向量字段；如不存在则追加。
        
        支持多维度向量字段共存：
        - 如果请求的向量字段已存在，直接返回
        - 如果有默认向量字段且维度匹配，复用默认字段
        - 如果有默认向量字段但维度不匹配，创建新的命名字段
        - 如果没有向量字段，创建新的命名字段
        """
        try:
            info = await self.client.get_collection(collection)
            existing = {}
            try:
                vectors = info.config.params.vectors  # type: ignore[attr-defined]
                # vectors 可能是 dict[str, VectorParams] 或单一 VectorParams
                if isinstance(vectors, dict):
                    existing = {k: getattr(v, "size", None) for k, v in vectors.items()}
                elif hasattr(vectors, "size"):
                    existing = {"": getattr(vectors, "size", None)}
            except Exception:
                pass
            
            # 如果请求的向量字段已存在，直接返回
            if vector_name in existing:
                existing_dim = existing[vector_name]
                if existing_dim == dim:
                    return vector_name
                else:
                    logger.warning(f"向量字段 {vector_name} 已存在但维度不匹配: {existing_dim} != {dim}")
                    # 生成新的字段名避免冲突
                    vector_name = f"{vector_name}_{dim}"
            
            # 如果有默认向量字段且维度匹配，可以复用
            if "" in existing and existing[""] == dim and vector_name != "":
                logger.info(f"复用 {collection} 的默认向量字段 (dim={dim})")
                return ""
            
            # 如果有默认向量字段但维度不匹配，或者没有默认字段，创建新的命名字段
            if vector_name in existing:
                # 如果字段名冲突，生成新名称
                counter = 1
                base_name = vector_name
                while vector_name in existing:
                    vector_name = f"{base_name}_{counter}"
                    counter += 1
            
            await self.client.update_collection(
                collection_name=collection,
                vectors_config={vector_name: models.VectorParams(size=dim, distance=models.Distance.COSINE)},
            )
            logger.info(f"为 {collection} 追加向量字段 {vector_name} (dim={dim})")
            return vector_name
        except Exception as exc:
            logger.warning(f"追加向量字段失败 {collection}:{vector_name} - {exc}")
            raise
    
    # ==================== 兼容旧接口 ====================
    
    def _collection_name(self, tenant_id: str) -> str:
        """兼容旧接口：返回 collection 模式的名称"""
        return self._collection_name_for_tenant(tenant_id)

    async def upsert_chunk(
        self,
        *,
        chunk_id: str,
        tenant_id: str,
        knowledge_base_id: str,
        text: str,
        metadata: dict | None = None,
        strategy: IsolationStrategy = "auto",
    ) -> None:
        """
        插入/更新单个 chunk
        
        Args:
            chunk_id: Chunk ID
            tenant_id: 租户 ID
            knowledge_base_id: 知识库 ID
            text: 文本内容
            metadata: 额外元数据
            strategy: 隔离策略
        """
        vector = await get_embedding(text)
        embedding_dim = len(vector) if vector is not None else self.dim
        vector_name = get_vector_field_name(None, embedding_dim)
        collection, effective, vector_name = await self._ensure_collection(
            tenant_id, strategy, embedding_dim=embedding_dim, vector_name=vector_name
        )
        
        # Partition 模式需要添加 tenant_id 到 payload
        payload = {
            "kb_id": knowledge_base_id,
            "text": text,
            "metadata": metadata or {},
            "embedding_dim": embedding_dim,
        }
        if effective == "partition":
            payload["tenant_id"] = tenant_id
        
        await self.client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=chunk_id,
                    vector=vector if vector_name == "" else {vector_name: vector},
                    payload=payload,
                )
            ],
        )

    async def upsert_chunks(
        self,
        *,
        tenant_id: str,
        chunks: list[dict],
        strategy: IsolationStrategy = "auto",
        embedding_config: dict | None = None,
    ) -> None:
        """
        批量插入/更新 chunks
        
        Args:
            tenant_id: 租户 ID
            chunks: chunk 列表，每个包含 chunk_id, knowledge_base_id, text, metadata
            strategy: 隔离策略
            embedding_config: 可选的 embedding 配置（来自前端），格式为 {provider, model, api_key, base_url}
        """
        if not chunks:
            return
        
        # 批量获取 Embedding（优先使用传入的配置）
        texts = [c["text"] for c in chunks]
        if embedding_config:
            vectors = await get_embeddings_with_config(texts, embedding_config)
        else:
            vectors = await get_embeddings(texts)
        
        # 根据 embedding 模型确定维度，确保 collection 使用正确的维度
        model_name = (embedding_config or {}).get("model") if embedding_config else None
        embedding_dim = _resolve_embedding_dim(
            model_name,
            len(vectors[0]) if vectors else None,
            self.dim,
        )
        vector_name = get_vector_field_name(
            model_name,
            embedding_dim,
        )
        
        collection, effective, vector_name = await self._ensure_collection(
            tenant_id, strategy, embedding_dim, vector_name
        )
        
        # 构建 points（Partition 模式需要添加 tenant_id）
        points = []
        for chunk, vector in zip(chunks, vectors):
            payload = {
                "kb_id": chunk["knowledge_base_id"],
                "text": chunk["text"],
                "metadata": chunk.get("metadata", {}),
                "embedding_model": (embedding_config or {}).get("model") if embedding_config else None,
                "embedding_dim": embedding_dim,
            }
            if effective == "partition":
                payload["tenant_id"] = tenant_id
            
            points.append(
                models.PointStruct(
                    id=chunk["chunk_id"],
                    vector=vector if vector_name == "" else {vector_name: vector},
                    payload=payload,
                )
            )
        
        try:
            await self.client.upsert(
                collection_name=collection,
                points=points,
            )
        except Exception as exc:
            # 如果因为缺少向量字段导致失败，尝试补充字段并重试一次
            msg = str(exc)
            if "Not existing vector name" in msg or "vector name error" in msg:
                await self._ensure_vector_field(collection, vector_name, embedding_dim or self.dim)
                await self.client.upsert(collection_name=collection, points=points)
            else:
                raise
        logger.debug(f"批量 upsert {len(chunks)} chunks 到 {collection} (策略: {effective})")

    async def upsert_vectors(
        self,
        *,
        tenant_id: str,
        knowledge_base_id: str,
        vectors: list[dict],
        strategy: IsolationStrategy = "auto",
    ) -> int:
        """
        批量插入已有向量（不重新生成 embedding）
        
        用于 RAPTOR 等已预先计算好 embedding 的场景。
        此方法是向量库无关的抽象接口，Milvus/ES/pgvector 实现时需提供相同签名。
        
        Args:
            tenant_id: 租户 ID
            knowledge_base_id: 知识库 ID
            vectors: 向量列表，每个包含:
                - id: str (UUID 格式)
                - vector: list[float]
                - payload: dict (包含 text, metadata 等)
            strategy: 隔离策略
            
        Returns:
            插入的向量数量
        """
        if not vectors:
            return 0
        
        # 从向量推断维度
        embedding_dim = len(vectors[0]["vector"]) if vectors else None
        
        vector_name = get_vector_field_name(None, embedding_dim)
        collection, effective, vector_name = await self._ensure_collection(
            tenant_id, strategy, embedding_dim, vector_name
        )
        
        # 构建 points
        points = []
        for v in vectors:
            payload = v.get("payload", {})
            payload["kb_id"] = knowledge_base_id
            if effective == "partition":
                payload["tenant_id"] = tenant_id
            
            points.append(
                models.PointStruct(
                    id=v["id"],
                    vector=v["vector"] if vector_name == "" else {vector_name: v["vector"]},
                    payload=payload,
                )
            )
        
        await self.client.upsert(
            collection_name=collection,
            points=points,
        )
        logger.debug(f"批量 upsert {len(vectors)} vectors 到 {collection} (策略: {effective})")
        return len(vectors)

    async def search(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: Iterable[str],
        top_k: int = 5,
        strategy: IsolationStrategy = "auto",
        score_threshold: float | None = None,
        embedding_config: dict | None = None,
        acl_filter: dict | None = None,
    ) -> list[tuple[float, VectorRecord]]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            tenant_id: 租户 ID
            kb_ids: 知识库 ID 列表
            top_k: 返回数量
            strategy: 隔离策略
            score_threshold: 最低分数阈值，低于此分数的结果将被过滤
            embedding_config: 可选的 embedding 配置（来自知识库配置）
        
        Returns:
            list[tuple[score, VectorRecord]]
        """
        # 读取上下文中的 ACL Filter（可由上层设置）
        if acl_filter is None:
            acl_filter = get_acl_filter_ctx()
        start_time = time.perf_counter()

        # 优先使用传入的 embedding 配置，否则使用默认配置
        if embedding_config:
            vector = await get_embeddings_with_config([query], embedding_config)
            vector = vector[0]
        else:
            vector = await get_embedding(query)
        
        # 根据 embedding 模型确定维度，确保使用正确的 collection
        model_name = (embedding_config or {}).get("model") if embedding_config else None
        embedding_dim = _resolve_embedding_dim(
            model_name,
            len(vector),
            self.dim,
        )
        vector_name = get_vector_field_name(
            model_name,
            embedding_dim,
        )
        
        collection, effective, vector_name = await self._ensure_collection(
            tenant_id, strategy, embedding_dim, vector_name
        )
        
        kb_list = list(kb_ids)
        
        # 构建过滤条件
        must_conditions = [
            models.FieldCondition(
                key="kb_id",
                match=models.MatchAny(any=kb_list),
            )
        ]
        
        # Partition 模式需要添加 tenant_id 过滤
        if effective == "partition":
            must_conditions.append(
                models.FieldCondition(
                    key="tenant_id",
                    match=models.MatchValue(value=tenant_id),
                )
            )
        
        # ACL Filter: (public) OR (用户/角色/组匹配)
        def _to_field_condition(cond: dict) -> models.FieldCondition:
            key = cond.get("key")
            match_cfg = cond.get("match") or {}
            if "value" in match_cfg:
                match = models.MatchValue(value=match_cfg["value"])
            elif "any" in match_cfg:
                match = models.MatchAny(any=match_cfg["any"])
            else:
                # 回退使用原始结构
                match = match_cfg
            return models.FieldCondition(key=key, match=match)

        should_conditions: list[models.FieldCondition] = []
        if acl_filter and isinstance(acl_filter, dict):
            for cond in acl_filter.get("should", []):
                try:
                    should_conditions.append(_to_field_condition(cond))
                except Exception as exc:  # pragma: no cover - 防御性处理
                    logger.warning(f"构建 ACL Filter 失败，跳过此条件: {exc}")

        filter_ = models.Filter(
            must=must_conditions,
            should=should_conditions or None,
        )
        
        try:
            query_vector = vector if vector_name == "" else models.NamedVector(name=vector_name, vector=vector)
            results = await self.client.search(
                collection_name=collection,
                query_vector=query_vector,
                query_filter=filter_,
                limit=top_k,
                with_payload=True,
                score_threshold=score_threshold,
            )
        except Exception as exc:
            logger.error(f"向量搜索失败: {exc}")
            latency_ms = (time.perf_counter() - start_time) * 1000
            metrics_collector.record_retrieval(
                retriever="vector_search",
                query=query,
                results=[],
                latency_ms=latency_ms,
                backend="qdrant",
                error=str(exc),
            )
            return []

        hits: list[tuple[float, VectorRecord]] = []
        results_for_metrics: list[dict] = []
        for point in results:
            payload = point.payload or {}
            kb_id = payload.get("kb_id")
            score = point.score or 0.0
            hits.append(
                (
                    score,
                    VectorRecord(
                        chunk_id=str(point.id),
                        tenant_id=tenant_id,
                        knowledge_base_id=kb_id,
                        text=payload.get("text", ""),
                        metadata=payload.get("metadata", {}) or {},
                    ),
                )
            )
            results_for_metrics.append(
                {
                    "score": score,
                    "knowledge_base_id": kb_id,
                    "source": "dense",
                }
            )
        latency_ms = (time.perf_counter() - start_time) * 1000
        metrics_collector.record_retrieval(
            retriever="vector_search",
            query=query,
            results=results_for_metrics,
            latency_ms=latency_ms,
            backend="qdrant",
        )
        return hits

    async def delete_by_kb(
        self,
        tenant_id: str,
        kb_id: str,
        strategy: IsolationStrategy = "auto",
    ) -> int:
        """
        删除指定知识库的所有向量
        
        Args:
            tenant_id: 租户 ID
            kb_id: 知识库 ID
            strategy: 隔离策略
        
        Returns:
            删除的数量
        """
        collection, effective, _ = await self._ensure_collection(tenant_id, strategy, ensure_vector=False)
        
        # 构建过滤条件
        must_conditions = [
            models.FieldCondition(
                key="kb_id",
                match=models.MatchValue(value=kb_id),
            )
        ]
        
        # Partition 模式需要添加 tenant_id 过滤
        if effective == "partition":
            must_conditions.append(
                models.FieldCondition(
                    key="tenant_id",
                    match=models.MatchValue(value=tenant_id),
                )
            )
        
        try:
            result = await self.client.delete(
                collection_name=collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=must_conditions)
                ),
            )
            logger.info(f"删除 KB {kb_id} 的向量，状态: {result.status} (策略: {effective})")
            return 0  # Qdrant 不返回删除数量
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return 0

    async def delete_by_ids(
        self,
        tenant_id: str,
        chunk_ids: list[str],
        strategy: IsolationStrategy = "auto",
    ) -> int:
        """
        按 ID 列表删除向量
        
        Args:
            tenant_id: 租户 ID
            chunk_ids: Chunk ID 列表
            strategy: 隔离策略
        
        Returns:
            删除的数量（Qdrant 不返回实际数量，返回 0）
        """
        if not chunk_ids:
            return 0
        
        collection, effective, _ = await self._ensure_collection(tenant_id, strategy, ensure_vector=False)
        try:
            result = await self.client.delete(
                collection_name=collection,
                points_selector=models.PointIdsList(
                    points=chunk_ids,
                ),
            )
            logger.info(f"删除 {len(chunk_ids)} 个向量，状态: {result.status} (策略: {effective})")
            return len(chunk_ids)
        except Exception as e:
            logger.error(f"按 ID 删除向量失败: {e}")
            return 0
    
    # ==================== 隔离策略管理 ====================
    
    def set_tenant_strategy(self, tenant_id: str, strategy: str) -> None:
        """
        设置租户的隔离策略缓存
        
        Args:
            tenant_id: 租户 ID
            strategy: "partition" 或 "collection"
        """
        if strategy in ("partition", "collection"):
            self._tenant_strategy_cache[tenant_id] = strategy
            logger.info(f"设置租户 {tenant_id} 隔离策略为: {strategy}")
    
    async def get_tenant_vector_count(self, tenant_id: str) -> int:
        """
        获取租户的向量数量
        
        用于 auto 模式判断是否需要迁移到 collection 模式
        """
        # 先尝试 collection 模式
        collection_name = self._collection_name_for_tenant(tenant_id)
        try:
            info = await self.client.get_collection(collection_name)
            return info.points_count or 0
        except Exception:
            pass
        
        # 再尝试 partition 模式（共享 collection）
        try:
            result = await self.client.count(
                collection_name=self.shared_collection,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="tenant_id",
                            match=models.MatchValue(value=tenant_id),
                        )
                    ]
                ),
            )
            return result.count
        except Exception:
            return 0


# 全局实例（异步）
vector_store = AsyncQdrantVectorStore()
