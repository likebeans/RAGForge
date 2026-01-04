"""
测试 OpenAI 兼容接口和 Python SDK（E2E，可选）

通过环境变量控制是否运行：
    RUN_OPENAI_E2E=1 API_KEY=xxx API_BASE=http://localhost:8020 uv run pytest -m e2e test_openai_sdk.py
"""

import os
import sys
import time

import pytest

# 跳过：默认不运行，避免 CI 依赖外部服务
if not os.getenv("RUN_OPENAI_E2E"):
    pytest.skip("RUN_OPENAI_E2E not set, skipping OpenAI e2e tests", allow_module_level=True)

# 测试环境配置（必须提供）
API_KEY = os.getenv("API_KEY")
API_BASE = os.getenv("API_BASE")
if not API_KEY or not API_BASE:
    pytest.skip("API_KEY or API_BASE not set for OpenAI e2e tests", allow_module_level=True)

# 使用时间戳确保名称唯一
TIMESTAMP = int(time.time())

print("=" * 80)
print("OpenAI 兼容接口和 SDK 测试")
print("=" * 80)

# ============================================================================
# 测试 1: OpenAI Embeddings API
# ============================================================================
print("\n【测试 1】OpenAI Embeddings API")
print("-" * 80)

try:
    import httpx
    
    # 测试单个文本
    resp = httpx.post(
        f"{API_BASE}/v1/embeddings",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "text-embedding-3-small",
            "input": "Hello, world!"
        },
        timeout=30.0
    )
    resp.raise_for_status()
    result = resp.json()
    
    print(f"✓ 单个文本 Embedding:")
    print(f"  - 模型: {result['model']}")
    print(f"  - 向量维度: {len(result['data'][0]['embedding'])}")
    print(f"  - Token 使用: {result['usage']['total_tokens']}")
    
    # 测试批量文本
    resp = httpx.post(
        f"{API_BASE}/v1/embeddings",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "text-embedding-3-small",
            "input": ["文本1", "文本2", "文本3"]
        },
        timeout=30.0
    )
    resp.raise_for_status()
    result = resp.json()
    
    print(f"✓ 批量文本 Embedding:")
    print(f"  - 文本数量: {len(result['data'])}")
    print(f"  - 向量维度: {len(result['data'][0]['embedding'])}")
    
    print("\n✅ OpenAI Embeddings API 测试通过")
    
except Exception as e:
    print(f"\n❌ OpenAI Embeddings API 测试失败: {e}")
    sys.exit(1)

# ============================================================================
# 测试 2: Python SDK - 知识库和文档管理
# ============================================================================
print("\n【测试 2】Python SDK - 知识库和文档管理")
print("-" * 80)

