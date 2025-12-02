"""
Pipeline 可插拔算法模块

提供可扩展的文档处理和检索算法框架：
- chunkers/   : 文本切分器（简单分段、滑动窗口、父子分块等）
- retrievers/ : 检索器（稠密检索、BM25、混合检索等）
- registry.py : 算法注册表，支持按名称动态获取算法实例

使用示例：
    from app.pipeline import operator_registry
    
    # 获取切分器
    chunker = operator_registry.get("chunker", "sliding_window")(window=512)
    pieces = chunker.chunk("长文本...")
    
    # 获取检索器
    retriever = operator_registry.get("retriever", "hybrid")()
    results = await retriever.retrieve(query="问题", ...)
"""

from app.pipeline import chunkers, retrievers  # noqa: F401
from app.pipeline.registry import operator_registry

__all__ = ["operator_registry"]
