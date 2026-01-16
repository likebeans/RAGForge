"""
SDK 客户端单元测试

测试 sdk/client.py 的功能：
- KBServiceClient 基本功能
- ConversationAPI
- RaptorAPI  
- ModelProviderAPI
- rag_stream 流式 RAG
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json


class TestKBServiceClient:
    """测试 KBServiceClient 基本功能"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        from sdk.client import KBServiceClient
        
        client = KBServiceClient(
            api_key="kb_sk_test",
            base_url="http://localhost:8020",
            timeout=30.0,
        )
        
        assert client.api_key == "kb_sk_test"
        assert client.base_url == "http://localhost:8020"
        assert client.knowledge_bases is not None
        assert client.documents is not None
        assert client.api_keys is not None
        assert client.openai is not None
        assert client.conversations is not None
        assert client.raptor is not None
        assert client.model_providers is not None
        
        client.close()
    
    def test_client_context_manager(self):
        """测试上下文管理器"""
        from sdk.client import KBServiceClient
        
        with KBServiceClient(api_key="kb_sk_test") as client:
            assert client.api_key == "kb_sk_test"
        # 退出后客户端应该已关闭
    
    def test_default_base_url(self):
        """测试默认 base_url"""
        from sdk.client import KBServiceClient
        
        client = KBServiceClient(api_key="kb_sk_test")
        assert client.base_url == "http://localhost:8020"
        client.close()


class TestConversationAPI:
    """测试 ConversationAPI"""
    
    def test_conversation_api_exists(self):
        """测试 ConversationAPI 存在"""
        from sdk.client import KBServiceClient, ConversationAPI
        
        client = KBServiceClient(api_key="kb_sk_test")
        assert isinstance(client.conversations, ConversationAPI)
        client.close()
    
    def test_conversation_api_methods(self):
        """测试 ConversationAPI 方法存在"""
        from sdk.client import ConversationAPI, KBServiceClient
        
        client = KBServiceClient(api_key="kb_sk_test")
        conv_api = client.conversations
        
        # 检查所有方法存在
        assert hasattr(conv_api, 'create')
        assert hasattr(conv_api, 'list')
        assert hasattr(conv_api, 'get')
        assert hasattr(conv_api, 'update')
        assert hasattr(conv_api, 'delete')
        assert hasattr(conv_api, 'add_message')
        
        client.close()


class TestRaptorAPI:
    """测试 RaptorAPI"""
    
    def test_raptor_api_exists(self):
        """测试 RaptorAPI 存在"""
        from sdk.client import KBServiceClient, RaptorAPI
        
        client = KBServiceClient(api_key="kb_sk_test")
        assert isinstance(client.raptor, RaptorAPI)
        client.close()
    
    def test_raptor_api_methods(self):
        """测试 RaptorAPI 方法存在"""
        from sdk.client import RaptorAPI, KBServiceClient
        
        client = KBServiceClient(api_key="kb_sk_test")
        raptor_api = client.raptor
        
        # 检查所有方法存在
        assert hasattr(raptor_api, 'get_status')
        assert hasattr(raptor_api, 'build')
        assert hasattr(raptor_api, 'delete')
        
        client.close()


class TestModelProviderAPI:
    """测试 ModelProviderAPI"""
    
    def test_model_provider_api_exists(self):
        """测试 ModelProviderAPI 存在"""
        from sdk.client import KBServiceClient, ModelProviderAPI
        
        client = KBServiceClient(api_key="kb_sk_test")
        assert isinstance(client.model_providers, ModelProviderAPI)
        client.close()
    
    def test_model_provider_api_methods(self):
        """测试 ModelProviderAPI 方法存在"""
        from sdk.client import ModelProviderAPI, KBServiceClient
        
        client = KBServiceClient(api_key="kb_sk_test")
        provider_api = client.model_providers
        
        # 检查所有方法存在
        assert hasattr(provider_api, 'list')
        assert hasattr(provider_api, 'validate')
        assert hasattr(provider_api, 'get_models')
        
        client.close()


class TestRagStream:
    """测试 rag_stream 流式 RAG"""
    
    def test_rag_stream_method_exists(self):
        """测试 rag_stream 方法存在"""
        from sdk.client import KBServiceClient
        
        client = KBServiceClient(api_key="kb_sk_test")
        assert hasattr(client, 'rag_stream')
        assert callable(client.rag_stream)
        client.close()


class TestKBClient:
    """测试旧版 KBClient 兼容性"""
    
    def test_kb_client_default_port(self):
        """测试 KBClient 默认端口为 8020"""
        from sdk.kb_client import KBClient
        
        client = KBClient(api_key="kb_sk_test")
        assert client.base_url == "http://localhost:8020"
        client.close()


class TestSDKExports:
    """测试 SDK 导出"""
    
    def test_sdk_exports(self):
        """测试 SDK 导出的类"""
        from sdk import (
            KBServiceClient,
            KBClient,
            ConversationAPI,
            RaptorAPI,
            ModelProviderAPI,
        )
        
        # 确保所有类都能导入
        assert KBServiceClient is not None
        assert KBClient is not None
        assert ConversationAPI is not None
        assert RaptorAPI is not None
        assert ModelProviderAPI is not None
