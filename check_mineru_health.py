#!/usr/bin/env python3
"""检查 MinerU 服务健康状态"""

import asyncio
import sys
from app.infra.mineru_client import MinerUClient
from app.config import get_settings

async def check_mineru_service():
    """检查 MinerU 服务状态"""
    settings = get_settings()
    print("🔍 正在检查 MinerU 服务状态...")
    print(f"服务地址: {settings.mineru_base_url}")
    print(f"启用状态: {settings.mineru_enabled}")
    print(f"超时设置: {settings.mineru_timeout}秒")
    
    if not settings.mineru_enabled:
        print("⚠️  MinerU 服务已禁用")
        return False
    
    client = MinerUClient(
        base_url=settings.mineru_base_url,
        timeout=settings.mineru_timeout,
        api_key=settings.mineru_api_key
    )
    
    print("\n📡 正在连接 MinerU 服务...")
    
    try:
        # 健康检查
        is_healthy = await client.health_check()
        
        if is_healthy:
            print("✅ MinerU 服务连接成功")
            
            # 获取服务信息
            service_info = await client.get_service_info()
            if service_info:
                print(f"ℹ️  服务信息: {service_info}")
            else:
                print("ℹ️  无法获取详细服务信息")
            
            return True
        else:
            print("❌ MinerU 服务无法访问")
            print("可能的原因:")
            print("  - MinerU 服务未启动")
            print("  - 服务地址配置错误")
            print("  - 网络连接问题")
            print("  - 防火墙阻止连接")
            return False
            
    except Exception as e:
        print(f"❌ 检查过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(check_mineru_service())
    sys.exit(0 if result else 1)