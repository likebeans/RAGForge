"""
RAPTOR Native Indexer

原生 RAPTOR 实现，不依赖 LlamaIndex RaptorPack。
参考 RAGFlow 的实现：https://github.com/infiniflow/ragflow/blob/main/rag/raptor.py

RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval)
递归地对文档块进行聚类和摘要，构建多层次的索引树。

原理：
1. 将文档切分为 chunks（Layer 0）
2. 对 chunks 进行向量化
3. 使用 UMAP 降维 + GMM 聚类
4. 对每个聚类生成摘要（Layer 1）
5. 递归处理摘要，直到只剩一个节点或达到最大层数

参考论文：https://arxiv.org/abs/2401.18059
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)

# 延迟导入依赖（避免启动时卡住）
# umap-learn 在某些环境下首次导入会很慢
RAPTOR_NATIVE_AVAILABLE = True  # 假设可用，实际使用时再检查

def _check_raptor_deps():
    """延迟检查 RAPTOR 依赖"""
    global RAPTOR_NATIVE_AVAILABLE
    try:
        import umap  # noqa: F401
        from sklearn.mixture import GaussianMixture  # noqa: F401
        return True
    except ImportError as e:
        RAPTOR_NATIVE_AVAILABLE = False
        logger.warning(f"RAPTOR 原生实现依赖未安装 (umap-learn, scikit-learn): {e}")
        return False


@dataclass
class RaptorNode:
    """RAPTOR 树节点"""
    id: str
    text: str
    level: int  # 0 = 原始 chunk, 1+ = 摘要层
    embedding: list[float] | None = None
    children_ids: list[str] = field(default_factory=list)
    parent_id: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RaptorBuildResult:
    """RAPTOR 索引构建结果"""
    total_nodes: int
    levels: int
    leaf_nodes: int  # 原始 chunks
    summary_nodes: int  # 摘要节点
    nodes: list[RaptorNode]
    layers: list[tuple[int, int]]  # 每层的起止索引


class RaptorNativeIndexer:
    """
    原生 RAPTOR 索引器
    
    使用 UMAP 降维 + GMM 聚类 + LLM 摘要，构建多层次索引树。
    
    使用示例：
    ```python
    indexer = RaptorNativeIndexer(
        llm_func=my_llm_chat,
        embed_func=my_embed,
        max_clusters=10,
        max_layers=3,
    )
    
    # 从 chunks 构建 RAPTOR 索引
    result = await indexer.build(chunks)
    
    print(f"总节点: {result.total_nodes}")
    print(f"层数: {result.levels}")
    ```
    """
    
    DEFAULT_SUMMARY_PROMPT = """请为以下文本内容生成一个简洁的摘要，保留关键信息：

{cluster_content}

