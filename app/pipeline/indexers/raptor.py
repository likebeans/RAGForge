"""
RAPTOR Indexer

RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval)
递归地对文档块进行聚类和摘要，构建多层次的索引树。

原理：
1. 将文档切分为 chunks
2. 对 chunks 进行聚类（基于向量相似度）
3. 对每个聚类生成摘要
4. 递归处理摘要，直到达到最大层数

检索时支持两种模式：
- collapsed: 将所有层级的节点作为一个整体进行检索
- tree_traversal: 从顶层向下遍历，逐层筛选

参考论文：https://arxiv.org/abs/2401.18059
"""

import logging
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from uuid import uuid4


from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.models.raptor_node import RaptorNode as RaptorNodeModel

# 尝试导入 LlamaIndex RAPTOR pack
try:
    from llama_index.packs.raptor import RaptorPack, RaptorRetriever
    from llama_index.packs.raptor.base import SummaryModule
    from llama_index.core import Document as LlamaDocument
    from llama_index.core.llms import LLM
    from llama_index.core.embeddings import BaseEmbedding
    # VectorStore 类型用于类型注解，使用 Any 替代以避免导入问题
    RAPTOR_AVAILABLE = True
except ImportError as e:
    RAPTOR_AVAILABLE = False
    logger.warning(f"llama-index-packs-raptor 未安装，RAPTOR 功能不可用: {e}")


@dataclass
class RaptorNode:
    """RAPTOR 树节点"""
    id: str
    text: str
    level: int  # 0 = 原始 chunk, 1+ = 摘要层
    children_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class RaptorIndexResult:
    """RAPTOR 索引结果"""
    total_nodes: int
    levels: int
    leaf_nodes: int  # 原始 chunks
    summary_nodes: int  # 摘要节点
    nodes: list[RaptorNode]


