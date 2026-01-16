"""
知识库服务 Python SDK

提供 Python 客户端，方便调用知识库服务 API。

使用示例：
    from sdk import KBServiceClient
    
    with KBServiceClient(api_key="kb_sk_xxx") as client:
        # 创建知识库
        kb = client.knowledge_bases.create("测试知识库")
        
        # 上传文档
        doc = client.documents.create(
            kb_id=kb["id"],
            title="文档标题",
            content="文档内容..."
        )
        
        # 检索
        results = client.retrieve(
            query="查询问题",
            knowledge_base_ids=[kb["id"]]
        )
        
        # RAG 生成
        answer = client.rag(
            query="查询问题",
            knowledge_base_ids=[kb["id"]]
        )
"""

from sdk.client import (
    KBServiceClient,
    ConversationAPI,
    RaptorAPI,
    ModelProviderAPI,
)
from sdk.kb_client import KBClient  # 保留旧版兼容

__all__ = [
    "KBServiceClient",
    "KBClient",
    "ConversationAPI",
    "RaptorAPI",
    "ModelProviderAPI",
]
