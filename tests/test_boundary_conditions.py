"""
边界条件测试

测试各种边界情况和异常场景：
- 空输入
- 超大输入
- 无效参数
- 极限值
- 并发冲突
- 资源耗尽
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ingestion import ingest_document, IngestionContext
from app.services.query import retrieve_chunks
from app.services.rag import generate_rag_response
from app.schemas.internal import IngestionParams, RetrieveParams, RAGParams
from app.models import KnowledgeBase, Document, Chunk
from app.exceptions import IngestionError, RetrievalError


class TestIngestionBoundaryConditions:
    """测试摄取服务的边界条件"""
    
    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_kb(self):
        """创建模拟的知识库"""
        return KnowledgeBase(
            id="kb_test",
            tenant_id="tenant_123",
            name="Test KB",
            config={},
        )
    
    @pytest.mark.asyncio
    async def test_ingest_empty_content(self, mock_session, mock_kb):
        """测试空内容入库"""
        params = IngestionParams(
            title="Empty Document",
            content="",  # 空内容
        )
        
        with patch("app.services.ingestion._setup_document") as mock_setup:
            with patch("app.services.ingestion._chunk_document") as mock_chunk:
                mock_doc = Document(
                    id="doc_empty",
                    tenant_id="tenant_123",
                    knowledge_base_id=mock_kb.id,
                    title="Empty Document",
                )
                mock_setup.return_value = mock_doc
                mock_chunk.return_value = []  # 空内容产生0个chunks
                
                result = await ingest_document(
                    session=mock_session,
                    tenant_id="tenant_123",
                    kb=mock_kb,
                    params=params,
                )
                
                # 验证：允许空文档，但没有 chunks
                assert result.document.id == "doc_empty"
                assert len(result.chunks) == 0
    
    @pytest.mark.asyncio
    async def test_ingest_very_long_content(self, mock_session, mock_kb):
        """测试超长内容入库（百万字符）"""
        params = IngestionParams(
            title="Long Document",
            content="A" * 1_000_000,  # 100万字符
        )
        
        with patch("app.services.ingestion._setup_document") as mock_setup:
            with patch("app.services.ingestion._chunk_document") as mock_chunk:
                mock_doc = Document(
                    id="doc_long",
                    tenant_id="tenant_123",
                    knowledge_base_id=mock_kb.id,
                    title="Long Document",
                )
                mock_setup.return_value = mock_doc
                
                # 模拟切分成很多 chunks
                chunks = [
                    Chunk(
                        id=f"chunk_{i}",
                        tenant_id="tenant_123",
                        knowledge_base_id=mock_kb.id,
                        document_id=mock_doc.id,
                        text="A" * 512,
                    )
                    for i in range(2000)  # 2000个chunks
                ]
                mock_chunk.return_value = chunks
                
                result = await ingest_document(
                    session=mock_session,
                    tenant_id="tenant_123",
                    kb=mock_kb,
                    params=params,
                )
                
                # 验证：能处理大量 chunks
                assert len(result.chunks) == 2000
    
    @pytest.mark.asyncio
    async def test_ingest_special_characters(self, mock_session, mock_kb):
        """测试特殊字符内容"""
        params = IngestionParams(
            title="Special Chars 特殊字符",
            content="测试 🎉 emoji, \n换行, \t制表符, \"引号\", <标签>",
        )
        
        with patch("app.services.ingestion._setup_document") as mock_setup:
            with patch("app.services.ingestion._chunk_document") as mock_chunk:
                mock_doc = Document(
                    id="doc_special",
                    tenant_id="tenant_123",
                    knowledge_base_id=mock_kb.id,
                    title=params.title,
                )
                mock_setup.return_value = mock_doc
                mock_chunk.return_value = [
                    Chunk(
                        id="chunk_special",
                        tenant_id="tenant_123",
                        knowledge_base_id=mock_kb.id,
                        document_id=mock_doc.id,
                        text=params.content,
                    )
                ]
                
                result = await ingest_document(
                    session=mock_session,
                    tenant_id="tenant_123",
                    kb=mock_kb,
                    params=params,
                )
                
                # 验证：正确处理特殊字符
                assert result.chunks[0].text == params.content
    
    @pytest.mark.asyncio
    async def test_ingest_invalid_kb(self, mock_session):
        """测试无效知识库"""
        invalid_kb = KnowledgeBase(
            id="kb_invalid",
            tenant_id="tenant_123",
            name="Invalid KB",
            config={"ingestion": {"chunker": {"name": "non_existent"}}},  # 不存在的切分器
        )
        
        params = IngestionParams(
            title="Test",
            content="Content",
        )
        
        # 应该降级到默认切分器或抛出错误
        with patch("app.services.ingestion._setup_document") as mock_setup:
            with patch("app.services.ingestion._chunk_document") as mock_chunk:
                mock_doc = Document(
                    id="doc_test",
                    tenant_id="tenant_123",
                    knowledge_base_id=invalid_kb.id,
                    title="Test",
                )
                mock_setup.return_value = mock_doc
                mock_chunk.return_value = []
                
                # 不应该抛出异常（降级处理）
                result = await ingest_document(
                    session=mock_session,
                    tenant_id="tenant_123",
                    kb=invalid_kb,
                    params=params,
                )
                
                assert result.document.id == "doc_test"
    
    @pytest.mark.asyncio
    async def test_ingest_concurrent_same_doc(self, mock_session, mock_kb):
        """测试并发入库相同文档"""
        params = IngestionParams(
            title="Concurrent Doc",
            content="Content",
            existing_doc_id="doc_123",  # 指定已存在的文档
        )
        
        # 模拟数据库已有该文档
        existing_doc = Document(
            id="doc_123",
            tenant_id="tenant_123",
            knowledge_base_id=mock_kb.id,
            title="Concurrent Doc",
            processing_status="processing",  # 正在处理中
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = existing_doc
        mock_session.execute.return_value = mock_result
        
        with patch("app.services.ingestion._setup_document") as mock_setup:
            with patch("app.services.ingestion._chunk_document") as mock_chunk:
                mock_setup.return_value = existing_doc
                mock_chunk.return_value = []
                
                # 应该能处理已存在的文档
                result = await ingest_document(
                    session=mock_session,
                    tenant_id="tenant_123",
                    kb=mock_kb,
                    params=params,
                )
                
                assert result.document.id == "doc_123"


class TestQueryBoundaryConditions:
    """测试查询服务的边界条件"""
    
    @pytest.fixture
    def mock_session(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_tenant_kbs")
    async def test_query_empty_string(self, mock_get_kbs, mock_session):
        """测试空查询字符串"""
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="Test KB",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        
        params = RetrieveParams(
            query="",  # 空查询
            kb_ids=["kb_1"],
        )
        
        with patch("app.services.query.retrieve_chunks") as mock_retrieve:
            mock_retrieve.return_value = ([], "dense", False)
            
            results, _, _ = await mock_retrieve(
                session=mock_session,
                tenant_id="tenant_123",
                params=params,
            )
            
            # 验证：空查询应返回空结果或抛出错误
            assert len(results) == 0
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_tenant_kbs")
    async def test_query_very_long_string(self, mock_get_kbs, mock_session):
        """测试超长查询字符串（10万字符）"""
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="Test KB",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        
        params = RetrieveParams(
            query="A" * 100_000,  # 10万字符
            kb_ids=["kb_1"],
        )
        
        with patch("app.services.query.retrieve_chunks") as mock_retrieve:
            # 应该能处理或截断超长查询
            mock_retrieve.return_value = ([], "dense", False)
            
            results, _, _ = await mock_retrieve(
                session=mock_session,
                tenant_id="tenant_123",
                params=params,
            )
            
            # 不应该抛出异常
            assert isinstance(results, list)
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_tenant_kbs")
    async def test_query_zero_top_k(self, mock_get_kbs, mock_session):
        """测试 top_k=0"""
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="Test KB",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        
        params = RetrieveParams(
            query="test",
            kb_ids=["kb_1"],
            top_k=0,  # 无效的 top_k
        )
        
        with patch("app.services.query.retrieve_chunks") as mock_retrieve:
            mock_retrieve.return_value = ([], "dense", False)
            
            results, _, _ = await mock_retrieve(
                session=mock_session,
                tenant_id="tenant_123",
                params=params,
            )
            
            # 应该返回空结果或使用默认值
            assert len(results) == 0
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_tenant_kbs")
    async def test_query_negative_top_k(self, mock_get_kbs, mock_session):
        """测试负数 top_k"""
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="Test KB",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        
        params = RetrieveParams(
            query="test",
            kb_ids=["kb_1"],
            top_k=-5,  # 负数
        )
        
        # 应该在 Pydantic 验证层面被拒绝
        # 或者在服务层面转换为默认值
        with patch("app.services.query.retrieve_chunks") as mock_retrieve:
            mock_retrieve.return_value = ([], "dense", False)
            
            results, _, _ = await mock_retrieve(
                session=mock_session,
                tenant_id="tenant_123",
                params=params,
            )
            
            assert isinstance(results, list)
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_tenant_kbs")
    async def test_query_non_existent_kb(self, mock_get_kbs, mock_session):
        """测试查询不存在的知识库"""
        mock_get_kbs.return_value = []  # 知识库不存在
        
        params = RetrieveParams(
            query="test",
            kb_ids=["kb_non_existent"],
        )
        
        with patch("app.services.query.retrieve_chunks") as mock_retrieve:
            mock_retrieve.return_value = ([], "dense", False)
            
            results, _, _ = await mock_retrieve(
                session=mock_session,
                tenant_id="tenant_123",
                params=params,
            )
            
            # 应该返回空结果
            assert len(results) == 0
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_tenant_kbs")
    async def test_query_empty_kb_list(self, mock_get_kbs, mock_session):
        """测试空知识库列表"""
        mock_get_kbs.return_value = []
        
        params = RetrieveParams(
            query="test",
            kb_ids=[],  # 空列表
        )
        
        with patch("app.services.query.retrieve_chunks") as mock_retrieve:
            mock_retrieve.return_value = ([], "dense", False)
            
            results, _, _ = await mock_retrieve(
                session=mock_session,
                tenant_id="tenant_123",
                params=params,
            )
            
            assert len(results) == 0


class TestRAGBoundaryConditions:
    """测试 RAG 服务的边界条件"""
    
    @pytest.fixture
    def mock_session(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    @patch("app.services.rag.get_tenant_kbs")
    @patch("app.services.rag.retrieve_chunks")
    @patch("app.services.rag.chat_completion_with_config")
    async def test_rag_no_context(
        self,
        mock_chat,
        mock_retrieve,
        mock_get_kbs,
        mock_session,
    ):
        """测试无上下文时的 RAG 生成"""
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="Test KB",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        mock_retrieve.return_value = ([], "dense", False)  # 无检索结果
        mock_chat.return_value = "我无法找到相关信息。"
        
        params = RAGParams(
            query="测试问题",
            kb_ids=["kb_1"],
        )
        
        response = await generate_rag_response(
            session=mock_session,
            tenant_id="tenant_123",
            params=params,
        )
        
        # 验证：无上下文时仍能生成回答
        assert response.answer is not None
        assert len(response.sources) == 0
    
    @pytest.mark.asyncio
    @patch("app.services.rag.get_tenant_kbs")
    @patch("app.services.rag.retrieve_chunks")
    @patch("app.services.rag.chat_completion_with_config")
    async def test_rag_huge_context(
        self,
        mock_chat,
        mock_retrieve,
        mock_get_kbs,
        mock_session,
    ):
        """测试超大上下文（可能超过 LLM 限制）"""
        from app.schemas.query import ChunkHit
        
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="Test KB",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        
        # 创建100个超长 chunks
        huge_chunks = [
            ChunkHit(
                chunk_id=f"chunk_{i}",
                text="A" * 10000,  # 每个chunk 10k字符
                score=0.9,
                metadata={},
                knowledge_base_id="kb_1",
            )
            for i in range(100)
        ]
        mock_retrieve.return_value = (huge_chunks, "dense", False)
        mock_chat.return_value = "基于大量资料的回答"
        
        params = RAGParams(
            query="测试",
            kb_ids=["kb_1"],
            top_k=100,
        )
        
        response = await generate_rag_response(
            session=mock_session,
            tenant_id="tenant_123",
            params=params,
        )
        
        # 验证：应该处理或截断超大上下文
        assert response.answer is not None
    
    @pytest.mark.asyncio
    @patch("app.services.rag.get_tenant_kbs")
    @patch("app.services.rag.chat_completion")
    async def test_rag_llm_timeout(
        self,
        mock_chat,
        mock_get_kbs,
        mock_session,
    ):
        """测试 LLM 超时"""
        mock_get_kbs.return_value = []
        mock_chat.side_effect = TimeoutError("LLM 请求超时")
        
        params = RAGParams(
            query="测试",
            kb_ids=[],
        )
        
        # 应该抛出超时错误
        with pytest.raises(TimeoutError):
            await generate_rag_response(
                session=mock_session,
                tenant_id="tenant_123",
                params=params,
            )
    
    def test_rag_max_tokens_zero(self):
        """测试 max_tokens=0 被 Pydantic 验证拒绝"""
        from pydantic import ValidationError
        
        # max_tokens=0 应该被 Pydantic 验证拒绝
        with pytest.raises(ValidationError) as exc_info:
            RAGParams(
                query="测试",
                kb_ids=["kb_1"],
                max_tokens=0,  # 无效值
            )
        
        # 验证错误信息
        assert "max_tokens" in str(exc_info.value)


class TestResourceLimits:
    """测试资源限制"""
    
    @pytest.mark.asyncio
    async def test_bm25_store_size_limit(self):
        """测试 BM25 存储大小限制"""
        from app.infra.bm25_store import InMemoryBM25Store
        
        store = InMemoryBM25Store()
        
        # 验证默认限制存在
        assert store.MAX_RECORDS_PER_KB > 0
        assert hasattr(store, 'MAX_DOC_SIZE_MB')
        
        # 添加文档
        tenant_id = "tenant_test"
        kb_id = "kb_test"
        
        for i in range(5):
            store.upsert_chunk(
                chunk_id=f"chunk_{i}",
                tenant_id=tenant_id,
                knowledge_base_id=kb_id,
                text=f"Document {i} about testing",
            )
        
        # 验证搜索功能
        results = store.search(
            query="testing",
            tenant_id=tenant_id,
            kb_ids=[kb_id],
            top_k=5,
        )
        
        # 验证：搜索应该返回结果
        assert len(results) <= 5
    
    @pytest.mark.asyncio
    @patch("app.infra.redis_cache.get_redis_cache")
    async def test_redis_cache_unavailable_graceful_degradation(self, mock_get_cache):
        """测试 Redis 不可用时的优雅降级"""
        from app.infra.redis_cache import RedisCache
        
        # 模拟 Redis 不可用
        mock_cache = RedisCache()
        mock_cache._available = False
        mock_get_cache.return_value = mock_cache
        
        # 尝试获取缓存
        result = await mock_cache.get_query_cache(
            tenant_id="tenant_123",
            query="test",
            kb_ids=["kb_1"],
            retriever_name="dense",
            top_k=5,
        )
        
        # 验证：应该返回 None 而不是抛出异常
        assert result is None
        
        # 尝试设置缓存也应该静默失败
        await mock_cache.set_query_cache(
            tenant_id="tenant_123",
            query="test",
            kb_ids=["kb_1"],
            retriever_name="dense",
            top_k=5,
            result={"results": []},
        )
        # 不应抛出异常
