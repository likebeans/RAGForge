"""
查询服务单元测试

测试 app/services/query.py 的核心功能：
- 检索功能
- 多种检索器
- ACL 权限过滤
- 缓存功能
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.query import (
    retrieve_chunks,
    get_tenant_kbs,
    _resolve_retriever,
)
from app.models import KnowledgeBase
from app.schemas.internal import RetrieveParams
from app.services.acl import UserContext


class TestGetTenantKbs:
    """测试知识库获取功能"""
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_redis_cache")
    async def test_get_tenant_kbs_from_db(self, mock_redis_cache):
        """测试从数据库获取知识库"""
        # 配置 mock
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_kb_config_cache.return_value = None
        mock_redis_cache.return_value = mock_cache_instance
        
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_kb = KnowledgeBase(
            id="kb_123",
            tenant_id="tenant_123",
            name="测试知识库",
            config={"ingestion": {"chunker": {"name": "simple"}}},
        )
        mock_result.scalars.return_value.all.return_value = [mock_kb]
        mock_session.execute.return_value = mock_result
        
        # 执行查询
        kbs = await get_tenant_kbs(
            session=mock_session,
            tenant_id="tenant_123",
            kb_ids=["kb_123"],
        )
        
        # 验证结果
        assert len(kbs) == 1
        assert kbs[0].id == "kb_123"
        
        # 验证数据库查询被调用
        mock_session.execute.assert_called_once()
        # 验证缓存设置被调用
        mock_cache_instance.set_kb_config_cache.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_redis_cache")
    async def test_get_tenant_kbs_from_cache(self, mock_redis_cache):
        """测试从缓存获取知识库"""
        # 配置 mock 返回缓存数据
        mock_cache_instance = AsyncMock()
        cached_config = {
            "id": "kb_123",
            "tenant_id": "tenant_123",
            "name": "测试知识库",
            "config": {"ingestion": {"chunker": {"name": "simple"}}},
        }
        mock_cache_instance.get_kb_config_cache.return_value = cached_config
        mock_redis_cache.return_value = mock_cache_instance
        
        mock_session = AsyncMock(spec=AsyncSession)
        
        # 执行查询
        kbs = await get_tenant_kbs(
            session=mock_session,
            tenant_id="tenant_123",
            kb_ids=["kb_123"],
        )
        
        # 验证结果
        assert len(kbs) == 1
        assert kbs[0].id == "kb_123"
        assert kbs[0].name == "测试知识库"
        
        # 验证数据库查询未被调用
        mock_session.execute.assert_not_called()


class TestResolveRetriever:
    """测试检索器解析功能"""
    
    def test_resolve_retriever_default(self):
        """测试默认检索器（dense）"""
        kbs = [
            KnowledgeBase(
                id="kb_123",
                tenant_id="tenant_123",
                name="测试知识库",
                config={},
            )
        ]
        
        retriever, name = _resolve_retriever(kbs)
        
        # 验证返回 dense 检索器
        assert name == "dense"
        assert retriever is not None
    
    def test_resolve_retriever_override(self):
        """测试检索器覆盖配置"""
        kbs = [
            KnowledgeBase(
                id="kb_123",
                tenant_id="tenant_123",
                name="测试知识库",
                config={},
            )
        ]
        
        override = {"name": "hybrid", "params": {}}
        retriever, name = _resolve_retriever(kbs, override=override)
        
        # 验证返回 hybrid 检索器
        assert name == "hybrid"
        assert retriever is not None
    
    def test_resolve_retriever_from_kb_config(self):
        """测试从知识库配置读取检索器"""
        kbs = [
            KnowledgeBase(
                id="kb_123",
                tenant_id="tenant_123",
                name="测试知识库",
                config={
                    "retrieval": {
                        "retriever": {"name": "fusion", "params": {}}
                    }
                },
            )
        ]
        
        retriever, name = _resolve_retriever(kbs)
        
        # 验证返回 fusion 检索器
        assert name == "fusion"
        assert retriever is not None


class TestRetrieveChunks:
    """测试检索功能"""
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_redis_cache")
    @patch("app.services.query._resolve_retriever")
    async def test_retrieve_chunks_with_cache(self, mock_resolve_retriever, mock_redis_cache):
        """测试缓存命中的情况"""
        # 配置 mock
        mock_cache_instance = AsyncMock()
        cached_result = {
            "results": [
                {
                    "chunk_id": "chunk_1",
                    "text": "缓存的内容",
                    "score": 0.95,
                    "metadata": {},
                    "knowledge_base_id": "kb_123",
                    "document_id": "doc_123",
                }
            ],
            "retriever_name": "dense",
        }
        mock_cache_instance.get_query_cache.return_value = cached_result
        mock_redis_cache.return_value = mock_cache_instance
        
        mock_retriever = AsyncMock()
        mock_resolve_retriever.return_value = (mock_retriever, "dense")
        
        # 执行检索
        kbs = [
            KnowledgeBase(
                id="kb_123",
                tenant_id="tenant_123",
                name="测试知识库",
                config={},
            )
        ]
        
        params = RetrieveParams(
            query="测试查询",
            top_k=5,
        )
        
        results, retriever_name, acl_blocked = await retrieve_chunks(
            tenant_id="tenant_123",
            kbs=kbs,
            params=params,
            session=None,
            user_context=None,
        )
        
        # 验证缓存命中，未执行实际检索
        assert len(results) == 1
        assert results[0].chunk_id == "chunk_1"
        assert results[0].text == "缓存的内容"
        mock_retriever.retrieve.assert_not_called()
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_redis_cache")
    @patch("app.services.query._resolve_retriever")
    @patch("app.services.query.metrics_collector")
    @patch("app.services.query.set_acl_filter_ctx")
    @patch("app.services.query.reset_acl_filter_ctx")
    async def test_retrieve_chunks_without_cache(
        self,
        mock_reset_ctx,
        mock_set_ctx,
        mock_metrics,
        mock_resolve_retriever,
        mock_redis_cache,
    ):
        """测试缓存未命中，执行实际检索"""
        # 配置 mock
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_query_cache.return_value = None
        mock_redis_cache.return_value = mock_cache_instance
        
        mock_retriever = AsyncMock()
        mock_retriever.retrieve.return_value = [
            {
                "chunk_id": "chunk_1",
                "text": "检索到的内容",
                "score": 0.90,
                "metadata": {},
                "knowledge_base_id": "kb_123",
                "document_id": "doc_123",
            }
        ]
        mock_resolve_retriever.return_value = (mock_retriever, "dense")
        mock_set_ctx.return_value = "token"
        
        # 执行检索
        kbs = [
            KnowledgeBase(
                id="kb_123",
                tenant_id="tenant_123",
                name="测试知识库",
                config={},
            )
        ]
        
        params = RetrieveParams(
            query="测试查询",
            top_k=5,
        )
        
        results, retriever_name, acl_blocked = await retrieve_chunks(
            tenant_id="tenant_123",
            kbs=kbs,
            params=params,
            session=None,
            user_context=None,
        )
        
        # 验证执行了实际检索
        assert len(results) == 1
        assert results[0].chunk_id == "chunk_1"
        assert results[0].text == "检索到的内容"
        mock_retriever.retrieve.assert_called_once()
        
        # 验证结果被缓存
        mock_cache_instance.set_query_cache.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_redis_cache")
    @patch("app.services.query._resolve_retriever")
    @patch("app.services.query.filter_results_by_acl")
    @patch("app.services.query.metrics_collector")
    @patch("app.services.query.set_acl_filter_ctx")
    @patch("app.services.query.reset_acl_filter_ctx")
    async def test_retrieve_chunks_with_acl_filter(
        self,
        mock_reset_ctx,
        mock_set_ctx,
        mock_metrics,
        mock_filter_acl,
        mock_resolve_retriever,
        mock_redis_cache,
    ):
        """测试 ACL 权限过滤"""
        # 配置 mock
        mock_cache_instance = AsyncMock()
        mock_redis_cache.return_value = mock_cache_instance
        
        mock_retriever = AsyncMock()
        mock_retriever.retrieve.return_value = [
            {
                "chunk_id": "chunk_1",
                "text": "内部文档",
                "score": 0.95,
                "metadata": {"sensitivity_level": "internal"},
                "knowledge_base_id": "kb_123",
                "document_id": "doc_123",
            },
            {
                "chunk_id": "chunk_2",
                "text": "机密文档",
                "score": 0.90,
                "metadata": {"sensitivity_level": "confidential"},
                "knowledge_base_id": "kb_123",
                "document_id": "doc_456",
            },
        ]
        mock_resolve_retriever.return_value = (mock_retriever, "dense")
        mock_set_ctx.return_value = "token"
        
        # ACL 过滤只保留第一个结果
        mock_filter_acl.return_value = [mock_retriever.retrieve.return_value[0]]
        
        # 执行检索
        kbs = [
            KnowledgeBase(
                id="kb_123",
                tenant_id="tenant_123",
                name="测试知识库",
                config={},
            )
        ]
        
        params = RetrieveParams(
            query="测试查询",
            top_k=5,
        )
        
        user_context = UserContext(
            user_id="user_123",
            roles=["viewer"],
            groups=[],
        )
        
        results, retriever_name, acl_blocked = await retrieve_chunks(
            tenant_id="tenant_123",
            kbs=kbs,
            params=params,
            session=None,
            user_context=user_context,
        )
        
        # 验证 ACL 过滤被应用
        assert len(results) == 1
        assert results[0].chunk_id == "chunk_1"
        mock_filter_acl.assert_called_once()
        
        # 验证有 ACL 过滤时不使用缓存
        mock_cache_instance.get_query_cache.assert_not_called()
        mock_cache_instance.set_query_cache.assert_not_called()
    
    @pytest.mark.asyncio
    @patch("app.services.query.get_redis_cache")
    @patch("app.services.query._resolve_retriever")
    @patch("app.services.query.metrics_collector")
    @patch("app.services.query.set_acl_filter_ctx")
    @patch("app.services.query.reset_acl_filter_ctx")
    async def test_retrieve_chunks_with_score_threshold(
        self,
        mock_reset_ctx,
        mock_set_ctx,
        mock_metrics,
        mock_resolve_retriever,
        mock_redis_cache,
    ):
        """测试分数阈值过滤"""
        # 配置 mock
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get_query_cache.return_value = None
        mock_redis_cache.return_value = mock_cache_instance
        
        mock_retriever = AsyncMock()
        mock_retriever.retrieve.return_value = [
            {
                "chunk_id": "chunk_1",
                "text": "高分内容",
                "score": 0.95,
                "metadata": {},
                "knowledge_base_id": "kb_123",
                "document_id": "doc_123",
            },
            {
                "chunk_id": "chunk_2",
                "text": "低分内容",
                "score": 0.60,
                "metadata": {},
                "knowledge_base_id": "kb_123",
                "document_id": "doc_456",
            },
        ]
        mock_resolve_retriever.return_value = (mock_retriever, "dense")
        mock_set_ctx.return_value = "token"
        
        # 执行检索（设置分数阈值 0.8）
        kbs = [
            KnowledgeBase(
                id="kb_123",
                tenant_id="tenant_123",
                name="测试知识库",
                config={},
            )
        ]
        
        params = RetrieveParams(
            query="测试查询",
            top_k=5,
            score_threshold=0.8,
        )
        
        results, retriever_name, acl_blocked = await retrieve_chunks(
            tenant_id="tenant_123",
            kbs=kbs,
            params=params,
            session=None,
            user_context=None,
        )
        
        # 验证低分结果被过滤
        assert len(results) == 1
        assert results[0].chunk_id == "chunk_1"
        assert results[0].score >= 0.8
