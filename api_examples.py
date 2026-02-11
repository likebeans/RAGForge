#!/usr/bin/env python3
"""
RAGForge API 使用示例

展示各个 API 接口的调用方法和参数格式。
这些示例可以在配置了有效 API key 的环境中正常运行。
"""

import asyncio
import httpx
import json


class RAGForgeExamples:
    """RAGForge API 调用示例"""

    def __init__(self, base_url: str = "http://localhost:8020"):
        self.base_url = base_url.rstrip("/")
        # 使用你提供的 API keys
        self.admin_token = "ragforge-admin-2024"  # 租户管理 token
        self.api_key = "kb_sk_T7dNScWSz1x_LtcXslFOqIfNIXez9sbPJlJhfhlhPW8"  # 租户 API key

    async def make_request(self, method: str, url: str, **kwargs):
        """统一的请求方法"""
        headers = kwargs.pop("headers", {})

        # 根据 URL 自动选择认证方式
        if url.startswith("/admin"):
            headers["X-Admin-Token"] = self.admin_token
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"

        headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, f"{self.base_url}{url}", headers=headers, **kwargs)
            return response

    def print_example(self, title: str, method: str, url: str, data: dict = None, description: str = ""):
        """打印 API 调用示例"""
        print(f"\n{'='*60}")
        print(f"📋 {title}")
        print(f"{'='*60}")
        if description:
            print(f"说明: {description}")
        print(f"方法: {method}")
        print(f"URL: {url}")
        if data:
            print("请求体:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

        # 生成 curl 命令
        headers = []
        if url.startswith("/admin"):
            headers.append('-H "X-Admin-Token: ragforge-admin-2024"')
        else:
            headers.append('-H "Authorization: Bearer kb_sk_T7dNScWSz1x_LtcXslFOqIfNIXez9sbPJlJhfhlhPW8"')

        # 构建 curl 命令（避免在 f-string 中使用反斜杠）
        curl_parts = [
            'curl -X {} "{}{}"'.format(method, self.base_url, url),
            '  -H "Content-Type: application/json"',
        ]
        curl_parts.extend("  " + h for h in headers)
        if data:
            json_data = json.dumps(data, ensure_ascii=False)
            curl_parts.append("  -d '{}'".format(json_data))
        curl_cmd = " \\\n".join(curl_parts)

        print("\n🔧 Curl 命令:")
        print(curl_cmd)

    async def show_health_check(self):
        """健康检查接口"""
        self.print_example(
            "健康检查",
            "GET",
            "/health",
            description="检查服务是否正常运行"
        )

        try:
            response = await self.make_request("GET", "/health")
            print(f"\n✅ 响应状态: {response.status_code}")
            if response.status_code == 200:
                print(f"响应内容: {response.json()}")
        except Exception as e:
            print(f"❌ 请求失败: {e}")

    async def show_admin_create_tenant(self):
        """管理员创建租户"""
        data = {
            "name": "示例公司"
        }

        self.print_example(
            "管理员创建租户",
            "POST",
            "/admin/tenants",
            data,
            description="管理员创建新租户，会自动生成初始 API key"
        )

        try:
            response = await self.make_request("POST", "/admin/tenants", json=data)
            print(f"\n✅ 响应状态: {response.status_code}")
            if response.status_code == 201:
                result = response.json()
                print("创建成功! 返回信息:")
                print(f"  租户ID: {result['tenant']['id']}")
                print(f"  API Key: {result['api_key']['key']}")
                print("  ⚠️  请保存 API Key，只在创建时返回一次!")
        except Exception as e:
            print(f"❌ 请求失败: {e}")

    async def show_list_knowledge_bases(self):
        """列出知识库"""
        self.print_example(
            "列出知识库",
            "GET",
            "/v1/knowledge-bases",
            description="获取当前租户的所有知识库"
        )

        try:
            response = await self.make_request("GET", "/v1/knowledge-bases")
            print(f"\n✅ 响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"知识库数量: {len(result['items'])}")
                for kb in result['items'][:3]:  # 只显示前3个
                    print(f"  - {kb['name']} (ID: {kb['id']})")
        except Exception as e:
            print(f"❌ 请求失败: {e}")

    async def show_create_knowledge_base(self):
        """创建知识库"""
        data = {
            "name": "示例知识库",
            "description": "用于演示的知识库"
        }

        self.print_example(
            "创建知识库",
            "POST",
            "/v1/knowledge-bases",
            data,
            description="在当前租户下创建新的知识库"
        )

        try:
            response = await self.make_request("POST", "/v1/knowledge-bases", json=data)
            print(f"\n✅ 响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"创建成功! 知识库ID: {result['id']}")
        except Exception as e:
            print(f"❌ 请求失败: {e}")

    async def show_upload_document(self):
        """上传文档"""
        kb_id = "your_kb_id_here"  # 需要替换为实际的知识库ID

        data = {
            "content": """
            人工智能（Artificial Intelligence）是计算机科学的一个分支，
            致力于理解智能的本质，并创造出新的能以人类智能相似的方式做出反应的智能机器。

            AI 的发展历程可以分为几个阶段：
            1. 推理期（1950s-1960s）：研究通用问题求解
            2. 知识期（1970s-1980s）：专家系统和知识工程
            3. 学习期（1990s-2000s）：机器学习和统计方法
            4. 大数据时代（2010s-至今）：深度学习取得突破

            目前 AI 已经在图像识别、自然语言处理、语音识别等领域
            达到了或超过了人类水平的性能。
            """.strip(),
            "title": "人工智能简介",
            "source": "manual"
        }

        self.print_example(
            f"上传文档到知识库 {kb_id}",
            "POST",
            f"/v1/knowledge-bases/{kb_id}/documents",
            data,
            description="将文档上传到指定知识库进行向量化存储"
        )

        try:
            response = await self.make_request("POST", f"/v1/knowledge-bases/{kb_id}/documents", json=data)
            print(f"\n✅ 响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("上传成功!")
                print(f"  文档ID: {result['document']['id']}")
                print(f"  处理状态: {result['document']['processing_status']}")
        except Exception as e:
            print(f"❌ 请求失败: {e}")

    async def show_retrieve(self):
        """检索接口"""
        kb_id = "your_kb_id_here"  # 需要替换为实际的知识库ID

        data = {
            "query": "人工智能的发展历程是什么？",
            "knowledge_base_ids": [kb_id],
            "top_k": 5,
            "score_threshold": 0.1
        }

        self.print_example(
            f"从知识库 {kb_id} 检索相关内容",
            "POST",
            "/v1/retrieve",
            data,
            description="根据查询语句检索最相关的文档片段"
        )

        try:
            response = await self.make_request("POST", "/v1/retrieve", json=data)
            print(f"\n✅ 响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("检索成功!")
                print(f"  找到结果: {len(result['results'])} 条")
                if result['results']:
                    print(f"  最高分: {result['results'][0]['score']:.3f}")
                    print(f"  内容预览: {result['results'][0]['text'][:100]}...")
            elif response.status_code == 404:
                print("  ⚠️  知识库中没有找到相关文档")
        except Exception as e:
            print(f"❌ 请求失败: {e}")

    async def show_rag_generate(self):
        """RAG 生成"""
        kb_id = "your_kb_id_here"  # 需要替换为实际的知识库ID

        data = {
            "query": "请简要介绍人工智能的发展历程",
            "knowledge_base_ids": [kb_id],
            "top_k": 5,
            "temperature": 0.7,
            "max_tokens": 500,
            "include_sources": True
        }

        self.print_example(
            f"RAG 生成回答 (基于知识库 {kb_id})",
            "POST",
            "/v1/rag",
            data,
            description="基于知识库内容生成回答，结合检索和 LLM 生成"
        )

        try:
            response = await self.make_request("POST", "/v1/rag", json=data)
            print(f"\n✅ 响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("RAG 生成成功!")
                print(f"  回答: {result['answer'][:200]}...")
                print(f"  引用来源: {len(result['sources'])} 个")
                print(f"  使用的模型: {result['model']}")
            elif response.status_code == 404:
                print("  ⚠️  知识库中没有找到相关文档")
        except Exception as e:
            print(f"❌ 请求失败: {e}")

    async def show_rag_stream(self):
        """流式 RAG 生成"""
        kb_id = "your_kb_id_here"  # 需要替换为实际的知识库ID

        data = {
            "query": "人工智能有哪些应用领域？",
            "knowledge_base_ids": [kb_id],
            "retriever": "dense",
            "top_k": 5,
            "temperature": 0.7
        }

        self.print_example(
            f"流式 RAG 生成 (基于知识库 {kb_id})",
            "POST",
            "/v1/rag/stream",
            data,
            description="流式返回 RAG 生成结果，支持实时显示"
        )

        print("\n🔧 Curl 命令 (流式):")
        print(f"""curl -X POST "{self.base_url}/v1/rag/stream" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer kb_sk_T7dNScWSz1x_LtcXslFOqIfNIXez9sbPJlJhfhlhPW8" \\
  -d '{json.dumps(data, ensure_ascii=False)}'""")

        print("\n📡 流式响应格式:")
        print("event: sources")
        print("data: [检索到的文档列表]")
        print()
        print("event: content")
        print("data: 生成的")
        print()
        print("event: content")
        print("data: 文本")
        print()
        print("event: content")
        print("data: 内容")
        print()
        print("event: done")
        print("data: ")

    async def show_model_configs(self):
        """模型配置管理"""
        self.print_example(
            "查看模型配置",
            "GET",
            "/v1/model-configs",
            description="查看当前租户的模型配置（Embedding/LLM/Rerank）"
        )

        try:
            response = await self.make_request("GET", "/v1/model-configs")
            print(f"\n✅ 响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"配置数量: {len(result['items'])}")
        except Exception as e:
            print(f"❌ 请求失败: {e}")

    async def show_admin_system_config(self):
        """管理员系统配置"""
        self.print_example(
            "管理员查看系统配置",
            "GET",
            "/admin/system-config",
            description="管理员查看系统级配置"
        )

        try:
            response = await self.make_request("GET", "/admin/system-config")
            print(f"\n✅ 响应状态: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"系统配置项: {len(result['items'])}")
        except Exception as e:
            print(f"❌ 请求失败: {e}")

    async def run_examples(self):
        """运行所有示例"""
        print("🚀 RAGForge API 使用示例")
        print("=" * 60)
        print(f"服务地址: {self.base_url}")
        print(f"管理员Token: {self.admin_token}")
        print(f"API Key: {self.api_key}")
        print()

        # 基础接口
        await self.show_health_check()
        await self.show_model_configs()

        # 管理员接口
        await self.show_admin_create_tenant()
        await self.show_admin_system_config()

        # 租户接口
        await self.show_list_knowledge_bases()
        await self.show_create_knowledge_base()

        # 核心功能（需要有知识库和文档）
        await self.show_upload_document()
        await self.show_retrieve()
        await self.show_rag_generate()
        await self.show_rag_stream()

        print(f"\n{'='*60}")
        print("🎉 示例展示完成!")
        print("\n📝 注意事项:")
        print("1. 将 'your_kb_id_here' 替换为实际的知识库ID")
        print("2. 确保环境变量中配置了有效的 API keys")
        print("3. 某些接口需要知识库中有文档才能正常工作")


async def main():
    """主函数"""
    examples = RAGForgeExamples()
    await examples.run_examples()


if __name__ == "__main__":
    asyncio.run(main())
