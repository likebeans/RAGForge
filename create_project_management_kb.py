#!/usr/bin/env python3
"""创建项目管理知识库"""
import asyncio
import httpx
import json

async def create_project_management_kb():
    """创建项目管理知识库"""
    
    # API端点
    base_url = "http://localhost:8000"
    api_endpoint = f"{base_url}/api/knowledge-bases"
    
    # 知识库配置
    kb_config = {
        "name": "项目管理知识库",
        "description": "涵盖项目管理方法论、最佳实践、工具模板、敏捷开发、风险管理等内容的综合知识库，支持MinerU PDF解析和Markdown智能分块",
        "config": {
            "ingestion": {
                "chunker": {
                    "name": "markdown", 
                    "params": {
                        "chunk_size": 1024,
                        "chunk_overlap": 200,
                        "strip_headers": False
                    }
                },
                "generate_summary": True,
                "enrich_chunks": False
            },
            "query": {
                "retriever": {
                    "name": "hybrid",
                    "params": {
                        "weights": [0.7, 0.3]
                    }
                },
                "top_k": 10
            },
            "embedding": {
                "provider": "openai", 
                "model": "text-embedding-3-small"
            }
        }
    }
    
    try:
        print("🚀 正在创建项目管理知识库...")
        print(f"📡 API端点: {api_endpoint}")
        print(f"📋 配置: {json.dumps(kb_config, ensure_ascii=False, indent=2)}")
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                api_endpoint,
                json=kb_config,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\n📊 响应状态: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 知识库创建成功!")
                print(f"🆔 知识库ID: {result.get('id', 'N/A')}")
                print(f"📖 名称: {result.get('name', 'N/A')}")
                print(f"📝 描述: {result.get('description', 'N/A')}")
                
                # 保存完整响应
                with open('/home/admin1/RAGForge/project_management_kb_response.json', 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"\n💾 完整响应已保存到: project_management_kb_response.json")
                
                return result.get('id')
            else:
                print(f"❌ 创建失败: {response.status_code}")
                print(f"📄 错误信息: {response.text}")
                return None
                
    except httpx.ConnectError:
        print("❌ 无法连接到API服务，请确保RAGForge服务正在运行")
        print("💡 启动服务: uv run python main.py")
        return None
    except Exception as e:
        print(f"❌ 发生异常: {type(e).__name__}: {e}")
        return None

if __name__ == "__main__":
    kb_id = asyncio.run(create_project_management_kb())
    if kb_id:
        print(f"\n🎉 项目管理知识库创建成功! ID: {kb_id}")
    else:
        print("\n❌ 知识库创建失败")
        exit(1)