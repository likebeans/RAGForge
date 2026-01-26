#!/usr/bin/env python3
"""
RAGForge API 完整测试流程

演示完整的 API 调用流程：
1. 创建租户（admin token）
2. 创建知识库（租户 API key）
3. 上传文档（租户 API key）
4. 检索测试（租户 API key）
5. RAG 生成测试（租户 API key）
"""

import asyncio
import json
import time
from typing import Dict, Any

import httpx


class RAGForgeTester:
    def __init__(self, base_url: str = "http://localhost:8020"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

        # API Keys
        self.admin_token = "ragforge-admin-2024"  # 管理员 token
        self.api_key = "kb_sk_T7dNScWSz1x_LtcXslFOqIfNIXez9sbPJlJhfhlhPW8"  # 租户 API key

        # 存储创建的资源 ID
        self.tenant_id = None
        self.kb_id = None
        self.document_ids = []

    async def make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """统一的请求方法，自动添加认证头"""
        headers = kwargs.pop("headers", {})

        # 根据 URL 自动选择认证方式
        if url.startswith("/admin"):
            headers["X-Admin-Token"] = self.admin_token
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = await self.client.request(method, f"{self.base_url}{url}", headers=headers, **kwargs)

        print(f"{method} {url} -> {response.status_code}")
        if response.status_code >= 400:
            print(f"Error: {response.text}")

        response.raise_for_status()
        return response.json() if response.content else {}

    async def test_health_check(self):
        """测试健康检查接口"""
        print("\n🔍 测试健康检查...")
        result = await self.make_request("GET", "/health")
        print(f"✅ 服务状态: {result}")
        return result

    async def test_create_tenant(self):
        """创建租户（使用 admin token）"""
        print("\n🏢 创建租户...")
        data = {
            "name": "测试公司"
        }
        result = await self.make_request("POST", "/admin/tenants", json=data)
        print(f"✅ 租户创建成功: {result}")

        self.tenant_id = result["tenant"]["id"]
        self.api_key = result["api_key"]["key"]  # 使用新创建的 API key
        print(f"📝 租户ID: {self.tenant_id}")
        print(f"🔑 API Key: {self.api_key}")
        return result

    async def test_list_tenants(self):
        """列出租户"""
        print("\n📋 列出租户...")
        result = await self.make_request("GET", "/admin/tenants")
        print(f"✅ 租户列表: {result}")
        return result

    async def test_create_knowledge_base(self):
        """创建知识库"""
        print("\n📚 创建知识库...")
        data = {
            "name": "测试知识库",
            "description": "用于演示的测试知识库"
        }
        result = await self.make_request("POST", "/v1/knowledge-bases", json=data)
        print(f"✅ 知识库创建成功: {result}")

        self.kb_id = result["id"]
        print(f"📝 知识库ID: {self.kb_id}")
        return result

    async def test_list_knowledge_bases(self):
        """列出知识库"""
        print("\n📚 列出知识库...")
        result = await self.make_request("GET", "/v1/knowledge-bases")
        print(f"✅ 知识库列表: {result}")
        return result

    async def test_upload_document(self):
        """上传文档"""
        print("\n📄 上传文档...")
        test_content = """
        人工智能的发展历程

        人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，
        致力于理解智能的本质，并创造出新的能以人类智能相似的方式做出反应的智能机器。

        人工智能的历史可以追溯到古代神话中的机械人，但现代人工智能的发展始于20世纪中叶。

        1956年，约翰·麦卡锡等人在达特茅斯会议上正式提出"人工智能"一词，这标志着人工智能学科的诞生。

        从那以后，人工智能经历了多次起伏：
        - 1950s-1960s: 推理期，研究通用问题求解和推理
        - 1970s-1980s: 知识期，专家系统和知识工程兴起
        - 1990s-2000s: 学习期，机器学习和统计方法成为主流
        - 2010s至今: 大数据和深度学习时代，神经网络取得重大突破

        近年来，随着计算能力的提升和大数据的积累，人工智能取得了前所未有的进展，
        在图像识别、自然语言处理、语音识别等领域都达到了人类水平的性能。
        """

        data = {
            "content": test_content.strip(),
            "title": "人工智能简介",
            "source": "manual"
        }

        result = await self.make_request("POST", f"/v1/knowledge-bases/{self.kb_id}/documents", json=data)
        print(f"✅ 文档上传成功: {result}")

        doc_id = result["document"]["id"]
        self.document_ids.append(doc_id)
        print(f"📝 文档ID: {doc_id}")
        return result

    async def test_list_documents(self):
        """列出文档"""
        print("\n📄 列出文档...")
        result = await self.make_request("GET", f"/v1/knowledge-bases/{self.kb_id}/documents")
        print(f"✅ 文档列表: {len(result['items'])} 个文档")
        return result

    async def test_retrieve(self):
        """测试检索接口"""
        print("\n🔍 测试检索接口...")
        data = {
            "query": "人工智能的发展历程是什么？",
            "knowledge_base_ids": [self.kb_id],
            "top_k": 3
        }

        result = await self.make_request("POST", "/v1/retrieve", json=data)
        print("✅ 检索成功"        print(f"📊 检索到 {len(result['results'])} 条结果")
        if result['results']:
            print(f"🎯 最高分结果: {result['results'][0]['text'][:100]}...")
        return result

    async def test_rag_generate(self):
        """测试 RAG 生成"""
        print("\n🤖 测试 RAG 生成...")
        data = {
            "query": "请简要介绍人工智能的发展历程",
            "knowledge_base_ids": [self.kb_id],
            "top_k": 3,
            "temperature": 0.7
        }

        result = await self.make_request("POST", "/v1/rag", json=data)
        print("✅ RAG 生成成功"        print(f"💬 回答: {result['answer'][:200]}...")
        print(f"📚 引用来源: {len(result['sources'])} 个")
        return result

    async def test_rag_stream(self):
        """测试流式 RAG"""
        print("\n🌊 测试流式 RAG...")
        data = {
            "query": "人工智能有哪些应用领域？",
            "knowledge_base_ids": [self.kb_id],
            "retriever": "dense",
            "top_k": 3
        }

        # 流式请求需要特殊处理
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with self.client.stream("POST", f"{self.base_url}/v1/rag/stream", json=data, headers=headers) as response:
            print(f"POST /v1/rag/stream -> {response.status_code}")
            if response.status_code != 200:
                print(f"Error: {response.text}")
                return

            print("📡 流式输出:")
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # 移除 "data: " 前缀
                    if data.strip():
                        try:
                            event_data = json.loads(data)
                            if "sources" in event_data:
                                print(f"📚 检索到 {len(event_data['sources'])} 个来源")
                            elif "content" in event_data:
                                print(f"💬 {event_data['content']}", end="", flush=True)
                            elif "error" in event_data:
                                print(f"❌ 错误: {event_data['error']}")
                        except json.JSONDecodeError:
                            continue
            print("\n✅ 流式 RAG 完成")

    async def test_model_configs(self):
        """测试模型配置接口"""
        print("\n⚙️ 测试模型配置...")
        result = await self.make_request("GET", "/v1/model-configs")
        print(f"✅ 模型配置: {len(result['items'])} 个配置")
        return result

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始 RAGForge API 完整测试流程")
        print("=" * 50)

        try:
            # 基础测试
            await self.test_health_check()

            # 管理员操作
            await self.test_create_tenant()
            await self.test_list_tenants()

            # 租户操作
            await self.test_create_knowledge_base()
            await self.test_list_knowledge_bases()
            await self.test_upload_document()
            await self.test_list_documents()

            # 核心功能测试
            await self.test_retrieve()
            await self.test_rag_generate()
            await self.test_rag_stream()
            await self.test_model_configs()

            print("\n🎉 所有测试完成！")

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await self.client.aclose()


async def main():
    """主函数"""
    tester = RAGForgeTester()

    # 如果已经有租户和知识库，可以直接跳过创建步骤
    use_existing = input("是否使用已存在的租户和知识库？(y/n): ").lower().strip() == 'y'

    if use_existing:
        tester.tenant_id = input("输入租户ID: ").strip()
        tester.api_key = input("输入API Key: ").strip()
        tester.kb_id = input("输入知识库ID: ").strip()

        # 直接运行核心功能测试
        await tester.test_retrieve()
        await tester.test_rag_generate()
        await tester.test_rag_stream()
    else:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
