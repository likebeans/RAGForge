"""
算法注册表

提供算法组件的注册和发现机制，类似插件系统。

使用方式：
1. 通过装饰器注册：
   @register_operator("chunker", "my_chunker")
   class MyChunker: ...

2. 通过注册表获取：
   chunker_cls = operator_registry.get("chunker", "my_chunker")
   instance = chunker_cls(param=value)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class OperatorRegistry:
    """
    算法组件注册表
    
    按 kind（类型）和 name（名称）两级索引管理算法组件。
    """
    
    def __init__(self) -> None:
        # 二级字典: kind -> name -> operator_class
        self._operators: dict[str, dict[str, Any]] = defaultdict(dict)

    def register(self, kind: str, name: str, op: Any) -> None:
        """注册算法组件"""
        self._operators[kind][name] = op

    def get(self, kind: str, name: str) -> Any:
        """获取算法组件类"""
        return self._operators.get(kind, {}).get(name)

    def list(self, kind: str) -> list[str]:
        """列出某类型下所有已注册的算法名称"""
        return list(self._operators.get(kind, {}).keys())


# 全局单例
operator_registry = OperatorRegistry()


def register_operator(kind: str, name: str) -> Callable[[Any], Any]:
    """
    算法注册装饰器
    
    使用示例：
        @register_operator("chunker", "simple")
        class SimpleChunker:
            ...
    """
    def wrapper(cls_or_fn: Any) -> Any:
        operator_registry.register(kind, name, cls_or_fn)
        return cls_or_fn

    return wrapper
