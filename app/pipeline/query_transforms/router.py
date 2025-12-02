"""
查询路由器 (Query Router)

根据查询类型自动选择最佳检索策略。

路由策略：
- semantic: 语义问题 → Dense 检索
- keyword: 关键词/术语查询 → BM25 优先
- hybrid: 混合问题 → Hybrid + RRF
- code: 代码相关 → 代码专用检索器

实现方式：
- 规则匹配（快速）：正则检测代码模式、问句类型
- LLM 分类（精准）：使用小模型判断查询意图
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """查询类型"""
    SEMANTIC = "semantic"    # 语义问题（什么是...、如何...、为什么...）
    KEYWORD = "keyword"      # 关键词查询（专业术语、名词短语）
    HYBRID = "hybrid"        # 混合问题
    CODE = "code"            # 代码相关（函数、类、代码片段）


@dataclass
class RouteResult:
    """路由结果"""
    query_type: QueryType
    retriever: str           # 推荐的检索器名称
    confidence: float        # 置信度 0-1
    reason: str             # 路由原因


# 检索器映射
RETRIEVER_MAP = {
    QueryType.SEMANTIC: "dense",
    QueryType.KEYWORD: "bm25",
    QueryType.HYBRID: "hybrid",
    QueryType.CODE: "hybrid",  # 代码查询也用混合检索
}


# 代码相关模式
CODE_PATTERNS = [
    r'\b(function|def|class|method|api|endpoint)\b',
    r'\b(import|from|require|include)\b',
    r'\b(error|exception|bug|fix)\b.*\b(code|function|method)\b',
    r'`[^`]+`',  # 反引号包围的代码
    r'\b\w+\(\)',  # 函数调用模式
    r'\b(how to|how do i)\b.*\b(implement|code|write|create)\b',
    r'\.(py|js|ts|java|go|rs|cpp|c|h)\b',
]

# 语义问题模式
SEMANTIC_PATTERNS = [
    r'^(what|what\'s|whats)\s+(is|are|was|were)\b',
    r'^(how|why|when|where|who)\b',
    r'^(explain|describe|tell me|can you)\b',
    r'(什么|为什么|怎么|如何|怎样|哪个|哪些)',
    r'(解释|说明|介绍|描述)',
]

# 关键词查询模式（短查询、名词短语）
KEYWORD_PATTERNS = [
    r'^[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*$',  # PascalCase 术语
    r'^[a-z]+(?:_[a-z]+)*$',  # snake_case 标识符
    r'^[a-z]+(?:-[a-z]+)*$',  # kebab-case 标识符
    r'^\S+$',  # 单个词
]


class QueryRouter:
    """
    查询路由器
    
    使用示例：
    ```python
    router = QueryRouter()
    result = router.route("什么是 RAG？")
    print(result.retriever)  # "dense"
    
    # 使用 LLM 路由（更精准）
    router = QueryRouter(use_llm=True)
    result = await router.aroute("如何实现分页？")
    ```
    """
    
    def __init__(
        self,
        use_llm: bool = False,
        model: str | None = None,
        default_type: QueryType = QueryType.HYBRID,
    ):
        """
        Args:
            use_llm: 是否使用 LLM 进行路由（更精准但较慢）
            model: LLM 模型名称
            default_type: 默认查询类型（无法判断时使用）
        """
        self.use_llm = use_llm
        self.default_type = default_type
        
        settings = get_settings()
        self.model = model or settings.openai_model
        self._client: OpenAI | None = None
    
    def _get_client(self) -> OpenAI:
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            settings = get_settings()
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY 未配置")
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
            )
        return self._client
    
    def _rule_based_route(self, query: str) -> RouteResult:
        """基于规则的路由（快速）"""
        query_lower = query.lower().strip()
        
        # 检查代码模式
        for pattern in CODE_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return RouteResult(
                    query_type=QueryType.CODE,
                    retriever=RETRIEVER_MAP[QueryType.CODE],
                    confidence=0.8,
                    reason=f"匹配代码模式: {pattern}",
                )
        
        # 检查语义问题模式
        for pattern in SEMANTIC_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return RouteResult(
                    query_type=QueryType.SEMANTIC,
                    retriever=RETRIEVER_MAP[QueryType.SEMANTIC],
                    confidence=0.8,
                    reason=f"匹配语义模式: {pattern}",
                )
        
        # 检查关键词模式（短查询）
        word_count = len(query.split())
        if word_count <= 3:
            for pattern in KEYWORD_PATTERNS:
                if re.match(pattern, query_lower):
                    return RouteResult(
                        query_type=QueryType.KEYWORD,
                        retriever=RETRIEVER_MAP[QueryType.KEYWORD],
                        confidence=0.7,
                        reason=f"短查询/关键词模式",
                    )
        
        # 默认使用混合检索
        return RouteResult(
            query_type=self.default_type,
            retriever=RETRIEVER_MAP[self.default_type],
            confidence=0.5,
            reason="无明确模式，使用默认策略",
        )
    
    def _llm_route(self, query: str) -> RouteResult:
        """基于 LLM 的路由（精准）"""
        try:
            client = self._get_client()
            
            prompt = f"""分析以下查询，判断其类型。

