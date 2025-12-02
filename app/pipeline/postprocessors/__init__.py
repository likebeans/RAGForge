"""
后处理器模块

提供检索结果的后处理功能：
- ContextWindowPostprocessor: 上下文窗口扩展
"""

from app.pipeline.postprocessors.context_window import (
    ContextWindowPostprocessor,
    expand_context_window,
)

__all__ = [
    "ContextWindowPostprocessor",
    "expand_context_window",
]
