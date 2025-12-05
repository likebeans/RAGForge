"""简单的 SDK 测试"""
import sys
sys.path.insert(0, '/home/admin1/work/self_rag_pipeline')

from sdk import KBServiceClient

API_KEY = "kb_sk_zeELI2nytTxS2O56L3RyghJrAUnRorNFfnsNaj-5DS8"
API_BASE = "http://localhost:8020"

print("测试 SDK...")
try:
    with KBServiceClient(api_key=API_KEY, base_url=API_BASE) as client:
        print(f"客户端创建成功")
        print(f"Base URL: {client.base_url}")
        print(f"API Key: {client.api_key[:20]}...")
        
        # 测试创建知识库
        print("\n创建知识库...")
        kb = client.knowledge_bases.create(
            name="简单测试",
            description="测试描述"
        )
        print(f"✓ 知识库创建成功: {kb['id']}")
        print(f"  名称: {kb['name']}")
        
        # 清理
        client.knowledge_bases.delete(kb['id'])
        print(f"✓ 知识库已删除")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