class RaptorIndexer:
    """
    RAPTOR 索引器
    
    封装 LlamaIndex 的 RaptorPack，提供更灵活的配置和集成。
    
    使用示例：
    ```python
    indexer = RaptorIndexer(
        llm=llm,
        embed_model=embed_model,
        max_layers=3,
        summary_num_workers=4,
    )
    
    # 从 chunks 构建 RAPTOR 索引
    result = indexer.build_from_chunks(chunks)
    
    # 检索
    retriever = indexer.get_retriever(mode="collapsed")
    nodes = retriever.retrieve("query", top_k=5)
    ```
    """
    
    def __init__(
        self,
        llm: Any | None = None,
        embed_model: Any | None = None,
        vector_store: Any | None = None,
        max_layers: int = 3,
        summary_num_workers: int = 4,
        summary_prompt: str | None = None,
    ):
        """
        初始化 RAPTOR 索引器
        
        Args:
            llm: LLM 实例，用于生成摘要
            embed_model: Embedding 模型实例
            vector_store: 向量存储实例（可选，用于持久化）
            max_layers: 最大层数，默认 3
            summary_num_workers: 摘要生成并发数，默认 4
            summary_prompt: 自定义摘要提示词
        """
        if not RAPTOR_AVAILABLE:
            raise ImportError(
                "llama-index-packs-raptor 未安装。"
                "请运行: pip install llama-index-packs-raptor"
            )
        
        self.llm = llm
        self.embed_model = embed_model
        self.vector_store = vector_store
        self.max_layers = max_layers
        self.summary_num_workers = summary_num_workers
        self.summary_prompt = summary_prompt or self._default_summary_prompt()
        
        self._pack: RaptorPack | None = None
        self._retriever: RaptorRetriever | None = None
    
    def _default_summary_prompt(self) -> str:
        """默认摘要提示词"""
        return (
            "请为以下文本生成简洁全面的摘要，保留关键信息和核心概念。"
            "摘要应当能够独立理解，无需参考原文。\n\n"
            "文本：\n{context_str}\n\n"
            "摘要："
        )
    
    def build_from_texts(
        self,
        texts: list[str],
        metadata_list: list[dict] | None = None,
    ) -> RaptorIndexResult:
        """
        从文本列表构建 RAPTOR 索引
        
        Args:
            texts: 文本列表
            metadata_list: 每个文本对应的元数据列表
            
        Returns:
            索引结果
        """
        metadata_list = metadata_list or [{} for _ in texts]
        
        # 转换为 LlamaIndex Document
        documents = [
            LlamaDocument(text=text, metadata=meta)
            for text, meta in zip(texts, metadata_list)
        ]
        
        return self._build_index(documents)
    
    def build_from_chunks(
        self,
        chunks: list[dict],
    ) -> RaptorIndexResult:
        """
        从 chunk 字典列表构建 RAPTOR 索引
        
        Args:
            chunks: chunk 列表，每个 chunk 包含 text 和可选的 metadata
            
        Returns:
            索引结果
        """
        texts = [c.get("text", "") for c in chunks]
        metadata_list = [c.get("metadata", {}) for c in chunks]
        return self.build_from_texts(texts, metadata_list)
    
    def _build_index(self, documents: list) -> RaptorIndexResult:
        """构建 RAPTOR 索引"""
        import time
        start_time = time.time()
        
        logger.info(f"[RAPTOR] 开始构建索引，共 {len(documents)} 个文档")
        logger.info(f"[RAPTOR] LLM: {type(self.llm).__name__}, Embedding: {type(self.embed_model).__name__}")
        logger.info(f"[RAPTOR] 配置: max_layers={self.max_layers}, summary_workers={self.summary_num_workers}")
        
        # 创建 SummaryModule 配置
        logger.info(f"[RAPTOR] 步骤 1/4: 创建 SummaryModule...")
        summary_module = SummaryModule(
            llm=self.llm,
            summary_prompt=self.summary_prompt,
            num_workers=self.summary_num_workers,
        )
        logger.info(f"[RAPTOR] SummaryModule 创建完成")
        
        # 构建 RaptorPack
        logger.info(f"[RAPTOR] 步骤 2/4: 初始化 RaptorPack（这一步会进行向量化和聚类，可能较慢）...")
        pack_kwargs = {
            "documents": documents,
            "llm": self.llm,
            "embed_model": self.embed_model,
            "summary_module": summary_module,
        }
        
        if self.vector_store:
            pack_kwargs["vector_store"] = self.vector_store
        
        self._pack = RaptorPack(**pack_kwargs)
        self._retriever = self._pack.retriever
        logger.info(f"[RAPTOR] 步骤 3/4: RaptorPack 构建完成，耗时 {time.time() - start_time:.2f}s")
        
        # 统计结果
        # 注意：LlamaIndex RaptorPack 内部会自动处理聚类和摘要
        # 我们只能通过 retriever 获取节点信息
        logger.info(f"[RAPTOR] 步骤 4/4: 提取节点信息...")
        nodes = self._extract_nodes()
        
        leaf_count = sum(1 for n in nodes if n.level == 0)
        summary_count = len(nodes) - leaf_count
        max_level = max((n.level for n in nodes), default=0)
        
        total_time = time.time() - start_time
        logger.info(
            f"[RAPTOR] 索引构建完成! 总耗时 {total_time:.2f}s, "
            f"总节点 {len(nodes)}, 层数 {max_level + 1}, "
            f"叶子节点 {leaf_count}, 摘要节点 {summary_count}"
        )
        
        return RaptorIndexResult(
            total_nodes=len(nodes),
            levels=max_level + 1,
            leaf_nodes=leaf_count,
            summary_nodes=summary_count,
            nodes=nodes,
        )
    
    def _extract_nodes(self) -> list[RaptorNode]:
        """从 retriever 提取节点信息"""
        nodes: list[RaptorNode] = []
        
        if not self._retriever:
            return nodes
        
        # 尝试从 retriever 的 index 获取所有节点
        try:
            # 使用公开的 index 属性（不是 _index）
            index = self._retriever.index
            if hasattr(index, "docstore") and hasattr(index.docstore, "docs"):
                for node_id, node in index.docstore.docs.items():
                    # RAPTOR 使用 'level' 字段标记层级
                    # 原始文档没有 level 字段，摘要节点有 level 字段（0=第一层摘要, 1=第二层...）
                    # 我们将原始文档标记为 level=-1，摘要从 0 开始
                    level = node.metadata.get("level", -1)
                    parent_id = node.metadata.get("parent_id", "")
                    nodes.append(RaptorNode(
                        id=str(node_id),
                        text=node.text,
                        level=level,
                        children_ids=[parent_id] if parent_id else [],
                        metadata=dict(node.metadata),
                    ))
        except Exception as e:
            logger.warning(f"提取 RAPTOR 节点失败: {e}")
            # 返回空列表，不影响主流程
        
        return nodes
    
    def get_retriever(
        self,
        mode: str = "collapsed",
        top_k: int = 5,
    ) -> "RaptorRetrieverWrapper":
        """
        获取检索器
        
        Args:
            mode: 检索模式
                - "collapsed": 扁平化检索，所有层级节点一起检索
                - "tree_traversal": 树遍历检索，从顶层向下
            top_k: 返回的节点数量
            
        Returns:
            检索器包装器
        """
        if not self._retriever:
            raise RuntimeError("请先调用 build_from_* 方法构建索引")
        
        return RaptorRetrieverWrapper(
            retriever=self._retriever,
            mode=mode,
            top_k=top_k,
        )
    
    async def save_to_db(
        self,
        session: AsyncSession,
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
            chunk_id_mapping: 原始文档 ID 到 chunk_id 的映射（用于叶子节点关联）
            
        Returns:
            保存的节点数量
        """
        from app.models.raptor_node import RaptorNode as RaptorNodeModel
        
        nodes = self._extract_nodes()
        if not nodes:
            logger.warning("没有节点需要保存")
            return 0
        
        chunk_id_mapping = chunk_id_mapping or {}
        saved_count = 0
        
        # 创建节点 ID 映射（LlamaIndex ID -> 数据库 ID）
        id_mapping: dict[str, str] = {}
        
        for node in nodes:
            db_id = str(uuid4())
            id_mapping[node.id] = db_id
        
        # 保存节点
        for node in nodes:
            db_id = id_mapping[node.id]
            
            # 查找关联的原始 chunk ID（仅叶子节点）
            chunk_id = None
            if node.level == 0:
                # 尝试从 metadata 或映射中获取原始 chunk ID
                original_doc_id = node.metadata.get("doc_id") or node.metadata.get("original_id")
                if original_doc_id and original_doc_id in chunk_id_mapping:
                    chunk_id = chunk_id_mapping[original_doc_id]
            
            # 映射父节点 ID
            parent_id = None
            if node.children_ids:  # 注意：这里 children_ids 实际存储的是 parent_id
                parent_llama_id = node.children_ids[0]
                parent_id = id_mapping.get(parent_llama_id)
            
            # 映射子节点 ID
            children_ids = []
            # 从其他节点的 parent_id 反推子节点
            for other_node in nodes:
                if other_node.children_ids and other_node.children_ids[0] == node.id:
                    children_ids.append(id_mapping[other_node.id])
            
            db_node = RaptorNodeModel(
                id=db_id,
                tenant_id=tenant_id,
                knowledge_base_id=knowledge_base_id,
                chunk_id=chunk_id,
                text=node.text,
                level=node.level,
                parent_id=parent_id,
                children_ids=children_ids,
                indexing_status="pending",
                extra_metadata=node.metadata,
            )
            session.add(db_node)
            saved_count += 1
        
        await session.flush()
        logger.info(f"保存了 {saved_count} 个 RAPTOR 节点到数据库")
        return saved_count
    
    @classmethod
    async def load_from_db(
        cls,
        session: AsyncSession,
        tenant_id: str,
        knowledge_base_id: str,
    ) -> list["RaptorNode"]:
        """
        从数据库加载 RAPTOR 节点
        
        Args:
            session: 数据库会话
            tenant_id: 租户 ID
            knowledge_base_id: 知识库 ID
            
        Returns:
            RAPTOR 节点列表
        """
        from app.models.raptor_node import RaptorNode as RaptorNodeModel
        
        stmt = (
            select(RaptorNodeModel)
            .where(RaptorNodeModel.tenant_id == tenant_id)
            .where(RaptorNodeModel.knowledge_base_id == knowledge_base_id)
            .order_by(RaptorNodeModel.level, RaptorNodeModel.created_at)
        )
        
        result = await session.execute(stmt)
        db_nodes = result.scalars().all()
        
        nodes = []
        for db_node in db_nodes:
            nodes.append(RaptorNode(
                id=db_node.id,
                text=db_node.text,
                level=db_node.level,
                children_ids=db_node.children_ids or [],
                metadata=db_node.extra_metadata or {},
            ))
        
        logger.info(f"从数据库加载了 {len(nodes)} 个 RAPTOR 节点")
        return nodes
    
    @classmethod
    async def delete_from_db(
        cls,
        session: AsyncSession,
        tenant_id: str,
        knowledge_base_id: str,
    ) -> int:
        """
        从数据库删除 RAPTOR 节点
        
        Args:
            session: 数据库会话
            tenant_id: 租户 ID
            knowledge_base_id: 知识库 ID
            
        Returns:
            删除的节点数量
        """
        from app.models.raptor_node import RaptorNode as RaptorNodeModel
        
        stmt = (
            delete(RaptorNodeModel)
            .where(RaptorNodeModel.tenant_id == tenant_id)
            .where(RaptorNodeModel.knowledge_base_id == knowledge_base_id)
        )
        
        result = await session.execute(stmt)
        deleted_count = result.rowcount
        
        logger.info(f"从数据库删除了 {deleted_count} 个 RAPTOR 节点")
        return deleted_count
    
    @classmethod
    async def has_index(
        cls,
        session: AsyncSession,
        tenant_id: str,
        knowledge_base_id: str,
    ) -> bool:
        """
        检查知识库是否有 RAPTOR 索引
        
        Args:
            session: 数据库会话
            tenant_id: 租户 ID
            knowledge_base_id: 知识库 ID
            
        Returns:
            是否存在 RAPTOR 索引
        """
        from app.models.raptor_node import RaptorNode as RaptorNodeModel
        from sqlalchemy import func
        
        stmt = (
            select(func.count(RaptorNodeModel.id))
            .where(RaptorNodeModel.tenant_id == tenant_id)
            .where(RaptorNodeModel.knowledge_base_id == knowledge_base_id)
        )
        
        result = await session.execute(stmt)
        count = result.scalar() or 0
        
        return count > 0


class RaptorRetrieverWrapper:
    """
    RAPTOR 检索器包装器
    
    提供统一的检索接口，适配项目的检索器协议。
    """
    
    def __init__(
        self,
        retriever: Any,
        mode: str = "collapsed",
        top_k: int = 5,
    ):
        self._retriever = retriever
        self.mode = mode
        self.top_k = top_k
    
    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        检索相关节点
        
        Args:
            query: 查询文本
            top_k: 返回数量，默认使用初始化时的值
            
        Returns:
            检索结果列表
        """
        k = top_k or self.top_k
        
        # 调用 LlamaIndex retriever
        nodes = self._retriever.retrieve(query, mode=self.mode)
        
        # 转换为统一格式
        results = []
        for i, node in enumerate(nodes[:k]):
            metadata = dict(node.node.metadata) if hasattr(node.node, "metadata") else {}
            # LlamaIndex RAPTOR 使用 'level' 字段标记摘要层级
            # level=-1 表示原始文档，level>=0 表示摘要层级
            level = metadata.get("level", -1)
            
            results.append({
                "chunk_id": str(node.node.node_id) if hasattr(node.node, "node_id") else str(uuid4()),
                "text": node.node.text,
                "score": node.score if hasattr(node, "score") else 1.0 - i * 0.01,
                "metadata": metadata,
                "source": "raptor",
                "raptor_level": level,  # -1=原始文档, 0+=摘要层级
            })
        
        return results


def create_raptor_indexer_from_config(
    embedding_config: dict | None = None,
) -> RaptorIndexer | None:
    """
    从应用配置创建 RAPTOR 索引器
    
    读取 LLM 和 Embedding 配置，创建索引器实例。
    支持 Ollama 和 OpenAI 提供商。
    
    Args:
        embedding_config: 可选的 Embedding 配置（来自 KB/Ground），格式为 {provider, model, api_key, base_url}
                         如果提供，优先使用此配置；否则使用全局 settings
    """
    if not RAPTOR_AVAILABLE:
        logger.warning("RAPTOR 不可用，跳过创建索引器")
        return None
    
    try:
        from app.config import get_settings
        settings = get_settings()
        
        # 根据提供商创建 LLM（使用全局 settings 的 LLM 配置）
        llm = None
        llm_config = settings.get_llm_config()
        llm_provider = llm_config.get("provider", "ollama")
        llm_model_name = llm_config.get("model", settings.llm_model)
        llm_api_key = llm_config.get("api_key")
        llm_base_url = llm_config.get("base_url")
        
        if llm_provider == "ollama":
            try:
                from llama_index.llms.ollama import Ollama
                llm = Ollama(
                    model=llm_model_name,
                    base_url=llm_base_url or settings.ollama_base_url,
                    request_timeout=120.0,
                )
            except ImportError:
                logger.warning("llama-index-llms-ollama 未安装，尝试使用 OpenAI 兼容模式")
        
        if llm is None:
            # 使用 OpenAI 兼容模式
            if llm_provider == "ollama":
                from llama_index.llms.openai import OpenAI
                llm = OpenAI(
                    model=llm_model_name,
                    api_base=f"{llm_base_url or settings.ollama_base_url}/v1",
                    api_key="ollama",
                )
            elif llm_provider in ("siliconflow", "qwen", "zhipu", "deepseek", "kimi", "gemini"):
                # OpenAI 兼容服务 - 使用 OpenAILike 绕过模型名验证
                try:
                    from llama_index.llms.openai_like import OpenAILike
                    llm = OpenAILike(
                        model=llm_model_name,
                        api_base=llm_base_url,
                        api_key=llm_api_key or "dummy",
                        is_chat_model=True,
                        context_window=32000,  # 默认上下文窗口
                    )
                    logger.info(f"[RAPTOR] 使用 OpenAILike LLM: {llm_provider}/{llm_model_name}")
                except ImportError:
                    # 如果没有 OpenAILike，回退到自定义实现
                    from openai import OpenAI as OpenAIClient
                    from llama_index.core.llms import CustomLLM, CompletionResponse, LLMMetadata
                    from llama_index.core.llms.callbacks import llm_completion_callback
                    
                    class OpenAICompatibleLLM(CustomLLM):
                        """OpenAI 兼容 API 的 LLM 实现"""
                        _model_name: str
                        _client: OpenAIClient
                        _context_window: int = 32000
                        
                        def __init__(self, model_name: str, api_key: str, api_base: str):
                            super().__init__()
                            object.__setattr__(self, '_model_name', model_name)
                            object.__setattr__(self, '_client', OpenAIClient(api_key=api_key, base_url=api_base))
                        
                        @property
                        def metadata(self) -> LLMMetadata:
                            return LLMMetadata(
                                model_name=self._model_name,
                                context_window=self._context_window,
                                is_chat_model=True,
                            )
                        
                        @llm_completion_callback()
                        def complete(self, prompt: str, **kwargs) -> CompletionResponse:
                            response = self._client.chat.completions.create(
                                model=self._model_name,
                                messages=[{"role": "user", "content": prompt}],
                                **kwargs,
                            )
                            return CompletionResponse(text=response.choices[0].message.content or "")
                        
                        @llm_completion_callback()
                        async def acomplete(self, prompt: str, **kwargs) -> CompletionResponse:
                            return self.complete(prompt, **kwargs)
                        
                        def stream_complete(self, prompt: str, **kwargs):
                            raise NotImplementedError("Streaming not supported")
                    
                    llm = OpenAICompatibleLLM(
                        model_name=llm_model_name,
                        api_key=llm_api_key or "dummy",
                        api_base=llm_base_url,
                    )
                    logger.info(f"[RAPTOR] 使用自定义 OpenAI 兼容 LLM: {llm_provider}/{llm_model_name}")
            else:
                # 原生 OpenAI
                from llama_index.llms.openai import OpenAI
                llm = OpenAI(
                    model=llm_model_name,
                    api_key=llm_api_key or settings.openai_api_key,
                )
        
        # 根据提供商创建 Embedding
        # 优先使用传入的 embedding_config（来自 KB/Ground），否则使用全局 settings
        embed_model = None
        if embedding_config:
            embed_provider = embedding_config.get("provider", "ollama")
            embed_model_name = embedding_config.get("model", settings.embedding_model)
            embed_api_key = embedding_config.get("api_key")
            embed_base_url = embedding_config.get("base_url")
        else:
            embed_cfg = settings.get_embedding_config()
            embed_provider = embed_cfg.get("provider", "ollama")
            embed_model_name = embed_cfg.get("model", settings.embedding_model)
            embed_api_key = embed_cfg.get("api_key")
            embed_base_url = embed_cfg.get("base_url")
        
        if embed_provider == "ollama":
            try:
                from llama_index.embeddings.ollama import OllamaEmbedding
                embed_model = OllamaEmbedding(
                    model_name=embed_model_name,
                    base_url=embed_base_url or settings.ollama_base_url,
                )
            except ImportError:
                logger.warning("llama-index-embeddings-ollama 未安装，尝试使用 OpenAI 兼容模式")
        
        # 对于非 Ollama 提供商，使用 OpenAI 兼容模式
        if embed_model is None:
            # 对于 OpenAI 兼容服务（siliconflow, qwen, zhipu 等），需要设置 api_base
            # 使用 OpenAIEmbedding 时，非标准模型名会导致 enum 校验失败
            # 所以使用 LlamaIndex 的 OpenAILike 或通用方式
            if embed_provider in ("siliconflow", "qwen", "zhipu", "deepseek", "kimi", "gemini"):
                try:
                    # 尝试使用 OpenAILike 或 HuggingFaceEmbedding 的方式
                    from openai import OpenAI as OpenAIClient
                    from llama_index.core.embeddings import BaseEmbedding
                    from llama_index.embeddings.openai import OpenAIEmbedding
                    
                    # 创建一个简单的自定义 Embedding 类来绕过模型名校验
                    class OpenAICompatibleEmbedding(BaseEmbedding):
                        """OpenAI 兼容 API 的 Embedding 实现（带速率限制）"""
                        
                        # 批量大小和速率限制
                        BATCH_SIZE: int = 10  # 每批最多 10 个文本
                        RATE_LIMIT_DELAY: float = 0.5  # 每批之间等待 0.5 秒
                        
                        def __init__(self, model_name: str, api_key: str, api_base: str):
                            super().__init__()
                            self._model_name = model_name
                            self._client = OpenAIClient(
                                api_key=api_key, 
                                base_url=api_base,
                                timeout=60.0,  # 60 秒超时
                                max_retries=3,  # 最多重试 3 次
                            )
                        
                        @property
                        def model_name(self) -> str:
                            return self._model_name
                        
                        def _get_query_embedding(self, query: str) -> list[float]:
                            response = self._client.embeddings.create(
                                input=[query],
                                model=self._model_name,
                            )
                            return response.data[0].embedding
                        
                        def _get_text_embedding(self, text: str) -> list[float]:
                            return self._get_query_embedding(text)
                        
                        def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
                            """批量获取 embeddings，带速率限制"""
                            import time
                            
                            all_embeddings = []
                            total = len(texts)
                            
                            # 分批处理
                            for i in range(0, total, self.BATCH_SIZE):
                                batch = texts[i:i + self.BATCH_SIZE]
                                batch_num = i // self.BATCH_SIZE + 1
                                total_batches = (total + self.BATCH_SIZE - 1) // self.BATCH_SIZE
                                
                                logger.info(f"[RAPTOR Embedding] 批次 {batch_num}/{total_batches}，处理 {len(batch)} 个文本")
                                
                                try:
                                    response = self._client.embeddings.create(
                                        input=batch,
                                        model=self._model_name,
                                    )
                                    all_embeddings.extend([item.embedding for item in response.data])
                                except Exception as e:
                                    logger.error(f"[RAPTOR Embedding] 批次 {batch_num} 失败: {e}")
                                    raise
                                
                                # 速率限制：每批之间等待
                                if i + self.BATCH_SIZE < total:
                                    time.sleep(self.RATE_LIMIT_DELAY)
                            
                            return all_embeddings
                        
                        async def _aget_query_embedding(self, query: str) -> list[float]:
                            return self._get_query_embedding(query)
                        
                        async def _aget_text_embedding(self, text: str) -> list[float]:
                            return self._get_text_embedding(text)
                    
                    embed_model = OpenAICompatibleEmbedding(
                        model_name=embed_model_name,
                        api_key=embed_api_key or "dummy",
                        api_base=embed_base_url,
                    )
                    logger.info(f"[RAPTOR] 使用 OpenAI 兼容 Embedding: {embed_provider}/{embed_model_name}")
                except Exception as e:
                    logger.error(f"[RAPTOR] 创建 OpenAI 兼容 Embedding 失败: {e}")
                    raise
            else:
                # 原生 OpenAI
                from llama_index.embeddings.openai import OpenAIEmbedding
                embed_model = OpenAIEmbedding(
                    model=embed_model_name,
                    api_key=embed_api_key or settings.openai_api_key or "dummy",
                )
        
        logger.info(f"创建 RAPTOR 索引器: LLM={llm_provider}/{llm_model_name}, "
                    f"Embedding={embed_provider}/{embed_model_name}")
        
        return RaptorIndexer(
            llm=llm,
            embed_model=embed_model,
        )
    except Exception as e:
        logger.error(f"创建 RAPTOR 索引器失败: {e}")
        import traceback
        traceback.print_exc()
        return None