查询：{query}

类型选项：
1. semantic - 语义问题（什么是、为什么、如何、解释类问题）
2. keyword - 关键词查询（专业术语、名词短语、标识符）
3. code - 代码相关（函数、类、API、代码实现问题）
4. hybrid - 混合问题（无法明确分类）

只返回类型名称（semantic/keyword/code/hybrid），不要其他内容。"""

            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0,
            )
            
            if response.choices:
                result = response.choices[0].message.content.strip().lower()
                
                type_map = {
                    "semantic": QueryType.SEMANTIC,
                    "keyword": QueryType.KEYWORD,
                    "code": QueryType.CODE,
                    "hybrid": QueryType.HYBRID,
                }
                
                query_type = type_map.get(result, self.default_type)
                return RouteResult(
                    query_type=query_type,
                    retriever=RETRIEVER_MAP[query_type],
                    confidence=0.9,
                    reason=f"LLM 分类: {result}",
                )
        
        except Exception as e:
            logger.warning(f"LLM 路由失败: {e}")
        
        # 回退到规则路由
        return self._rule_based_route(query)
    
    def route(self, query: str) -> RouteResult:
        """
        同步路由查询
        
        Args:
            query: 用户查询
            
        Returns:
            RouteResult 包含推荐的检索器和置信度
        """
        if self.use_llm:
            return self._llm_route(query)
        return self._rule_based_route(query)
    
    async def aroute(self, query: str) -> RouteResult:
        """异步路由查询"""
        import asyncio
        return await asyncio.to_thread(self.route, query)
    
    def get_retriever_name(self, query: str) -> str:
        """获取推荐的检索器名称"""
        return self.route(query).retriever


@dataclass
class RouterConfig:
    """路由器配置"""
    enabled: bool = True
    use_llm: bool = False
    model: str | None = None
    default_type: str = "hybrid"


def get_query_router(config: RouterConfig | None = None) -> QueryRouter | None:
    """
    获取查询路由器
    
    Args:
        config: 路由器配置
        
    Returns:
        QueryRouter 实例，未启用时返回 None
    """
    if config is None:
        config = RouterConfig()
    
    if not config.enabled:
        return None
    
    default_type = QueryType(config.default_type)
    return QueryRouter(
        use_llm=config.use_llm,
        model=config.model,
        default_type=default_type,
    )


# 便捷函数
def route_query(query: str, use_llm: bool = False) -> RouteResult:
    """
    路由查询
    
    Args:
        query: 用户查询
        use_llm: 是否使用 LLM
        
    Returns:
        RouteResult
    """
    router = QueryRouter(use_llm=use_llm)
    return router.route(query)
