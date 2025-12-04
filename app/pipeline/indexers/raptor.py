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
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

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
        logger.info(f"开始构建 RAPTOR 索引，共 {len(documents)} 个文档")
        
        # 创建 SummaryModule 配置
        summary_module = SummaryModule(
            llm=self.llm,
            summary_prompt=self.summary_prompt,
            num_workers=self.summary_num_workers,
        )
        
        # 构建 RaptorPack
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
        
        # 统计结果
        # 注意：LlamaIndex RaptorPack 内部会自动处理聚类和摘要
        # 我们只能通过 retriever 获取节点信息
        nodes = self._extract_nodes()
        
        leaf_count = sum(1 for n in nodes if n.level == 0)
        summary_count = len(nodes) - leaf_count
        max_level = max((n.level for n in nodes), default=0)
        
        logger.info(
            f"RAPTOR 索引构建完成: "
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
    
    def save(self, path: str) -> None:
        """保存索引到磁盘"""
        # TODO: 实现持久化
        raise NotImplementedError("持久化功能待实现")
    
    @classmethod
    def load(cls, path: str) -> "RaptorIndexer":
        """从磁盘加载索引"""
        # TODO: 实现加载
        raise NotImplementedError("加载功能待实现")


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


def create_raptor_indexer_from_config() -> RaptorIndexer | None:
    """
    从应用配置创建 RAPTOR 索引器
    
    读取 LLM 和 Embedding 配置，创建索引器实例。
    支持 Ollama 和 OpenAI 提供商。
    """
    if not RAPTOR_AVAILABLE:
        logger.warning("RAPTOR 不可用，跳过创建索引器")
        return None
    
    try:
        from app.config import get_settings
        settings = get_settings()
        
        # 根据提供商创建 LLM
        llm = None
        if settings.llm_provider == "ollama":
            try:
                from llama_index.llms.ollama import Ollama
                llm = Ollama(
                    model=settings.llm_model,
                    base_url=settings.ollama_base_url,
                    request_timeout=120.0,
                )
            except ImportError:
                logger.warning("llama-index-llms-ollama 未安装，尝试使用 OpenAI 兼容模式")
        
        if llm is None:
            # 使用 OpenAI 兼容模式（适用于 Ollama 或其他 OpenAI 兼容服务）
            from llama_index.llms.openai import OpenAI
            if settings.llm_provider == "ollama":
                llm = OpenAI(
                    model=settings.llm_model,
                    api_base=f"{settings.ollama_base_url}/v1",
                    api_key="ollama",  # Ollama 不需要 API Key
                )
            else:
                llm = OpenAI(
                    model=settings.llm_model,
                    api_key=settings.openai_api_key,
                )
        
        # 根据提供商创建 Embedding
        embed_model = None
        if settings.embedding_provider == "ollama":
            try:
                from llama_index.embeddings.ollama import OllamaEmbedding
                embed_model = OllamaEmbedding(
                    model_name=settings.embedding_model,
                    base_url=settings.ollama_base_url,
                )
            except ImportError:
                logger.warning("llama-index-embeddings-ollama 未安装，尝试使用 OpenAI 兼容模式")
        
        if embed_model is None:
            from llama_index.embeddings.openai import OpenAIEmbedding
            embed_model = OpenAIEmbedding(
                model=settings.embedding_model,
                api_key=settings.openai_api_key or "dummy",
            )
        
        logger.info(f"创建 RAPTOR 索引器: LLM={settings.llm_provider}/{settings.llm_model}, "
                    f"Embedding={settings.embedding_provider}/{settings.embedding_model}")
        
        return RaptorIndexer(
            llm=llm,
            embed_model=embed_model,
        )
    except Exception as e:
        logger.error(f"创建 RAPTOR 索引器失败: {e}")
        import traceback
        traceback.print_exc()
        return None
