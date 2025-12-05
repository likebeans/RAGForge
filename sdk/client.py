"""
知识库服务 Python SDK

提供完整的 Python 客户端，封装所有 API 调用。
"""

from __future__ import annotations

from typing import Any

import httpx


class KBServiceClient:
    """
    知识库服务 Python 客户端
    
    功能：
    - 知识库管理（创建、列表、获取、更新、删除）
    - 文档管理（上传、列表、获取、删除、批量上传）
    - 检索（语义检索、RAG 生成）
    - API Key 管理
    - OpenAI 兼容接口
    
    使用示例：
        ```python
        from sdk import KBServiceClient
        
        # 方式1：上下文管理器（推荐）
        with KBServiceClient(api_key="kb_sk_xxx") as client:
            # 创建知识库
            kb = client.knowledge_bases.create("测试知识库")
            
            # 上传文档
            doc = client.documents.create(
                kb_id=kb["id"],
                title="文档标题",
                content="文档内容..."
            )
            
            # 检索
            results = client.retrieve(
                query="查询问题",
                knowledge_base_ids=[kb["id"]]
            )
            
            # RAG 生成
            answer = client.rag(
                query="查询问题",
                knowledge_base_ids=[kb["id"]]
            )
        
        # 方式2：手动管理
        client = KBServiceClient(api_key="kb_sk_xxx")
        try:
            kb = client.knowledge_bases.create("测试")
        finally:
            client.close()
        ```
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8020",
        timeout: float = 30.0,
    ):
        """
        初始化客户端
        
        Args:
            api_key: API Key（格式：kb_sk_xxx）
            base_url: 服务地址
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        
        # 初始化子模块
        self.knowledge_bases = KnowledgeBaseAPI(self)
        self.documents = DocumentAPI(self)
        self.api_keys = APIKeyAPI(self)
        self.openai = OpenAICompatAPI(self)
    
    def retrieve(
        self,
        query: str,
        knowledge_base_ids: list[str],
        top_k: int = 5,
        score_threshold: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
        retriever_override: dict[str, Any] | None = None,
        rerank: bool = False,
        rerank_top_k: int | None = None,
        context_window: int | None = None,
    ) -> dict[str, Any]:
        """
        检索知识库
        
        Args:
            query: 查询文本
            knowledge_base_ids: 知识库 ID 列表
            top_k: 返回结果数量
            score_threshold: 相似度阈值（0-1）
            metadata_filter: 元数据过滤条件
            retriever_override: 检索器覆盖配置
            rerank: 是否启用重排
            rerank_top_k: 重排后返回数量
            context_window: 上下文窗口扩展（前后各扩展 N 个 chunks）
        
        Returns:
            检索结果字典，包含 results 和 model 信息
        """
        payload: dict[str, Any] = {
            "query": query,
            "knowledge_base_ids": knowledge_base_ids,
            "top_k": top_k,
        }
        
        if score_threshold is not None:
            payload["score_threshold"] = score_threshold
        if metadata_filter:
            payload["metadata_filter"] = metadata_filter
        if retriever_override:
            payload["retriever_override"] = retriever_override
        if rerank:
            payload["rerank"] = rerank
        if rerank_top_k is not None:
            payload["rerank_top_k"] = rerank_top_k
        if context_window is not None:
            payload["context_window"] = context_window
        
        resp = self._client.post(f"{self.base_url}/v1/retrieve", json=payload)
        resp.raise_for_status()
        return resp.json()
    
    def rag(
        self,
        query: str,
        knowledge_base_ids: list[str],
        top_k: int = 5,
        score_threshold: float | None = None,
        retriever_override: dict[str, Any] | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> dict[str, Any]:
        """
        RAG 生成（检索 + LLM 生成）
        
        Args:
            query: 查询文本
            knowledge_base_ids: 知识库 ID 列表
            top_k: 检索结果数量
            score_threshold: 相似度阈值
            retriever_override: 检索器覆盖配置
            system_prompt: 系统提示词
            temperature: LLM 温度（0-2）
            max_tokens: 最大生成 token 数
            top_p: Top-p 采样
        
        Returns:
            RAG 结果字典，包含 answer、sources 和 model 信息
        """
        payload: dict[str, Any] = {
            "query": query,
            "knowledge_base_ids": knowledge_base_ids,
            "top_k": top_k,
            "temperature": temperature,
            "top_p": top_p,
        }
        
        if score_threshold is not None:
            payload["score_threshold"] = score_threshold
        if retriever_override:
            payload["retriever_override"] = retriever_override
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        resp = self._client.post(f"{self.base_url}/v1/rag", json=payload)
        resp.raise_for_status()
        return resp.json()
    
    def close(self) -> None:
        """关闭客户端连接"""
        self._client.close()
    
    def __enter__(self) -> "KBServiceClient":
        return self
    
    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class KnowledgeBaseAPI:
    """知识库管理 API"""
    
    def __init__(self, client: KBServiceClient):
        self._client = client
    
    def create(
        self,
        name: str,
        description: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        创建知识库
        
        Args:
            name: 知识库名称
            description: 描述
            config: 配置（chunker/retriever/indexer 等）
        
        Returns:
            知识库信息字典
        """
        payload: dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        if config:
            payload["config"] = config
        
        resp = self._client._client.post(
            f"{self._client.base_url}/v1/knowledge-bases",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
    
    def list(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """
        列出知识库
        
        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量
        
        Returns:
            包含 items、total、pages 的字典
        """
        resp = self._client._client.get(
            f"{self._client.base_url}/v1/knowledge-bases",
            params={"page": page, "page_size": page_size},
        )
        resp.raise_for_status()
        return resp.json()
    
    def get(self, kb_id: str) -> dict[str, Any]:
        """
        获取知识库详情
        
        Args:
            kb_id: 知识库 ID
        
        Returns:
            知识库信息字典
        """
        resp = self._client._client.get(
            f"{self._client.base_url}/v1/knowledge-bases/{kb_id}"
        )
        resp.raise_for_status()
        return resp.json()
    
    def update(
        self,
        kb_id: str,
        name: str | None = None,
        description: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        更新知识库
        
        Args:
            kb_id: 知识库 ID
            name: 新名称
            description: 新描述
            config: 新配置
        
        Returns:
            更新后的知识库信息
        """
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if config is not None:
            payload["config"] = config
        
        resp = self._client._client.patch(
            f"{self._client.base_url}/v1/knowledge-bases/{kb_id}",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
    
    def delete(self, kb_id: str) -> None:
        """
        删除知识库
        
        Args:
            kb_id: 知识库 ID
        """
        resp = self._client._client.delete(
            f"{self._client.base_url}/v1/knowledge-bases/{kb_id}"
        )
        resp.raise_for_status()


class DocumentAPI:
    """文档管理 API"""
    
    def __init__(self, client: KBServiceClient):
        self._client = client
    
    def create(
        self,
        kb_id: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        source: str | None = None,
        sensitivity_level: str = "internal",
        acl: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        创建文档
        
        Args:
            kb_id: 知识库 ID
            title: 文档标题
            content: 文档内容
            metadata: 元数据
            source: 来源
            sensitivity_level: 敏感度（public/internal/restricted）
            acl: 访问控制列表
        
        Returns:
            包含 document_id 和 chunk_count 的字典
        """
        payload: dict[str, Any] = {
            "title": title,
            "content": content,
            "sensitivity_level": sensitivity_level,
        }
        if metadata:
            payload["metadata"] = metadata
        if source:
            payload["source"] = source
        if acl:
            payload["acl"] = acl
        
        resp = self._client._client.post(
            f"{self._client.base_url}/v1/knowledge-bases/{kb_id}/documents",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
    
    def create_from_url(
        self,
        kb_id: str,
        url: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        从 URL 创建文档
        
        Args:
            kb_id: 知识库 ID
            url: 文档 URL
            title: 文档标题（可选，默认从 URL 提取）
            metadata: 元数据
        
        Returns:
            包含 document_id 和 chunk_count 的字典
        """
        payload: dict[str, Any] = {"url": url}
        if title:
            payload["title"] = title
        if metadata:
            payload["metadata"] = metadata
        
        resp = self._client._client.post(
            f"{self._client.base_url}/v1/knowledge-bases/{kb_id}/documents",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
    
    def upload_file(
        self,
        kb_id: str,
        file_path: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        上传文件
        
        Args:
            kb_id: 知识库 ID
            file_path: 本地文件路径
            title: 文档标题（可选）
            metadata: 元数据
        
        Returns:
            包含 document_id 和 chunk_count 的字典
        """
        with open(file_path, "rb") as f:
            files = {"file": f}
            data: dict[str, Any] = {}
            if title:
                data["title"] = title
            if metadata:
                import json
                data["metadata"] = json.dumps(metadata)
            
            resp = self._client._client.post(
                f"{self._client.base_url}/v1/knowledge-bases/{kb_id}/documents/upload",
                files=files,
                data=data if data else None,
            )
            resp.raise_for_status()
            return resp.json()
    
    def batch_create(
        self,
        kb_id: str,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        批量创建文档
        
        Args:
            kb_id: 知识库 ID
            documents: 文档列表，每个包含 title、content 等字段
        
        Returns:
            批量上传结果
        """
        resp = self._client._client.post(
            f"{self._client.base_url}/v1/knowledge-bases/{kb_id}/documents/batch",
            json={"documents": documents},
        )
        resp.raise_for_status()
        return resp.json()
    
    def list(
        self,
        kb_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """
        列出文档
        
        Args:
            kb_id: 知识库 ID
            page: 页码
            page_size: 每页数量
        
        Returns:
            包含 items、total、pages 的字典
        """
        resp = self._client._client.get(
            f"{self._client.base_url}/v1/knowledge-bases/{kb_id}/documents",
            params={"page": page, "page_size": page_size},
        )
        resp.raise_for_status()
        return resp.json()
    
    def get(self, document_id: str) -> dict[str, Any]:
        """
        获取文档详情
        
        Args:
            document_id: 文档 ID
        
        Returns:
            文档信息字典
        """
        resp = self._client._client.get(
            f"{self._client.base_url}/v1/documents/{document_id}"
        )
        resp.raise_for_status()
        return resp.json()
    
    def delete(self, document_id: str) -> None:
        """
        删除文档
        
        Args:
            document_id: 文档 ID
        """
        resp = self._client._client.delete(
            f"{self._client.base_url}/v1/documents/{document_id}"
        )
        resp.raise_for_status()


class APIKeyAPI:
    """API Key 管理 API"""
    
    def __init__(self, client: KBServiceClient):
        self._client = client
    
    def create(
        self,
        name: str,
        role: str = "write",
        scope_kb_ids: list[str] | None = None,
        identity: dict[str, Any] | None = None,
        rate_limit_per_minute: int | None = None,
    ) -> dict[str, Any]:
        """
        创建 API Key
        
        Args:
            name: Key 名称
            role: 角色（admin/write/read）
            scope_kb_ids: KB 白名单
            identity: 身份信息（用于 ACL）
            rate_limit_per_minute: 限流配置
        
        Returns:
            包含 api_key 的字典（明文 Key 仅此一次返回）
        """
        payload: dict[str, Any] = {"name": name, "role": role}
        if scope_kb_ids:
            payload["scope_kb_ids"] = scope_kb_ids
        if identity:
            payload["identity"] = identity
        if rate_limit_per_minute is not None:
            payload["rate_limit_per_minute"] = rate_limit_per_minute
        
        resp = self._client._client.post(
            f"{self._client.base_url}/v1/api-keys",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
    
    def list(self) -> dict[str, Any]:
        """
        列出 API Keys
        
        Returns:
            API Key 列表
        """
        resp = self._client._client.get(f"{self._client.base_url}/v1/api-keys")
        resp.raise_for_status()
        return resp.json()
    
    def delete(self, key_id: str) -> None:
        """
        删除 API Key
        
        Args:
            key_id: Key ID
        """
        resp = self._client._client.delete(
            f"{self._client.base_url}/v1/api-keys/{key_id}"
        )
        resp.raise_for_status()


class OpenAICompatAPI:
    """OpenAI 兼容 API"""
    
    def __init__(self, client: KBServiceClient):
        self._client = client
    
    def chat_completions(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4",
        knowledge_base_ids: list[str] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Chat Completions（OpenAI 兼容）
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            model: 模型名称
            knowledge_base_ids: 知识库 ID 列表（启用 RAG）
            temperature: 温度
            max_tokens: 最大 token 数
            top_p: Top-p 采样
            top_k: 检索 top-k
        
        Returns:
            OpenAI 格式的响应
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }
        if knowledge_base_ids:
            payload["knowledge_base_ids"] = knowledge_base_ids
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        resp = self._client._client.post(
            f"{self._client.base_url}/v1/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
    
    def embeddings(
        self,
        input: str | list[str],
        model: str = "text-embedding-3-small",
    ) -> dict[str, Any]:
        """
        Embeddings（OpenAI 兼容）
        
        Args:
            input: 输入文本或文本列表
            model: 模型名称
        
        Returns:
            OpenAI 格式的 Embedding 响应
        """
        payload = {"model": model, "input": input}
        
        resp = self._client._client.post(
            f"{self._client.base_url}/v1/embeddings",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
