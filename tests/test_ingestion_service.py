"""
文档摄取服务单元测试

测试 app/services/ingestion.py 的核心功能：
- 文档创建
- 文档切分
- 向量化和索引
- Chunk 增强
- 错误处理
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ingestion import (
    IngestionContext,
    _setup_document,
    _chunk_document,
    _enrich_chunks_step,
    _index_to_vector_stores,
    ingest_document,
    IndexingResult,
)
from app.models import Document, Chunk, KnowledgeBase
from app.schemas.internal import IngestionParams


class TestIngestionContext:
    """测试 IngestionContext 类"""
    
    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_kb(self):
        """创建模拟的知识库对象"""
        return KnowledgeBase(
            id="kb_test_123",
            tenant_id="tenant_123",
            name="测试知识库",
            config={"ingestion": {"chunker": {"name": "simple"}}},
        )
    
    @pytest.fixture
    def ingestion_params(self):
        """创建测试用的摄取参数"""
        return IngestionParams(
            title="测试文档",
            content="这是一段测试内容。" * 10,
            source="test",
            metadata={"author": "tester"},
        )
    
    def test_add_log(self, mock_session, mock_kb, ingestion_params):
        """测试日志添加功能"""
        ctx = IngestionContext(
            session=mock_session,
            tenant_id="tenant_123",
            kb=mock_kb,
            params=ingestion_params,
            embedding_config=None,
        )
        
        ctx.add_log("测试日志", level="INFO")
        assert len(ctx.log_lines) == 1
        assert "测试日志" in ctx.log_lines[0]
        assert "INFO" in ctx.log_lines[0]
    
    @pytest.mark.asyncio
    async def test_save_log_to_db(self, mock_session, mock_kb, ingestion_params):
        """测试保存日志到数据库"""
        ctx = IngestionContext(
            session=mock_session,
            tenant_id="tenant_123",
            kb=mock_kb,
            params=ingestion_params,
            embedding_config=None,
        )
        
        # 添加文档引用
        doc = Document(id="doc_123", tenant_id="tenant_123")
        ctx.doc_ref.append(doc)
        ctx.add_log("测试日志")
        
        await ctx.save_log_to_db()
        
        # 验证 session.commit 被调用
        mock_session.commit.assert_called_once()
        assert doc.processing_log is not None


class TestSetupDocument:
    """测试文档设置功能"""
    
    @pytest.fixture
    def mock_kb(self):
        return KnowledgeBase(
            id="kb_123",
            tenant_id="tenant_123",
            name="测试知识库",
            config={
                "ingestion": {"chunker": {"name": "simple"}},
                "embedding": {"provider": "ollama", "model": "bge-m3"},
            },
        )
    
    @pytest.mark.asyncio
    async def test_setup_new_document(self, mock_kb):
        """测试创建新文档"""
        mock_session = AsyncMock(spec=AsyncSession)
        params = IngestionParams(
            title="新文档",
            content="测试内容",
            source="test",
        )
        
        ctx = IngestionContext(
            session=mock_session,
            tenant_id="tenant_123",
            kb=mock_kb,
            params=params,
            embedding_config=None,
        )
        
        doc = await _setup_document(ctx)
        
        # 验证文档被创建
        assert doc is not None
        assert doc.title == "新文档"
        assert doc.tenant_id == "tenant_123"
        assert doc.processing_status == "processing"
        
        # 验证 session 方法被调用
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called()


class TestChunkDocument:
    """测试文档切分功能"""
    
    @pytest.mark.asyncio
    async def test_chunk_document_simple(self):
        """测试简单切分"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_kb = KnowledgeBase(
            id="kb_123",
            tenant_id="tenant_123",
            name="测试知识库",
            config={"ingestion": {"chunker": {"name": "simple"}}},
        )
        
        params = IngestionParams(
            title="测试文档",
            content="第一段内容。\n\n第二段内容。\n\n第三段内容。",
            source="test",
        )
        
        ctx = IngestionContext(
            session=mock_session,
            tenant_id="tenant_123",
            kb=mock_kb,
            params=params,
            embedding_config=None,
        )
        
        doc = Document(id="doc_123", tenant_id="tenant_123")
        ctx.doc_ref.append(doc)
        
        chunks = await _chunk_document(ctx, doc)
        
        # 验证切分结果
        assert len(chunks) >= 1  # 至少生成一个 chunk
        for chunk in chunks:
            assert chunk.tenant_id == "tenant_123"
            assert chunk.document_id == "doc_123"
            assert chunk.indexing_status == "pending"
            assert "chunk_index" in chunk.extra_metadata
            assert "total_chunks" in chunk.extra_metadata