try:
    # 导入 SDK
    import importlib
    sys.path.insert(0, os.path.dirname(__file__))
    
    # 强制重新加载 SDK 模块
    if 'sdk' in sys.modules:
        del sys.modules['sdk']
    if 'sdk.client' in sys.modules:
        del sys.modules['sdk.client']
    
    from sdk import KBServiceClient
    
    with KBServiceClient(api_key=API_KEY, base_url=API_BASE) as client:
        # 创建知识库（使用唯一名称）
        try:
            kb = client.knowledge_bases.create(
                name=f"SDK测试知识库_{TIMESTAMP}",
                description="用于测试 SDK 功能"
            )
            kb_id = kb["id"]
            print(f"✓ 创建知识库: {kb_id}")
        except Exception as e:
            print(f"创建知识库失败: {e}")
            # 尝试获取响应内容
            if hasattr(e, 'response'):
                print(f"响应内容: {e.response.text}")
            raise
        
        # 上传文档（设置为 public 避免 ACL 问题）
        doc1 = client.documents.create(
            kb_id=kb_id,
            title="Python 简介",
            content="Python 是一种高级编程语言，由 Guido van Rossum 于 1991 年首次发布。Python 设计哲学强调代码的可读性和简洁的语法。",
            sensitivity_level="public"
        )
        print(f"✓ 上传文档1: {doc1['document_id']} ({doc1['chunk_count']} chunks)")
        
        doc2 = client.documents.create(
            kb_id=kb_id,
            title="Python 应用",
            content="Python 广泛应用于 Web 开发、数据分析、人工智能、科学计算等领域。流行的框架包括 Django、Flask、FastAPI、Pandas、NumPy 等。",
            sensitivity_level="public"
        )
        print(f"✓ 上传文档2: {doc2['document_id']} ({doc2['chunk_count']} chunks)")
        
        # 列出文档
        docs = client.documents.list(kb_id=kb_id)
        print(f"✓ 列出文档: {len(docs['items'])} 个文档")
        
        # 检索测试
        print("\n【测试 3】SDK - 检索功能")
        print("-" * 80)
        
        results = client.retrieve(
            query="Python 有什么应用",
            knowledge_base_ids=[kb_id],
            top_k=3
        )
        print(f"✓ 检索结果: {len(results['results'])} 条")
        for i, r in enumerate(results["results"], 1):
            print(f"  {i}. Score: {r['score']:.4f} | {r['text'][:50]}...")
        
        # RAG 测试
        print("\n【测试 4】SDK - RAG 生成")
        print("-" * 80)
        
        answer = client.rag(
            query="Python 有什么应用",
            knowledge_base_ids=[kb_id],
            temperature=0.7,
            max_tokens=200
        )
        print(f"✓ RAG 回答:")
        print(f"  {answer['answer'][:200]}...")
        print(f"✓ 来源数量: {len(answer['sources'])}")
        
        # OpenAI Chat Completions 测试
        print("\n【测试 5】SDK - OpenAI Chat Completions (RAG 模式)")
        print("-" * 80)
        
        response = client.openai.chat_completions(
            messages=[
                {"role": "system", "content": "你是一个技术助手"},
                {"role": "user", "content": "Python 有什么应用？"}
            ],
            model="gpt-4",
            knowledge_base_ids=[kb_id],
            temperature=0.7,
            max_tokens=200
        )
        print(f"✓ Chat Completions 响应:")
        print(f"  ID: {response['id']}")
        print(f"  模型: {response['model']}")
        print(f"  回答: {response['choices'][0]['message']['content'][:200]}...")
        if response.get('sources'):
            print(f"  来源数量: {len(response['sources'])}")
        
        # OpenAI Embeddings 测试
        print("\n【测试 6】SDK - OpenAI Embeddings")
        print("-" * 80)
        
        emb_response = client.openai.embeddings(
            input="测试文本",
            model="text-embedding-3-small"
        )
        print(f"✓ Embeddings 响应:")
        print(f"  模型: {emb_response['model']}")
        print(f"  向量维度: {len(emb_response['data'][0]['embedding'])}")
        
        # API Key 管理测试
        print("\n【测试 7】SDK - API Key 管理")
        print("-" * 80)
        
        # 创建测试 Key
        new_key = client.api_keys.create(
            name="SDK测试Key",
            role="read",
            scope_kb_ids=[kb_id]
        )
        print(f"✓ 创建 API Key: {new_key['name']} (role={new_key['role']})")
        print(f"  Key: {new_key['api_key'][:20]}...")
        
        # 列出 Keys
        keys = client.api_keys.list()
        print(f"✓ 列出 API Keys: {len(keys)} 个")
        
        # 删除测试 Key
        client.api_keys.delete(key_id=new_key['id'])
        print(f"✓ 删除 API Key: {new_key['id']}")
        
        # 清理：删除知识库
        print("\n【清理】删除测试数据")
        print("-" * 80)
        client.knowledge_bases.delete(kb_id=kb_id)
        print(f"✓ 删除知识库: {kb_id}")
    
    print("\n✅ 所有 SDK 测试通过")
    
except Exception as e:
    print(f"\n❌ SDK 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# 测试总结
# ============================================================================
print("\n" + "=" * 80)
print("测试总结")
print("=" * 80)
print("✅ OpenAI Embeddings API - 通过")
print("✅ SDK 知识库管理 - 通过")
print("✅ SDK 文档管理 - 通过")
print("✅ SDK 检索功能 - 通过")
print("✅ SDK RAG 生成 - 通过")
print("✅ SDK OpenAI Chat Completions - 通过")
print("✅ SDK OpenAI Embeddings - 通过")
print("✅ SDK API Key 管理 - 通过")
print("\n🎉 所有测试通过！")
