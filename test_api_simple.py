#!/usr/bin/env python3
"""
RAGForge API 简单测试

使用现有的 API key 进行测试，不创建新资源。
适用于已经有租户和知识库的环境。
"""

import asyncio
import json
import httpx


async def test_api_endpoints():
    """测试各个 API 端点"""

    base_url = "http://localhost:8020"
    api_key = "kb_sk_T7dNScWSz1x_LtcXslFOqIfNIXez9sbPJlJhfhlhPW8"
    admin_token = "ragforge-admin-2024"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    admin_headers = {
        "X-Admin-Token": admin_token,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:

        print("🚀 RAGForge API 测试开始")
        print("=" * 50)

        # 1. 健康检查
        print("\n1. 健康检查")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"✅ GET /health -> {response.status_code}")
            if response.status_code == 200:
                print(f"   响应: {response.json()}")
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")

        # 2. 模型配置
        print("\n2. 模型配置列表")
        try:
            response = await client.get(f"{base_url}/v1/model-configs", headers=headers)
            print(f"✅ GET /v1/model-configs -> {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   配置数量: {len(result['items'])}")
        except Exception as e:
            print(f"❌ 模型配置失败: {e}")

        # 3. 知识库列表
        print("\n3. 知识库列表")
        try:
            response = await client.get(f"{base_url}/v1/knowledge-bases", headers=headers)
            print(f"✅ GET /v1/knowledge-bases -> {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                kb_ids = [kb['id'] for kb in result['items']]
                print(f"   知识库数量: {len(result['items'])}")
                if kb_ids:
                    print(f"   知识库IDs: {kb_ids[:3]}")  # 只显示前3个
                kb_id = kb_ids[0] if kb_ids else None
            else:
                kb_id = None
        except Exception as e:
            print(f"❌ 知识库列表失败: {e}")
            kb_id = None

        # 4. 如果有知识库，测试检索
        if kb_id:
            print(f"\n4. 检索测试 (知识库: {kb_id})")
            try:
                data = {
                    "query": "测试检索功能",
                    "knowledge_base_ids": [kb_id],
                    "top_k": 3
                }
                response = await client.post(f"{base_url}/v1/retrieve", headers=headers, json=data)
                print(f"✅ POST /v1/retrieve -> {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    print(f"   检索结果: {len(result['results'])} 条")
                    if result['results']:
                        print(f"   第一个结果分数: {result['results'][0]['score']:.3f}")
                elif response.status_code == 404:
                    print("   ⚠️  知识库中没有文档")
            except Exception as e:
                print(f"❌ 检索测试失败: {e}")

            # 5. RAG 生成测试
            print(f"\n5. RAG 生成测试 (知识库: {kb_id})")
            try:
                data = {
                    "query": "请介绍一下相关内容",
                    "knowledge_base_ids": [kb_id],
                    "top_k": 3,
                    "temperature": 0.7
                }
                response = await client.post(f"{base_url}/v1/rag", headers=headers, json=data)
                print(f"✅ POST /v1/rag -> {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    print(f"   生成回答长度: {len(result['answer'])} 字符")
                    print(f"   引用来源: {len(result['sources'])} 个")
                elif response.status_code == 404:
                    print("   ⚠️  知识库中没有文档")
            except Exception as e:
                print(f"❌ RAG 生成失败: {e}")

            # 6. 流式 RAG 测试
            print(f"\n6. 流式 RAG 测试 (知识库: {kb_id})")
            try:
                data = {
                    "query": "请简要回答一个问题",
                    "knowledge_base_ids": [kb_id],
                    "retriever": "dense",
                    "top_k": 3
                }

                print("   📡 流式输出:")
                async with client.stream("POST", f"{base_url}/v1/rag/stream", json=data, headers=headers) as response:
                    if response.status_code != 200:
                        print(f"   ❌ 流式请求失败: {response.status_code}")
                        if response.content:
                            print(f"      {response.text}")
                    else:
                        content_received = False
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_content = line[6:]
                                if data_content.strip():
                                    try:
                                        event_data = json.loads(data_content)
                                        if "sources" in event_data:
                                            print(f"      📚 检索到 {len(event_data['sources'])} 个来源")
                                        elif "content" in event_data:
                                            if not content_received:
                                                print(f"      💬 ", end="", flush=True)
                                                content_received = True
                                            print(f"{event_data['content']}", end="", flush=True)
                                        elif "done" in event_data:
                                            print("...完成")
                                            break
                                        elif "error" in event_data:
                                            print(f"      ❌ 错误: {event_data['error']}")
                                            break
                                    except json.JSONDecodeError:
                                        continue

            except Exception as e:
                print(f"❌ 流式 RAG 失败: {e}")

        # 7. 管理员接口测试
        print("\n7. 管理员接口测试")
        try:
            response = await client.get(f"{base_url}/admin/system-config", headers=admin_headers)
            print(f"✅ GET /admin/system-config -> {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   系统配置: {len(result['items'])} 项")
        except Exception as e:
            print(f"❌ 管理员接口失败: {e}")

        print("\n" + "=" * 50)
        print("🎉 API 测试完成！")


async def create_sample_tenant_and_kb():
    """创建示例租户和知识库（可选）"""

    print("\n🏗️ 创建示例数据...")
    base_url = "http://localhost:8020"
    admin_token = "ragforge-admin-2024"

    admin_headers = {
        "X-Admin-Token": admin_token,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 创建租户
            print("   创建租户...")
            tenant_data = {"name": "示例公司"}
            response = await client.post(f"{base_url}/admin/tenants", headers=admin_headers, json=tenant_data)
            if response.status_code == 201:
                tenant_result = response.json()
                tenant_id = tenant_result["tenant"]["id"]
                api_key = tenant_result["api_key"]["key"]
                print(f"   ✅ 租户创建成功: {tenant_id}")
                print(f"   🔑 API Key: {api_key}")

                # 使用新创建的 API key 创建知识库
                kb_headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }

                print("   创建知识库...")
                kb_data = {
                    "name": "示例知识库",
                    "description": "用于测试的示例知识库"
                }
                response = await client.post(f"{base_url}/v1/knowledge-bases", headers=kb_headers, json=kb_data)
                if response.status_code == 200:
                    kb_result = response.json()
                    kb_id = kb_result["id"]
                    print(f"   ✅ 知识库创建成功: {kb_id}")

                    # 上传示例文档
                    print("   上传示例文档...")
                    doc_data = {
                        "content": """
                        机器学习是人工智能的一个重要分支。

                        机器学习（Machine Learning）是人工智能的核心技术之一，
                        通过算法让计算机从数据中学习规律，而无需显式编程。

                        主要类型包括：
                        1. 监督学习（Supervised Learning）
                        2. 无监督学习（Unsupervised Learning）
                        3. 强化学习（Reinforcement Learning）

                        监督学习使用标记数据进行训练，如分类和回归任务。
                        无监督学习从无标记数据中发现模式，如聚类分析。
                        强化学习通过试错学习最优策略，如游戏AI。

                        深度学习是机器学习的一个子集，使用神经网络进行特征学习。
                        """.strip(),
                        "title": "机器学习简介",
                        "source": "manual"
                    }

                    response = await client.post(f"{base_url}/v1/knowledge-bases/{kb_id}/documents",
                                               headers=kb_headers, json=doc_data)
                    if response.status_code == 200:
                        print("   ✅ 文档上传成功")
                        print("\n📝 示例数据创建完成!")
                        print(f"   租户ID: {tenant_id}")
                        print(f"   API Key: {api_key}")
                        print(f"   知识库ID: {kb_id}")
                        print("   现在可以运行主要测试了!")
                    else:
                        print(f"   ❌ 文档上传失败: {response.status_code}")
                else:
                    print(f"   ❌ 知识库创建失败: {response.status_code}")
            else:
                print(f"   ❌ 租户创建失败: {response.status_code}")
                print(f"      响应: {response.text}")

        except Exception as e:
            print(f"❌ 创建示例数据失败: {e}")


async def main():
    """主函数"""
    print("RAGForge API 测试工具")
    print("=" * 30)

    choice = input("选择测试模式:\n1. 测试现有数据\n2. 创建示例数据后测试\n请选择 (1/2): ").strip()

    if choice == "2":
        await create_sample_tenant_and_kb()

    await test_api_endpoints()


if __name__ == "__main__":
    asyncio.run(main())