class TestIndexToVectorStores:
    """测试向量库写入功能"""
    
    @pytest.mark.asyncio
    @patch("app.services.ingestion.vector_store")
    @patch("app.services.ingestion.bm25_store")
    @patch("app.services.ingestion.get_bm25_cache")
    @patch("app.services.ingestion.get_redis_cache")
    async def test_index_to_vector_stores_success(
        self,
        mock_redis_cache,
        mock_bm25_cache,
        mock_bm25_store,
        mock_vector_store,
    ):
        """测试成功写入向量库"""
        # 配置 mock
        mock_vector_store.upsert_chunks = AsyncMock()
        mock_bm25_store.upsert_chunks = AsyncMock()
        mock_bm25_cache_instance = AsyncMock()
        mock_bm25_cache.return_value = mock_bm25_cache_instance
        mock_redis_cache_instance = AsyncMock()
        mock_redis_cache.return_value = mock_redis_cache_instance
        
        # 创建测试上下文
        mock_session = AsyncMock(spec=AsyncSession)
        mock_kb = KnowledgeBase(
            id="kb_123",
            tenant_id="tenant_123",
            name="测试知识库",
            config={},
        )
        
        params = IngestionParams(
            title="测试文档",
            content="测试内容",
            source="test",
        )
        
        ctx = IngestionContext(
            session=mock_session,
            tenant_id="tenant_123",
            kb=mock_kb,
            params=params,
            embedding_config={"provider": "ollama", "model": "bge-m3"},
        )
        
        doc = Document(
            id="doc_123",
            tenant_id="tenant_123",
            title="测试文档",
            source="test",
        )
        ctx.doc_ref.append(doc)
        
        chunks = [
            Chunk(
                id="chunk_1",
                tenant_id="tenant_123",
                document_id="doc_123",
                text="测试内容 1",
                extra_metadata={},
            ),
            Chunk(
                id="chunk_2",
                tenant_id="tenant_123",
                document_id="doc_123",
                text="测试内容 2",
                extra_metadata={},
            ),
        ]
        
        # 执行写入
        results = await _index_to_vector_stores(ctx, doc, chunks)
        
        # 验证结果
        assert len(results) >= 1
        assert results[0].store_type == "qdrant"
        assert results[0].success is True
        assert results[0].chunks_count == 2
        
        # 验证向量库被调用
        mock_vector_store.upsert_chunks.assert_called_once()
        mock_bm25_store.upsert_chunks.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.services.ingestion.vector_store")
    @patch("app.services.ingestion.bm25_store")
    @patch("app.services.ingestion.get_bm25_cache")
    @patch("app.services.ingestion.get_redis_cache")
    async def test_index_to_vector_stores_failure(
        self,
        mock_redis_cache,
        mock_bm25_cache,
        mock_bm25_store,
        mock_vector_store,
    ):
        """测试向量库写入失败"""
        # 配置 mock 抛出异常
        mock_vector_store.upsert_chunks = AsyncMock(side_effect=Exception("向量库错误"))
        mock_bm25_store.upsert_chunks = AsyncMock()
        mock_bm25_cache_instance = AsyncMock()
        mock_bm25_cache.return_value = mock_bm25_cache_instance
        mock_redis_cache_instance = AsyncMock()
        mock_redis_cache.return_value = mock_redis_cache_instance
        
        # 创建测试上下文
        mock_session = AsyncMock(spec=AsyncSession)
        mock_kb = KnowledgeBase(
            id="kb_123",
            tenant_id="tenant_123",
            name="测试知识库",
            config={},
        )
        
        params = IngestionParams(
            title="测试文档",
            content="测试内容",
            source="test",
        )
        
        ctx = IngestionContext(
            session=mock_session,
            tenant_id="tenant_123",
            kb=mock_kb,
            params=params,
            embedding_config=None,
        )
        
        doc = Document(id="doc_123", tenant_id="tenant_123", title="测试文档")
        ctx.doc_ref.append(doc)
        
        chunks = [
            Chunk(
                id="chunk_1",
                tenant_id="tenant_123",
                document_id="doc_123",
                text="测试内容",
                extra_metadata={},
            ),
        ]
        
        # 执行写入
        results = await _index_to_vector_stores(ctx, doc, chunks)
        
        # 验证失败结果
        assert len(results) >= 1
        assert results[0].store_type == "qdrant"
        assert results[0].success is False
        assert "向量库错误" in results[0].error


class TestIngestDocument:
    """测试完整的文档摄取流程"""
    
    @pytest.mark.asyncio
    @patch("app.services.ingestion._setup_document")
    @patch("app.services.ingestion._chunk_document")
    @patch("app.services.ingestion._enrich_chunks_step")
    @patch("app.services.ingestion._index_to_vector_stores")
    @patch("app.services.ingestion._build_raptor_index_step")
    async def test_ingest_document_success(
        self,
        mock_raptor,
        mock_index,
        mock_enrich,
        mock_chunk,
        mock_setup,
    ):
        """测试完整摄取流程成功"""
        # 配置 mock
        mock_doc = Document(id="doc_123", tenant_id="tenant_123", title="测试文档")
        mock_setup.return_value = mock_doc
        
        mock_chunks = [
            Chunk(id="chunk_1", tenant_id="tenant_123", document_id="doc_123", text="内容 1"),
            Chunk(id="chunk_2", tenant_id="tenant_123", document_id="doc_123", text="内容 2"),
        ]
        mock_chunk.return_value = mock_chunks
        
        mock_index.return_value = [
            IndexingResult(store_type="qdrant", success=True, chunks_count=2)
        ]
        mock_raptor.return_value = None
        
        # 执行摄取
        mock_session = AsyncMock(spec=AsyncSession)
        mock_kb = KnowledgeBase(
            id="kb_123",
            tenant_id="tenant_123",
            name="测试知识库",
            config={},
        )
        
        params = IngestionParams(
            title="测试文档",
            content="测试内容",
            source="test",
        )
        
        result = await ingest_document(
            session=mock_session,
            tenant_id="tenant_123",
            kb=mock_kb,
            params=params,
        )
        
        # 验证结果
        assert result.document == mock_doc
        assert len(result.chunks) == 2
        assert len(result.indexing_results) == 1
        assert result.all_success is True
        assert result.primary_success is True
        
        # 验证各步骤被调用
        mock_setup.assert_called_once()
        mock_chunk.assert_called_once()
        mock_index.assert_called_once()
