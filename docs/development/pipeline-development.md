# Pipeline 开发指南

本文档介绍 Self-RAG Pipeline 中可插拔算法框架的开发和扩展，包括切分器、检索器、查询变换器等组件的实现。

## 架构概述

Self-RAG Pipeline 采用可插拔的算法框架，支持动态注册和发现算法组件。核心设计理念：

- **模块化**：每个算法组件独立实现，便于测试和维护
- **可扩展**：通过注册机制轻松添加新算法
- **配置化**：通过配置文件动态选择和配置算法
- **标准化**：统一的接口规范，确保组件间的兼容性

### 核心组件

```
app/pipeline/
├── base.py              # 基础协议定义
├── registry.py          # 算法注册表
├── chunkers/            # 切分器实现
├── retrievers/          # 检索器实现
├── query_transforms/    # 查询变换器
├── enrichers/           # 文档增强器
├── postprocessors/      # 后处理器
└── indexers/           # 索引器
```

## 基础协议

### 切分器协议 (ChunkerProtocol)

```python
from typing import Protocol, List
from app.schemas.chunk import ChunkPiece

class ChunkerProtocol(Protocol):
    """切分器协议定义"""
    
    def chunk(self, text: str, metadata: dict | None = None) -> List[ChunkPiece]:
        """
        将文本切分为多个片段
        
        Args:
            text: 待切分的文本
            metadata: 文档元数据
            
        Returns:
            切分后的片段列表
        """
        ...
```

### 检索器协议 (RetrieverProtocol)

```python
from typing import Protocol, List
from app.schemas.query import RetrievalResult

class RetrieverProtocol(Protocol):
    """检索器协议定义"""
    
    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        kb_ids: List[str],
        top_k: int = 10,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        执行检索操作
        
        Args:
            query: 查询文本
            tenant_id: 租户 ID
            kb_ids: 知识库 ID 列表
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        ...
```

## 开发新的切分器

### 1. 实现切分器类

```python
# app/pipeline/chunkers/my_chunker.py
from typing import List
from app.schemas.chunk import ChunkPiece
from app.pipeline.base import ChunkerProtocol

class MyChunker:
    """自定义切分器示例"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str, metadata: dict | None = None) -> List[ChunkPiece]:
        """实现切分逻辑"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            
            # 创建切分片段
            piece = ChunkPiece(
                text=chunk_text,
                metadata={
                    **(metadata or {}),
                    "chunk_index": len(chunks),
                    "start_pos": start,
                    "end_pos": end,
                }
            )
            chunks.append(piece)
            
            # 计算下一个起始位置（考虑重叠）
            start = end - self.overlap if end < len(text) else end
        
        return chunks
```

### 2. 注册切分器

```python
# app/pipeline/chunkers/__init__.py
from app.pipeline.registry import operator_registry
from .my_chunker import MyChunker

# 注册切分器
operator_registry.register("chunker", "my_chunker", MyChunker)
```

### 3. 添加配置支持

```python
# app/pipeline/chunkers/my_chunker.py
def create_my_chunker_from_config(config: dict) -> MyChunker:
    """从配置创建切分器实例"""
    return MyChunker(
        chunk_size=config.get("chunk_size", 1000),
        overlap=config.get("overlap", 100),
    )

# 注册工厂函数
operator_registry.register(
    "chunker", 
    "my_chunker", 
    create_my_chunker_from_config
)
```

### 4. 使用示例

```python
from app.pipeline import operator_registry

# 通过注册表获取切分器
chunker = operator_registry.get("chunker", "my_chunker")(
    chunk_size=800,
    overlap=50
)

# 执行切分
pieces = chunker.chunk("长文本内容...")
```

## 开发新的检索器

### 1. 实现检索器类