摘要："""
    
    def __init__(
        self,
        llm_func: Callable[[str], Any] | None = None,
        embed_func: Callable[[str], list[float]] | None = None,
        max_clusters: int = 10,
        max_layers: int = 3,
        summary_prompt: str | None = None,
        max_summary_tokens: int = 512,
        cluster_threshold: float = 0.1,
        callback: Callable[[str], None] | None = None,
    ):
        """
        初始化 RAPTOR 索引器
        
        Args:
            llm_func: LLM 调用函数，接收 prompt 返回摘要文本
            embed_func: Embedding 函数，接收文本返回向量
            max_clusters: 每层最大聚类数
            max_layers: 最大层数
            summary_prompt: 摘要生成提示词模板
            max_summary_tokens: 摘要最大 token 数
            cluster_threshold: GMM 聚类阈值
            callback: 进度回调函数
        """
        if not RAPTOR_NATIVE_AVAILABLE:
            raise RuntimeError("RAPTOR 原生实现需要安装 umap-learn 和 scikit-learn")
        
        self.llm_func = llm_func
        self.embed_func = embed_func
        self.max_clusters = max_clusters
        self.max_layers = max_layers
        self.summary_prompt = summary_prompt or self.DEFAULT_SUMMARY_PROMPT
        self.max_summary_tokens = max_summary_tokens
        self.cluster_threshold = cluster_threshold
        self.callback = callback
        
        self._nodes: list[RaptorNode] = []
        self._layers: list[tuple[int, int]] = []
    
    def _log(self, msg: str):
        """记录日志并调用回调"""
        logger.info(f"[RAPTOR-Native] {msg}")
        if self.callback:
            self.callback(msg)
    
    async def _get_embedding(self, text: str) -> list[float]:
        """获取文本的向量表示"""
        if self.embed_func is None:
            raise RuntimeError("未配置 embed_func")
        
        # 支持同步和异步函数
        if asyncio.iscoroutinefunction(self.embed_func):
            return await self.embed_func(text)
        else:
            return await asyncio.to_thread(self.embed_func, text)
    
    async def _generate_summary(self, texts: list[str]) -> str:
        """为一组文本生成摘要"""
        if self.llm_func is None:
            raise RuntimeError("未配置 llm_func")
        
        # 合并文本
        cluster_content = "\n\n---\n\n".join(texts)
        
        # 截断过长的内容（简单按字符截断）
        max_chars = 8000  # 约 2000 tokens
        if len(cluster_content) > max_chars:
            cluster_content = cluster_content[:max_chars] + "..."
        
        prompt = self.summary_prompt.format(cluster_content=cluster_content)
        
        # 调用 LLM
        if asyncio.iscoroutinefunction(self.llm_func):
            response = await self.llm_func(prompt)
        else:
            response = await asyncio.to_thread(self.llm_func, prompt)
        
        # 清理响应（移除 thinking 标签等）
        if isinstance(response, str):
            response = re.sub(r"^.*</think>", "", response, flags=re.DOTALL)
        
        return response
    
    def _get_optimal_clusters(
        self,
        embeddings: np.ndarray,
        random_state: int = 42,
    ) -> int:
        """使用 BIC 准则确定最优聚类数"""
        from sklearn.mixture import GaussianMixture
        
        max_clusters = min(self.max_clusters, len(embeddings))
        if max_clusters <= 1:
            return 1
        
        n_clusters_range = np.arange(1, max_clusters + 1)
        bics = []
        
        for n in n_clusters_range:
            gm = GaussianMixture(n_components=n, random_state=random_state)
            gm.fit(embeddings)
            bics.append(gm.bic(embeddings))
        
        optimal_clusters = n_clusters_range[np.argmin(bics)]
        return int(optimal_clusters)
    
    async def build(
        self,
        chunks: list[dict],
        random_state: int = 42,
    ) -> RaptorBuildResult:
        """
        构建 RAPTOR 索引
        
        Args:
            chunks: chunk 列表，每个 chunk 包含 text 和可选的 metadata
            random_state: 随机种子
            
        Returns:
            构建结果
        """
        if len(chunks) <= 1:
            self._log("chunks 数量不足，无法构建 RAPTOR 索引")
            return RaptorBuildResult(
                total_nodes=len(chunks),
                levels=1,
                leaf_nodes=len(chunks),
                summary_nodes=0,
                nodes=[],
                layers=[],
            )
        
        self._log(f"开始构建 RAPTOR 索引，共 {len(chunks)} 个 chunks")
        
        # Step 1: 向量化所有 chunks
        self._log("Step 1: 向量化 chunks...")
        nodes: list[RaptorNode] = []
        
        for i, chunk in enumerate(chunks):
            text = chunk.get("text", "")
            metadata = chunk.get("metadata", {})
            
            if not text:
                continue
            
            # 获取向量
            embedding = await self._get_embedding(text)
            
            node = RaptorNode(
                id=str(uuid4()),
                text=text,
                level=0,  # 原始 chunk 是 level 0
                embedding=embedding,
                metadata=metadata,
            )
            nodes.append(node)
        
        if len(nodes) <= 1:
            self._log("有效 chunks 数量不足")
            return RaptorBuildResult(
                total_nodes=len(nodes),
                levels=1,
                leaf_nodes=len(nodes),
                summary_nodes=0,
                nodes=nodes,
                layers=[(0, len(nodes))],
            )
        
        self._log(f"Step 1 完成: 向量化了 {len(nodes)} 个 chunks")
        
        # 记录层级信息
        layers: list[tuple[int, int]] = [(0, len(nodes))]
        start, end = 0, len(nodes)
        current_level = 0
        
        # Step 2: 递归聚类和摘要
        while end - start > 1 and current_level < self.max_layers:
            current_level += 1
            self._log(f"Step 2.{current_level}: 处理 Layer {current_level}...")
            
            # 获取当前层的向量
            embeddings = np.array([
                node.embedding for node in nodes[start:end]
                if node.embedding is not None
            ])
            
            if len(embeddings) <= 1:
                self._log(f"Layer {current_level}: 节点数不足，停止递归")
                break
            
            # 特殊情况：只有 2 个节点
            if len(embeddings) == 2:
                self._log(f"Layer {current_level}: 只有 2 个节点，直接合并")
                texts = [nodes[start].text, nodes[start + 1].text]
                try:
                    summary = await self._generate_summary(texts)
                    embedding = await self._get_embedding(summary)
                    
                    summary_node = RaptorNode(
                        id=str(uuid4()),
                        text=summary,
                        level=current_level,
                        embedding=embedding,
                        children_ids=[nodes[start].id, nodes[start + 1].id],
                        metadata={"cluster_size": 2},
                    )
                    
                    # 更新子节点的 parent_id
                    nodes[start].parent_id = summary_node.id
                    nodes[start + 1].parent_id = summary_node.id
                    
                    nodes.append(summary_node)
                except Exception as e:
                    self._log(f"Layer {current_level}: 摘要生成失败: {e}")
                
                layers.append((end, len(nodes)))
                start = end
                end = len(nodes)
                continue
            
            # UMAP 降维（延迟导入）
            import umap
            from sklearn.mixture import GaussianMixture
            
            n_neighbors = int((len(embeddings) - 1) ** 0.8)
            n_components = min(12, len(embeddings) - 2)
            
            try:
                reduced_embeddings = umap.UMAP(
                    n_neighbors=max(2, n_neighbors),
                    n_components=max(2, n_components),
                    metric="cosine",
                    random_state=random_state,
                ).fit_transform(embeddings)
            except Exception as e:
                self._log(f"Layer {current_level}: UMAP 降维失败: {e}")
                break
            
            # 确定最优聚类数
            n_clusters = self._get_optimal_clusters(reduced_embeddings, random_state)
            self._log(f"Layer {current_level}: 最优聚类数 = {n_clusters}")
            
            if n_clusters == 1:
                # 所有节点属于同一聚类
                labels = [0] * len(reduced_embeddings)
            else:
                # GMM 聚类
                gm = GaussianMixture(n_components=n_clusters, random_state=random_state)
                gm.fit(reduced_embeddings)
                probs = gm.predict_proba(reduced_embeddings)
                labels = [np.where(prob > self.cluster_threshold)[0] for prob in probs]
                labels = [lbl[0] if isinstance(lbl, np.ndarray) and len(lbl) > 0 else 0 for lbl in labels]
            
            # 为每个聚类生成摘要
            summary_tasks = []
            cluster_indices: dict[int, list[int]] = {}
            
            for i, label in enumerate(labels):
                if label not in cluster_indices:
                    cluster_indices[label] = []
                cluster_indices[label].append(start + i)
            
            for cluster_id, indices in cluster_indices.items():
                texts = [nodes[i].text for i in indices]
                summary_tasks.append((cluster_id, indices, texts))
            
            # 并发生成摘要
            new_summary_count = 0
            for cluster_id, indices, texts in summary_tasks:
                try:
                    summary = await self._generate_summary(texts)
                    embedding = await self._get_embedding(summary)
                    
                    summary_node = RaptorNode(
                        id=str(uuid4()),
                        text=summary,
                        level=current_level,
                        embedding=embedding,
                        children_ids=[nodes[i].id for i in indices],
                        metadata={"cluster_id": cluster_id, "cluster_size": len(indices)},
                    )
                    
                    # 更新子节点的 parent_id
                    for i in indices:
                        nodes[i].parent_id = summary_node.id
                    
                    nodes.append(summary_node)
                    new_summary_count += 1
                except Exception as e:
                    self._log(f"Layer {current_level}: 聚类 {cluster_id} 摘要生成失败: {e}")
            
            self._log(f"Layer {current_level}: 生成了 {new_summary_count} 个摘要节点")
            
            if new_summary_count == 0:
                self._log(f"Layer {current_level}: 没有生成新节点，停止递归")
                break
            
            layers.append((end, len(nodes)))
            start = end
            end = len(nodes)
        
        # 统计结果
        leaf_count = sum(1 for n in nodes if n.level == 0)
        summary_count = len(nodes) - leaf_count
        max_level = max((n.level for n in nodes), default=0)
        
        self._log(
            f"RAPTOR 索引构建完成! "
            f"总节点 {len(nodes)}, 层数 {max_level + 1}, "
            f"叶子节点 {leaf_count}, 摘要节点 {summary_count}"
        )
        
        self._nodes = nodes
        self._layers = layers
        
        return RaptorBuildResult(
            total_nodes=len(nodes),
            levels=max_level + 1,
            leaf_nodes=leaf_count,
            summary_nodes=summary_count,
            nodes=nodes,
            layers=layers,
        )
    
    def get_nodes(self) -> list[RaptorNode]:
        """获取所有节点"""
        return self._nodes
    
    def get_layers(self) -> list[tuple[int, int]]:
        """获取层级信息"""
        return self._layers
    
    async def save_to_db(
        self,
        session: Any,  # AsyncSession
        tenant_id: str,
        knowledge_base_id: str,
        chunk_id_mapping: dict[str, str] | None = None,
    ) -> int:
        """
        将 RAPTOR 节点保存到数据库
        
        Args:
            session: 数据库会话
            tenant_id: 租户 ID
            knowledge_base_id: 知识库 ID
            chunk_id_mapping: 原始 chunk 索引到 chunk_id 的映射
            
        Returns:
            保存的节点数量
        """
        from app.models.raptor_node import RaptorNode as RaptorNodeModel
        import numpy as np
        
        def convert_numpy_types(obj):
            """递归转换 numpy 类型为原生 Python 类型"""
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return [convert_numpy_types(x) for x in obj.tolist()]
            elif isinstance(obj, dict):
                return {str(k): convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_numpy_types(item) for item in obj]
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                return str(obj)
        
        nodes = self._nodes
        if not nodes:
            logger.warning("[RAPTOR-Native] 没有节点需要保存")
            return 0
        
        chunk_id_mapping = chunk_id_mapping or {}
        saved_count = 0
        
        for node in nodes:
            # 查找关联的原始 chunk ID（仅叶子节点）
            chunk_id = None
            if node.level == 0:
                # 尝试从 metadata 获取原始 chunk 索引
                original_idx = node.metadata.get("chunk_idx")
                if original_idx is not None and str(original_idx) in chunk_id_mapping:
                    chunk_id = chunk_id_mapping[str(original_idx)]
            
            db_node = RaptorNodeModel(
                id=node.id,
                tenant_id=tenant_id,
                knowledge_base_id=knowledge_base_id,
                chunk_id=chunk_id,
                text=node.text,
                level=convert_numpy_types(node.level),
                parent_id=node.parent_id,
                children_ids=convert_numpy_types(node.children_ids),
                vector_id=node.metadata.get("vector_id"),
                indexing_status="indexed",  # 原生实现直接标记为 indexed
                extra_metadata=convert_numpy_types(node.metadata),
            )
            session.add(db_node)
            saved_count += 1
        
        await session.flush()
        logger.info(f"[RAPTOR-Native] 保存了 {saved_count} 个节点到数据库")
        return saved_count
    
    async def save_to_vector_store(
        self,
        tenant_id: str,
        knowledge_base_id: str,
    ) -> int:
        """
        将 RAPTOR 节点向量保存到向量库
        
        使用 vector_store.upsert_vectors 抽象接口，兼容 Qdrant/Milvus/ES/pgvector。
        
        Args:
            tenant_id: 租户 ID
            knowledge_base_id: 知识库 ID
            
        Returns:
            保存的向量数量
        """
        from app.infra.vector_store import vector_store
        import uuid
        import numpy as np
        
        def convert_numpy_types(obj):
            """递归转换 numpy 类型为原生 Python 类型"""
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return [convert_numpy_types(x) for x in obj.tolist()]
            elif isinstance(obj, dict):
                return {str(k): convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_numpy_types(item) for item in obj]
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                # 其他未知类型转为字符串，避免序列化失败
                return str(obj)
        
        nodes = self._nodes
        if not nodes:
            logger.warning("[RAPTOR-Native] 没有节点需要保存到向量库")
            return 0
        
        # 准备向量数据（使用通用格式，兼容多种向量库）
        vectors = []
        for node in nodes:
            if node.embedding is None:
                continue
            
            # 向量库通常要求 ID 是 UUID 或 unsigned int
            # 使用 node.id 作为 UUID（如果有效），否则生成确定性 UUID
            try:
                vector_id = str(uuid.UUID(node.id))
            except ValueError:
                vector_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"raptor_{node.id}"))
            
            node.metadata["vector_id"] = vector_id
            
            # 使用 convert_numpy_types 确保所有数据都是原生 Python 类型
            vectors.append({
                "id": vector_id,
                "vector": convert_numpy_types(node.embedding),
                "payload": convert_numpy_types({
                    "chunk_id": node.id,
                    "text": node.text[:500],
                    "raptor_level": node.level,
                    "raptor_node": True,
                    "metadata": node.metadata,
                }),
            })
        
        if not vectors:
            logger.warning("[RAPTOR-Native] 没有向量需要保存")
            return 0
        
        # 使用通用的 upsert_vectors 接口（兼容多种向量库）
        count = await vector_store.upsert_vectors(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            vectors=vectors,
        )
        
        logger.info(f"[RAPTOR-Native] 保存了 {count} 个向量到向量库")
        return count


async def create_raptor_native_indexer_from_config(
    embedding_config: dict | None = None,
    llm_config: dict | None = None,
    raptor_config: dict | None = None,
) -> RaptorNativeIndexer:
    """
    从应用配置创建 RAPTOR 原生索引器
    
    Args:
        embedding_config: Embedding 配置
        llm_config: LLM 配置
        raptor_config: RAPTOR 配置
        
    Returns:
        RaptorNativeIndexer 实例
    """
    from app.config import get_settings
    from app.infra.embeddings import get_embedding_with_config
    from app.infra.llm import chat_completion_with_config
    
    settings = get_settings()
    raptor_config = raptor_config or {}
    
    # 构建完整的 embedding provider_config
    # 如果传入了 embedding_config（包含 api_key 等），直接使用；否则从 settings 构建
    if embedding_config and embedding_config.get("api_key"):
        # 使用传入的完整配置（来自知识库配置或前端）
        embed_provider_config = embedding_config
    else:
        # 从 settings 构建默认配置
        embed_provider_config = settings._get_provider_config(
            embedding_config.get("provider") if embedding_config else settings.embedding_provider,
            embedding_config.get("model") if embedding_config else settings.embedding_model,
        )
    
    async def embed_func(text: str) -> list[float]:
        return await get_embedding_with_config(
            text=text,
            provider_config=embed_provider_config,
        )
    
    # 构建完整的 LLM provider_config
    if llm_config and llm_config.get("api_key"):
        # 使用传入的完整配置
        llm_provider_config = llm_config
    else:
        # 从 settings 构建默认配置
        llm_provider_config = settings._get_provider_config(
            llm_config.get("provider") if llm_config else settings.llm_provider,
            llm_config.get("model") if llm_config else settings.llm_model,
        )
    
    async def llm_func(prompt: str) -> str:
        return await chat_completion_with_config(
            prompt=prompt,
            provider_config=llm_provider_config,
            max_tokens=512,
        )
    
    return RaptorNativeIndexer(
        llm_func=llm_func,
        embed_func=embed_func,
        max_clusters=raptor_config.get("max_clusters", 10),
        max_layers=raptor_config.get("max_layers", 3),
        summary_prompt=raptor_config.get("summary_prompt"),
        cluster_threshold=raptor_config.get("cluster_threshold", 0.1),
    )
