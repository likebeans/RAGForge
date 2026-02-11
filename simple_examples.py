#!/usr/bin/env python3
"""
RAGForge API 简单使用示例

展示核心 API 接口的使用方法
"""

import json


def show_example(title, method, url, data=None, description=""):
    """显示 API 调用示例"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")
    if description:
        print(f"说明: {description}")

    print(f"方法: {method}")
    print(f"URL: http://localhost:8020{url}")

    if data:
        print("请求体:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

    # 生成 curl 命令
    headers = []
    if url.startswith("/admin"):
        headers.append('-H "X-Admin-Token: ragforge-admin-2024"')
    else:
        headers.append('-H "Authorization: Bearer kb_sk_yvmEUfH-E4R9CgNKxeo_9m2L4wzHcy8bxI3BSo0XxcQ"')

    # 构建 curl 命令（避免在 f-string 中使用反斜杠）
    curl_parts = [
        'curl -X {} "http://localhost:8020{}"'.format(method, url),
        '  -H "Content-Type: application/json"',
    ]
    curl_parts.extend("  " + h for h in headers)
    if data:
        json_data = json.dumps(data, ensure_ascii=False)
        curl_parts.append("  -d '{}'".format(json_data))
    curl_cmd = " \\\n".join(curl_parts)

    print("\n🔧 Curl 命令:")
    print(curl_cmd)
    print()


def main():
    """主函数"""
    print("🚀 RAGForge API 使用示例")
    print("=" * 60)
    print("管理员 Token: ragforge-admin-2024")
    print("API Key: kb_sk_yvmEUfH-E4R9CgNKxeo_9m2L4wzHcy8bxI3BSo0XxcQ")
    print()

    # 1. 健康检查
    show_example(
        "1. 健康检查",
        "GET",
        "/health",
        description="检查服务是否正常运行"
    )

    # 2. 管理员创建租户
    show_example(
        "2. 管理员创建租户",
        "POST",
        "/admin/tenants",
        {
            "name": "示例公司"
        },
        description="管理员创建新租户，会自动生成初始 API key"
    )

    # 3. 查看模型配置
    show_example(
        "3. 查看模型配置",
        "GET",
        "/v1/model-configs",
        description="查看当前租户的模型配置（Embedding/LLM/Rerank）"
    )

    # 4. 列出知识库
    show_example(
        "4. 列出知识库",
        "GET",
        "/v1/knowledge-bases",
        description="获取当前租户的所有知识库"
    )

    # 5. 创建知识库
    show_example(
        "5. 创建知识库",
        "POST",
        "/v1/knowledge-bases",
        {
            "name": "示例知识库",
            "description": "用于演示的知识库"
        },
        description="在当前租户下创建新的知识库"
    )

    # 6. 上传文档
    show_example(
        "6. 上传文档",
        "POST",
        "/v1/knowledge-bases/YOUR_KB_ID/documents",
        {
            "content": "人工智能（AI）是计算机科学的一个分支，致力于创造智能机器。",
            "title": "AI简介",
            "source": "manual"
        },
        description="将文档上传到指定知识库进行向量化存储（替换 YOUR_KB_ID）"
    )

    # 7. 检索接口
    show_example(
        "7. 检索接口",
        "POST",
        "/v1/retrieve",
        {
            "query": "人工智能的发展历程是什么？",
            "knowledge_base_ids": ["YOUR_KB_ID"],
            "top_k": 5
        },
        description="根据查询语句检索最相关的文档片段"
    )

    # 8. RAG 生成
    show_example(
        "8. RAG 生成",
        "POST",
        "/v1/rag",
        {
            "query": "请介绍人工智能的发展历程",
            "knowledge_base_ids": ["YOUR_KB_ID"],
            "top_k": 5,
            "temperature": 0.7
        },
        description="基于知识库内容生成回答，结合检索和 LLM 生成"
    )

    # 9. 流式 RAG
    show_example(
        "9. 流式 RAG",
        "POST",
        "/v1/rag/stream",
        {
            "query": "人工智能有哪些应用领域？",
            "knowledge_base_ids": ["YOUR_KB_ID"],
            "retriever": "dense",
            "top_k": 5
        },
        description="流式返回 RAG 生成结果，支持实时显示"
    )

    print("=" * 60)
    print("🎉 示例展示完成!")
    print("\n📝 使用说明:")
    print("1. 将 'YOUR_KB_ID' 替换为实际的知识库ID")
    print("2. 确保环境变量中配置了有效的 API keys")
    print("3. 某些接口需要知识库中有文档才能正常工作")
    print("4. 运行上述 curl 命令来测试各个接口")


if __name__ == "__main__":
    main()