```python
# app/pipeline/retrievers/my_retriever.py
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.query import RetrievalResult
from app.pipeline.base import RetrieverProtocol
from app.infra.vector_store import get_vector_store

class MyRetriever:
    """自定义检索器示例"""
    
    def __init__(self, alpha: float = 0.7, beta: float = 0.3):
        self.alpha = alpha  # 向量检索权重
        self.beta = beta    # BM25 检索权重
    
    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        kb_ids: List[str],
        top_k: int = 10,
        session: AsyncSession | None = None,
        **kwargs
    ) -> List[RetrievalResult]:
        """实现检索逻辑"""
        
        # 1. 向量检索
        vector_store = get_vector_store()
        vector_results = await vector_store.search(
            query=query,
            tenant_id=tenant_id,
            kb_ids=kb_ids,
            top_k=top_k * 2,  # 获取更多候选
        )
        
        # 2. BM25 检索（示例）
        bm25_results = await self._bm25_search(
            query, tenant_id, kb_ids, top_k * 2, session
        )
        
        # 3. 融合结果
        fused_results = self._fuse_results(
            vector_results, bm25_results, top_k
        )
        
        return fused_results
    
    async def _bm25_search(
        self, query: str, tenant_id: str, kb_ids: List[str], 
        top_k: int, session: AsyncSession
    ) -> List[RetrievalResult]:
        """BM25 检索实现"""
        # 实现 BM25 检索逻辑
        pass
    
    def _fuse_results(
        self, 
        vector_results: List[RetrievalResult],
        bm25_results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """结果融合逻辑"""
        # 实现 RRF 或加权融合
        pass
```

### 2. 注册检索器

```python
# app/pipeline/retrievers/__init__.py
from app.pipeline.registry import operator_registry
from .my_retriever import MyRetriever

operator_registry.register("retriever", "my_retriever", MyRetriever)
```

### 3. 添加到 Schema

```python
# app/schemas/query.py
from typing import Literal

RetrieverName = Literal[
    "dense",
    "bm25", 
    "hybrid",
    "fusion",
    "hyde",
    "my_retriever",  # 添加新检索器
    # ... 其他检索器
]
```

## 开发查询变换器

### 1. 实现查询变换器

```python
# app/pipeline/query_transforms/my_transform.py
from typing import List
from app.infra.llm import get_llm_client

class MyQueryTransform:
    """自定义查询变换器"""
    
    def __init__(self, num_variants: int = 3):
        self.num_variants = num_variants
    
    async def transform(self, query: str) -> List[str]:
        """生成查询变体"""
        llm = get_llm_client()
        
        prompt = f"""
        基于用户查询，生成 {self.num_variants} 个语义相似但表达不同的查询变体。
        
        原始查询：{query}
        
        要求：
        1. 保持原意不变
        2. 使用不同的词汇和表达方式
        3. 每行一个查询变体
        """
        
        response = await llm.agenerate([prompt])
        variants = response.generations[0][0].text.strip().split('\n')
        
        # 清理和过滤结果
        variants = [v.strip() for v in variants if v.strip()]
        variants = variants[:self.num_variants]
        
        # 包含原始查询
        return [query] + variants
```

### 2. 集成到检索器

```python
# app/pipeline/retrievers/enhanced_retriever.py
class EnhancedRetriever:
    def __init__(self, base_retriever: str = "dense", use_transform: bool = True):
        self.base_retriever = base_retriever
        self.use_transform = use_transform
        self.query_transform = MyQueryTransform() if use_transform else None
    
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        queries = [query]
        
        if self.query_transform:
            queries = await self.query_transform.transform(query)
        
        # 对每个查询执行检索
        all_results = []
        for q in queries:
            results = await self._base_retrieve(q, **kwargs)
            all_results.extend(results)
        
        # 去重和重排
        return self._deduplicate_and_rerank(all_results, kwargs.get("top_k", 10))
```

## 开发文档增强器

### 1. 实现增强器

