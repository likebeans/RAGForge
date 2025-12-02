"""
RAG Pipeline Service - 启动入口

这是整个知识库服务的启动文件。
运行方式：
    - 直接执行：python main.py
    - 或者使用：uvicorn app.main:app --reload

服务启动后可以访问：
    - API 文档：http://localhost:8000/docs
    - 健康检查：http://localhost:8000/health
"""

import uvicorn


def main() -> None:
    """
    启动 FastAPI 服务器
    
    使用 uvicorn 作为 ASGI 服务器，支持以下特性：
    - 异步请求处理
    - 自动重载（开发模式）
    - 高性能并发
    """
    uvicorn.run(
        "app.main:app",  # 指向 app/main.py 中的 app 实例
        host="0.0.0.0",  # 监听所有网络接口，允许外部访问
        port=8000,       # 服务端口
        reload=True,     # 开发模式：代码修改后自动重启
    )


if __name__ == "__main__":
    # 当直接运行此文件时（而非被导入时），启动服务
    main()
