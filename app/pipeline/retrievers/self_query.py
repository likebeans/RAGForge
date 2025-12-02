"""
自查询检索器（Self-Query Retriever）

使用 LLM 解析用户查询，自动提取元数据过滤条件。
适用于结构化过滤场景，如「找2024年的Python教程」。

特点：
- LLM 自动解析查询意图
- 生成元数据过滤条件
- 结合语义检索和精确过滤
"""

import json
import logging
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator, operator_registry

logger = logging.getLogger(__name__)

# 查询解析提示词
QUERY_PARSE_PROMPT = """你是一个查询解析助手。分析用户查询，提取出语义查询部分和元数据过滤条件。

可用的元数据字段：
{metadata_fields}

用户查询：{query}

请以 JSON 格式返回：
{{
    "semantic_query": "用于语义检索的查询文本",
    "filters": {{
        "字段名": "值"
    }}
}}

规则：
1. semantic_query 是去除过滤条件后的核心查询
2. filters 只包含能明确匹配元数据字段的条件
3. 如果查询中没有明确的过滤条件，filters 为空对象 {{}}
4. 不要编造不存在的字段

返回 JSON："""


@register_operator("retriever", "self_query")
class SelfQueryRetriever(BaseRetrieverOperator):
    """
    自查询检索器
    
    使用示例：
    ```python
    retriever = operator_registry.get("retriever", "self_query")(
        base_retriever="dense",
        metadata_fields={
            "year": "文档年份（数字）",
            "language": "编程语言",
            "source": "来源（url/file/text）",
            "author": "作者名称",
        },
    )
    results = await retriever.retrieve(query="找2024年的Python教程", ...)
    ```
    """
    
    name = "self_query"
    kind = "retriever"
    
    def __init__(
        self,
        base_retriever: str = "dense",
        base_retriever_params: dict | None = None,
        metadata_fields: dict[str, str] | None = None,
        model: str | None = None,
    ):
        """
        Args:
            base_retriever: 底层检索器名称
            base_retriever_params: 底层检索器参数
            metadata_fields: 可用的元数据字段及其描述
            model: 使用的 LLM 模型
        """
        self.base_retriever_name = base_retriever
        self.base_retriever_params = base_retriever_params or {}
        self.metadata_fields = metadata_fields or {
            "source": "文档来源（url/file/text）",
            "document_id": "文档 ID",
            "year": "年份",
            "language": "语言",
        }
        
        settings = get_settings()
        self.model = model or settings.openai_model
        self._client: OpenAI | None = None
    
    def _get_client(self) -> OpenAI | None:
        """延迟初始化 LLM 客户端"""
        if self._client is None:
            settings = get_settings()
            if not settings.openai_api_key:
                logger.warning("OPENAI_API_KEY 未配置，Self-Query 将不解析过滤条件")
                return None
            
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
            )
        return self._client
    
    def _get_base_retriever(self) -> BaseRetrieverOperator:
        """获取底层检索器"""
        factory = operator_registry.get("retriever", self.base_retriever_name)
        if not factory:
            raise ValueError(f"未找到检索器: {self.base_retriever_name}")
        return factory(**self.base_retriever_params)
    
    def _parse_query(self, query: str) -> tuple[str, dict]:
        """
        解析查询，提取语义查询和过滤条件
        
        Returns:
            (semantic_query, filters)
        """
        client = self._get_client()
        if client is None:
            return query, {}
        
        try:
            # 构建字段描述
            fields_desc = "\n".join(
                f"- {name}: {desc}"
                for name, desc in self.metadata_fields.items()
            )
            
            prompt = QUERY_PARSE_PROMPT.format(
                metadata_fields=fields_desc,
                query=query,
            )
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0,
            )
            
            if response.choices:
                content = response.choices[0].message.content
                if content:
                    # 解析 JSON
                    # 尝试提取 JSON 部分（处理可能的 markdown 代码块）
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    
                    result = json.loads(content.strip())
                    semantic_query = result.get("semantic_query", query)
                    filters = result.get("filters", {})
                    
                    # 验证过滤字段
                    valid_filters = {
                        k: v for k, v in filters.items()
                        if k in self.metadata_fields and v
                    }
                    
                    logger.info(f"Self-Query 解析: query='{semantic_query}', filters={valid_filters}")
                    return semantic_query, valid_filters
        
        except json.JSONDecodeError as e:
            logger.warning(f"Self-Query JSON 解析失败: {e}")
        except Exception as e:
            logger.warning(f"Self-Query 解析失败: {e}")
        
        return query, {}
    
    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        执行自查询检索
        
        1. LLM 解析查询，提取过滤条件
        2. 使用底层检索器检索
        3. 应用元数据过滤
        """
        # 解析查询
        semantic_query, filters = self._parse_query(query)
        
        # 使用底层检索器检索（多召回一些以便过滤）
        base_retriever = self._get_base_retriever()
        recall_k = top_k * 3 if filters else top_k
        
        results = await base_retriever.retrieve(
            query=semantic_query,
            tenant_id=tenant_id,
            kb_ids=kb_ids,
            top_k=recall_k,
        )
        
        # 应用元数据过滤
        if filters:
            filtered_results = []
            for hit in results:
                metadata = hit.get("metadata", {})
                match = True
                for key, value in filters.items():
                    meta_value = metadata.get(key)
                    # 支持字符串部分匹配
                    if meta_value is not None:
                        if isinstance(meta_value, str) and isinstance(value, str):
                            if value.lower() not in meta_value.lower():
                                match = False
                                break
                        elif str(meta_value) != str(value):
                            match = False
                            break
                    else:
                        match = False
                        break
                
                if match:
                    filtered_results.append(hit)
            
            results = filtered_results[:top_k]
        else:
            results = results[:top_k]
        
        # 标记来源
        for hit in results:
            hit["source"] = "self_query"
            hit["parsed_filters"] = filters
        
        return results