```python
# app/pipeline/enrichers/my_enricher.py
from typing import Optional
from app.infra.llm import get_llm_client

class MyDocumentEnricher:
    """自定义文档增强器"""
    
    def __init__(self, enhancement_type: str = "summary"):
        self.enhancement_type = enhancement_type
    
    async def enrich(
        self, 
        content: str, 
        title: str,
        metadata: dict | None = None
    ) -> dict:
        """增强文档内容"""
        
        if self.enhancement_type == "summary":
            return await self._generate_summary(content, title)
        elif self.enhancement_type == "keywords":
            return await self._extract_keywords(content, title)
        else:
            return {"original_content": content}
    
    async def _generate_summary(self, content: str, title: str) -> dict:
        """生成文档摘要"""
        llm = get_llm_client()
        
        prompt = f"""
        为以下文档生成简洁的摘要：
        
        标题：{title}
        内容：{content[:2000]}...
        
        要求：
        1. 摘要长度控制在 200 字以内
        2. 突出文档的核心内容和关键信息
        3. 使用客观、准确的语言
        """
        
        response = await llm.agenerate([prompt])
        summary = response.generations[0][0].text.strip()
        
        return {
            "summary": summary,
            "enhancement_type": "summary",
            "original_length": len(content),
            "summary_length": len(summary)
        }
    
    async def _extract_keywords(self, content: str, title: str) -> dict:
        """提取关键词"""
        llm = get_llm_client()
        
        prompt = f"""
        从以下文档中提取 5-10 个关键词：
        
        标题：{title}
        内容：{content[:1500]}...
        
        要求：
        1. 关键词应该是名词或名词短语
        2. 按重要性排序
        3. 用逗号分隔
        """
        
        response = await llm.agenerate([prompt])
        keywords_text = response.generations[0][0].text.strip()
        keywords = [kw.strip() for kw in keywords_text.split(',')]
        
        return {
            "keywords": keywords,
            "enhancement_type": "keywords",
            "keyword_count": len(keywords)
        }
```

### 2. 集成到入库流程

```python
# app/services/ingestion.py
async def ingest_document_with_enrichment(
    session: AsyncSession,
    tenant_id: str,
    kb: KnowledgeBase,
    title: str,
    content: str,
    enable_enrichment: bool = False,
    **kwargs
) -> tuple[Document, List[Chunk]]:
    """带增强功能的文档入库"""
    
    enriched_metadata = {}
    
    if enable_enrichment:
        enricher = MyDocumentEnricher()
        enriched_metadata = await enricher.enrich(content, title)
    
    # 正常的入库流程
    doc, chunks = await ingest_document(
        session=session,
        tenant_id=tenant_id,
        kb=kb,
        title=title,
        content=content,
        metadata={**kwargs.get("metadata", {}), **enriched_metadata},
        **kwargs
    )
    
    return doc, chunks
```

## 开发后处理器

### 1. 实现后处理器

```python
# app/pipeline/postprocessors/my_postprocessor.py
from typing import List
from app.schemas.query import RetrievalResult

class MyPostprocessor:
    """自定义后处理器"""
    
    def __init__(self, score_threshold: float = 0.5, max_results: int = 10):
        self.score_threshold = score_threshold
        self.max_results = max_results
    
    async def process(
        self, 
        results: List[RetrievalResult],
        query: str,
        **kwargs
    ) -> List[RetrievalResult]:
        """后处理检索结果"""
        
        # 1. 分数过滤
        filtered_results = [
            r for r in results 
            if r.score >= self.score_threshold
        ]
        
        # 2. 去重（基于内容相似度）
        deduplicated_results = await self._deduplicate(filtered_results)
        
        # 3. 重排序
        reranked_results = await self._rerank(deduplicated_results, query)
        
        # 4. 限制数量
        return reranked_results[:self.max_results]
    
    async def _deduplicate(
        self, results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """去重逻辑"""
        seen_texts = set()
        unique_results = []
        
        for result in results:
            # 简单的文本去重
            text_hash = hash(result.text[:100])  # 使用前100字符的哈希
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_results.append(result)
        
        return unique_results
    
    async def _rerank(
        self, results: List[RetrievalResult], query: str
    ) -> List[RetrievalResult]:
        """重排序逻辑"""
        # 可以集成 Cross-encoder 模型进行重排
        # 这里使用简单的长度惩罚作为示例
        
        for result in results:
            # 长度惩罚：过长或过短的文本降低分数
            length_penalty = 1.0
            text_length = len(result.text)
            
            if text_length < 50:  # 太短
                length_penalty = 0.8
            elif text_length > 2000:  # 太长
                length_penalty = 0.9
            
            result.score *= length_penalty
        
        # 按分数重新排序
        return sorted(results, key=lambda x: x.score, reverse=True)
```

