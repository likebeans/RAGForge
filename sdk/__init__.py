"""
知识库服务 Python SDK

提供 Python 客户端，方便调用知识库服务 API。

使用示例：
    from sdk import KBClient
    
    with KBClient(api_key="kb_sk_xxx") as client:
        kb = client.create_kb("测试知识库")
        client.add_document(kb["id"], "标题", "内容...")
        results = client.query("查询问题", [kb["id"]])
"""

from sdk.kb_client import KBClient

__all__ = ["KBClient"]
