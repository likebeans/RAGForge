"""
RAG 服务单元测试

测试 app/services/rag.py 的核心功能：
- RAG 回答生成
- 上下文构建
- LLM 调用
- 源文档处理
- 错误处理
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rag import generate_rag_response
from app.schemas.internal import RAGParams
from app.schemas.query import ChunkHit
from app.schemas.rag import RAGResponse
from app.services.acl import UserContext
from app.models import KnowledgeBase


class TestRAGService:
    """测试 RAG 服务"""
    
    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_chunks(self):
        """创建模拟的检索结果"""
        return [
            ChunkHit(
                chunk_id="chunk_1",
                text="Python 是一种高级编程语言",
                score=0.9,
                metadata={"source": "python_intro.md"},
                knowledge_base_id="kb_1",
            ),
            ChunkHit(
                chunk_id="chunk_2",
                text="Python 广泛应用于 AI、数据分析、Web 开发",
                score=0.85,
                metadata={"source": "python_uses.md"},
                knowledge_base_id="kb_1",
            ),
        ]
    
    @pytest.fixture
    def rag_params(self):
        """创建测试用的 RAG 参数"""
        return RAGParams(
            query="Python 是什么？",
            kb_ids=["kb_1"],
            top_k=5,
            retriever_name="dense",
        )
    
    @pytest.mark.asyncio
    @patch("app.services.rag.get_tenant_kbs")
    @patch("app.services.rag.retrieve_chunks")
    @patch("app.services.rag.chat_completion_with_config")
    async def test_generate_rag_response_success(
        self,
        mock_chat,
        mock_retrieve,
        mock_get_kbs,
        mock_session,
        mock_chunks,
        rag_params,
    ):
        """测试成功生成 RAG 回答"""
        # 配置 mock
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="测试知识库",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        mock_retrieve.return_value = (mock_chunks, "dense", False)
        mock_chat.return_value = "Python 是一种高级编程语言，广泛应用于多个领域。"
        
        # 执行
        response = await generate_rag_response(
            session=mock_session,
            tenant_id="tenant_123",
            params=rag_params,
        )
        
        # 验证
        assert isinstance(response, RAGResponse)
        assert "Python" in response.answer
        assert len(response.sources) == 2
        assert response.sources[0].chunk_id == "chunk_1"
        assert response.model.retriever == "dense"
        
        # 验证调用
        mock_get_kbs.assert_called_once()
        mock_retrieve.assert_called_once()
        mock_chat.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.services.rag.get_tenant_kbs")
    @patch("app.services.rag.chat_completion")
    async def test_generate_rag_response_no_kbs(
        self,
        mock_chat,
        mock_get_kbs,
        mock_session,
        rag_params,
    ):
        """测试无知识库时的降级行为"""
        # 配置 mock
        mock_get_kbs.return_value = []
        mock_chat.return_value = "我没有相关知识库信息。"
        
        # 执行
        response = await generate_rag_response(
            session=mock_session,
            tenant_id="tenant_123",
            params=rag_params,
        )
        
        # 验证
        assert isinstance(response, RAGResponse)
        assert len(response.sources) == 0
        assert response.model.retriever == "none"
        
        # 验证直接调用 LLM
        mock_chat.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.services.rag.get_tenant_kbs")
    @patch("app.services.rag.retrieve_chunks")
    @patch("app.services.rag.chat_completion_with_config")
    async def test_generate_rag_response_no_chunks(
        self,
        mock_chat,
        mock_retrieve,
        mock_get_kbs,
        mock_session,
        rag_params,
    ):
        """测试检索无结果时的行为"""
        # 配置 mock
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="测试知识库",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        mock_retrieve.return_value = ([], "dense", False)
        mock_chat.return_value = "抱歉，我在知识库中未找到相关信息。"
        
        # 执行
        response = await generate_rag_response(
            session=mock_session,
            tenant_id="tenant_123",
            params=rag_params,
        )
        
        # 验证
        assert isinstance(response, RAGResponse)
        assert len(response.sources) == 0
        assert "未找到" in response.answer or "抱歉" in response.answer
    
    @pytest.mark.asyncio
    @patch("app.services.rag.get_tenant_kbs")
    @patch("app.services.rag.retrieve_chunks")
    @patch("app.services.rag.chat_completion_with_config")
    async def test_generate_rag_response_with_acl(
        self,
        mock_chat,
        mock_retrieve,
        mock_get_kbs,
        mock_session,
        mock_chunks,
        rag_params,
    ):
        """测试带 ACL 过滤的 RAG 生成"""
        # 配置 mock
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="测试知识库",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        mock_retrieve.return_value = (mock_chunks, "dense", True)  # acl_blocked=True
        mock_chat.return_value = "根据可访问的资料，Python 是一种编程语言。"
        
        # 创建用户上下文
        user_ctx = UserContext(
            user_id="user_123",
            roles=["developer"],
        )
        
        # 执行
        response = await generate_rag_response(
            session=mock_session,
            tenant_id="tenant_123",
            params=rag_params,
            user_context=user_ctx,
        )
        
        # 验证
        assert isinstance(response, RAGResponse)
        assert len(response.sources) > 0
        
        # 验证 ACL 上下文被传递
        retrieve_call_kwargs = mock_retrieve.call_args.kwargs
        assert retrieve_call_kwargs["user_context"] == user_ctx
    
    @pytest.mark.asyncio
    @patch("app.services.rag.get_tenant_kbs")
    @patch("app.services.rag.retrieve_chunks")
    async def test_generate_rag_response_llm_error(
        self,
        mock_retrieve,
        mock_get_kbs,
        mock_session,
        mock_chunks,
        rag_params,
    ):
        """测试 LLM 调用失败时的错误处理"""
        # 配置 mock
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="测试知识库",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        mock_retrieve.return_value = (mock_chunks, "dense", False)
        
        # LLM 抛出异常
        with patch("app.services.rag.chat_completion_with_config") as mock_chat:
            mock_chat.side_effect = Exception("LLM API 错误")
            
            # 执行应该抛出异常
            with pytest.raises(Exception) as exc_info:
                await generate_rag_response(
                    session=mock_session,
                    tenant_id="tenant_123",
                    params=rag_params,
                )
            
            assert "LLM API 错误" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch("app.services.rag.get_tenant_kbs")
    @patch("app.services.rag.retrieve_chunks")
    @patch("app.services.rag.chat_completion_with_config")
    async def test_generate_rag_response_custom_llm(
        self,
        mock_chat,
        mock_retrieve,
        mock_get_kbs,
        mock_session,
        mock_chunks,
    ):
        """测试使用自定义 LLM 配置"""
        # 配置 mock
        mock_kb = KnowledgeBase(
            id="kb_1",
            tenant_id="tenant_123",
            name="测试知识库",
            config={},
        )
        mock_get_kbs.return_value = [mock_kb]
        mock_retrieve.return_value = (mock_chunks, "dense", False)
        mock_chat.return_value = "自定义模型的回答"
        
        # 自定义 LLM 配置
        custom_llm = {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "sk-test",
        }
        
        params = RAGParams(
            query="测试",
            kb_ids=["kb_1"],
            llm_override=custom_llm,
        )
        
        # 执行
        response = await generate_rag_response(
            session=mock_session,
            tenant_id="tenant_123",
            params=params,
        )
        
        # 验证
        assert response.model.llm_provider == "openai"
        assert response.model.llm_model == "gpt-4"
        
        # 验证使用了自定义配置
        call_kwargs = mock_chat.call_args.kwargs
        assert call_kwargs["config"]["provider"] == "openai"
        assert call_kwargs["config"]["model"] == "gpt-4"