### 2. 集成到检索流程

```python
# app/services/query.py
async def retrieve_with_postprocessing(
    tenant_id: str,
    kbs: List[KnowledgeBase],
    query: str,
    top_k: int = 10,
    enable_postprocessing: bool = True,
    **kwargs
) -> List[RetrievalResult]:
    """带后处理的检索"""
    
    # 执行基础检索
    results = await basic_retrieve(tenant_id, kbs, query, top_k * 2, **kwargs)
    
    if enable_postprocessing:
        postprocessor = MyPostprocessor(max_results=top_k)
        results = await postprocessor.process(results, query)
    
    return results
```

## 算法性能优化

### 1. 缓存策略

```python
from functools import lru_cache
from app.infra.cache import get_redis_client

class CachedRetriever:
    def __init__(self, base_retriever: RetrieverProtocol):
        self.base_retriever = base_retriever
        self.redis = get_redis_client()
    
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        # 生成缓存键
        cache_key = self._generate_cache_key(query, kwargs)
        
        # 尝试从缓存获取
        cached_result = await self.redis.get(cache_key)
        if cached_result:
            return self._deserialize_results(cached_result)
        
        # 执行检索
        results = await self.base_retriever.retrieve(query, **kwargs)
        
        # 缓存结果
        await self.redis.setex(
            cache_key, 
            3600,  # 1小时过期
            self._serialize_results(results)
        )
        
        return results
    
    def _generate_cache_key(self, query: str, kwargs: dict) -> str:
        """生成缓存键"""
        import hashlib
        key_data = f"{query}:{sorted(kwargs.items())}"
        return f"retrieval:{hashlib.md5(key_data.encode()).hexdigest()}"
```

### 2. 批量处理

```python
class BatchProcessor:
    """批量处理器，提高吞吐量"""
    
    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
    
    async def process_batch(
        self, 
        items: List[str], 
        processor_func: callable
    ) -> List:
        """批量处理"""
        results = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = await processor_func(batch)
            results.extend(batch_results)
        
        return results
```

### 3. 异步并发

```python
import asyncio
from typing import List, Awaitable

class ConcurrentProcessor:
    """并发处理器"""
    
    def __init__(self, max_concurrency: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrency)
    
    async def process_concurrent(
        self, 
        tasks: List[Awaitable]
    ) -> List:
        """并发执行任务"""
        
        async def limited_task(task):
            async with self.semaphore:
                return await task
        
        # 并发执行所有任务
        results = await asyncio.gather(
            *[limited_task(task) for task in tasks],
            return_exceptions=True
        )
        
        # 过滤异常结果
        return [r for r in results if not isinstance(r, Exception)]
```

## 测试和调试

### 1. 单元测试

```python
# tests/test_my_chunker.py
import pytest
from app.pipeline.chunkers.my_chunker import MyChunker

class TestMyChunker:
    def test_basic_chunking(self):
        chunker = MyChunker(chunk_size=100, overlap=20)
        text = "这是一个测试文本。" * 20  # 创建长文本
        
        chunks = chunker.chunk(text)
        
        assert len(chunks) > 1
        assert all(len(chunk.text) <= 100 for chunk in chunks)
        assert chunks[0].metadata["chunk_index"] == 0
    
    def test_overlap_behavior(self):
        chunker = MyChunker(chunk_size=50, overlap=10)
        text = "A" * 100
        
        chunks = chunker.chunk(text)
        
        # 检查重叠
        assert len(chunks) >= 2
        # 第二个chunk应该包含第一个chunk的末尾部分
```

### 2. 集成测试

```python
# tests/test_retriever_integration.py
import pytest
from app.pipeline.retrievers.my_retriever import MyRetriever
from app.tests.conftest import test_kb, sample_documents

@pytest.mark.asyncio
async def test_retriever_integration(test_kb, sample_documents):
    # 上传测试文档
    for doc in sample_documents:
        await upload_document(test_kb.id, doc)
    
    # 测试检索
    retriever = MyRetriever()
    results = await retriever.retrieve(
        query="Python 编程",
        tenant_id=test_kb.tenant_id,
        kb_ids=[test_kb.id],
        top_k=5
    )
    
    assert len(results) > 0
    assert all(result.score > 0 for result in results)
```

### 3. 性能测试

```python
# tests/test_performance.py
import time
import pytest
from app.pipeline.chunkers.my_chunker import MyChunker

class TestPerformance:
    def test_chunker_performance(self):
        chunker = MyChunker()
        large_text = "测试文本。" * 10000  # 大文本
        
        start_time = time.time()
        chunks = chunker.chunk(large_text)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # 性能断言
        assert processing_time < 1.0  # 应该在1秒内完成
        assert len(chunks) > 0
        
        print(f"处理时间: {processing_time:.3f}秒")
        print(f"生成chunks: {len(chunks)}个")
        print(f"处理速度: {len(large_text)/processing_time:.0f} 字符/秒")
```

## 最佳实践

### 1. 错误处理

```python
class RobustRetriever:
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        try:
            return await self._do_retrieve(query, **kwargs)
        except Exception as e:
            logger.error(f"检索失败: {e}", exc_info=True)
            
            # 降级策略：返回简单的文本匹配结果
            return await self._fallback_retrieve(query, **kwargs)
    
    async def _fallback_retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        """降级检索策略"""
        # 实现简单的文本匹配作为后备方案
        pass
```

### 2. 配置管理

```python
from pydantic import BaseModel

class ChunkerConfig(BaseModel):
    """切分器配置"""
    name: str
    chunk_size: int = 1000
    overlap: int = 100
    language: str | None = None

class RetrieverConfig(BaseModel):
    """检索器配置"""
    name: str
    top_k: int = 10
    score_threshold: float = 0.0
    enable_rerank: bool = False

def create_chunker_from_config(config: ChunkerConfig):
    """从配置创建切分器"""
    chunker_class = operator_registry.get("chunker", config.name)
    return chunker_class(
        chunk_size=config.chunk_size,
        overlap=config.overlap,
        language=config.language
    )
```

### 3. 监控和日志

```python
import logging
from app.infra.metrics import record_metric

logger = logging.getLogger(__name__)

class MonitoredRetriever:
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        start_time = time.time()
        
        try:
            results = await self._do_retrieve(query, **kwargs)
            
            # 记录成功指标
            record_metric("retrieval.success", 1, {
                "retriever": self.__class__.__name__,
                "result_count": len(results)
            })
            
            return results
            
        except Exception as e:
            # 记录失败指标
            record_metric("retrieval.error", 1, {
                "retriever": self.__class__.__name__,
                "error_type": type(e).__name__
            })
            raise
            
        finally:
            # 记录耗时
            duration = time.time() - start_time
            record_metric("retrieval.duration", duration, {
                "retriever": self.__class__.__name__
            })
            
            logger.info(f"检索完成，耗时: {duration:.3f}秒")
```

### 4. 版本兼容性

```python
class VersionedAlgorithm:
    """支持版本化的算法"""
    
    VERSION = "1.0.0"
    
    def __init__(self, **kwargs):
        self.config_version = kwargs.get("version", self.VERSION)
        
        # 根据版本调整行为
        if self.config_version < "1.0.0":
            self._setup_legacy_mode()
        else:
            self._setup_current_mode()
    
    def _setup_legacy_mode(self):
        """兼容旧版本配置"""
        pass
    
    def _setup_current_mode(self):
        """当前版本配置"""
        pass
```

通过遵循这些开发指南，可以高效地扩展和维护 Pipeline 算法框架，确保系统的可扩展性和稳定性。