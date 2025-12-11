"""模型提供商管理 API"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
import httpx
from typing import Iterable

from app.api.deps import get_current_api_key, APIKeyContext

router = APIRouter(prefix="/v1/model-providers", tags=["model-providers"])

# 支持的提供商配置
PROVIDER_CONFIGS = {
    "ollama": {
        "name": "Ollama",
        "description": "本地运行的开源模型",
        "base_url_required": True,
        "api_key_required": False,
        "default_base_url": "http://localhost:11434",
        "supports": {"llm": True, "embedding": True, "rerank": True},
    },
    "openai": {
        "name": "OpenAI",
        "description": "OpenAI GPT 系列模型",
        "base_url_required": False,
        "api_key_required": True,
        "default_base_url": "https://api.openai.com/v1",
        "supports": {"llm": True, "embedding": True, "rerank": False},
    },
    "qwen": {
        "name": "通义千问",
        "description": "阿里云通义千问模型",
        "base_url_required": False,
        "api_key_required": True,
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "supports": {"llm": True, "embedding": True, "rerank": False},
    },
    "deepseek": {
        "name": "DeepSeek",
        "description": "DeepSeek 深度求索模型",
        "base_url_required": False,
        "api_key_required": True,
        "default_base_url": "https://api.deepseek.com/v1",
        "supports": {"llm": True, "embedding": True, "rerank": False},
    },
    "zhipu": {
        "name": "智谱 AI",
        "description": "智谱 GLM 系列模型",
        "base_url_required": False,
        "api_key_required": True,
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "supports": {"llm": True, "embedding": True, "rerank": True},
    },
    "siliconflow": {
        "name": "SiliconFlow",
        "description": "硅基流动模型平台",
        "base_url_required": False,
        "api_key_required": True,
        "default_base_url": "https://api.siliconflow.cn/v1",
        "supports": {"llm": True, "embedding": True, "rerank": True},
    },
    "gemini": {
        "name": "Google Gemini",
        "description": "Google Gemini 模型",
        "base_url_required": False,
        "api_key_required": True,
        "default_base_url": "https://generativelanguage.googleapis.com/v1beta",
        "supports": {"llm": True, "embedding": True, "rerank": False},
    },
    "kimi": {
        "name": "Kimi",
        "description": "月之暗面 Kimi 模型",
        "base_url_required": False,
        "api_key_required": True,
        "default_base_url": "https://api.moonshot.cn/v1",
        "supports": {"llm": True, "embedding": False, "rerank": False},
    },
    "vllm": {
        "name": "vLLM",
        "description": "自部署 vLLM 服务（OpenAI 兼容）",
        "base_url_required": True,
        "api_key_required": False,
        "default_base_url": "http://localhost:8000/v1",
        "supports": {"llm": True, "embedding": True, "rerank": True},
    },
}

# 各提供商的常用模型（用于无法自动获取时的备选）
DEFAULT_MODELS = {
    "ollama": {
        "llm": ["qwen3:14b", "qwen3:8b", "qwen3:4b", "llama3.2:8b", "llama3.1:8b", "mistral:7b", "gemma2:9b"],
        "embedding": ["bge-m3", "nomic-embed-text", "mxbai-embed-large"],
        "rerank": ["bge-reranker-large", "bge-reranker-v2-m3"],
    },
    "openai": {
        "llm": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "embedding": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
        "rerank": [],
    },
    "qwen": {
        "llm": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-long"],
        "embedding": ["text-embedding-v3", "text-embedding-v2"],
        "rerank": [],
    },
    "deepseek": {
        "llm": ["deepseek-chat", "deepseek-coder"],
        "embedding": ["deepseek-embed"],
        "rerank": [],
    },
    "zhipu": {
        "llm": ["glm-4-plus", "glm-4", "glm-4-flash", "glm-3-turbo"],
        "embedding": ["embedding-3", "embedding-2"],
        "rerank": ["rerank"],
    },
    "siliconflow": {
        "llm": ["Qwen/Qwen2.5-72B-Instruct", "Qwen/Qwen2.5-32B-Instruct", "deepseek-ai/DeepSeek-V2.5"],
        "embedding": ["BAAI/bge-m3", "BAAI/bge-large-zh-v1.5"],
        "rerank": ["BAAI/bge-reranker-v2-m3"],
    },
    "gemini": {
        "llm": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
        "embedding": ["text-embedding-004"],
        "rerank": [],
    },
    "kimi": {
        "llm": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "embedding": [],
        "rerank": [],
    },
    "vllm": {
        "llm": [],
        "embedding": [],
        "rerank": ["BAAI/bge-reranker-v2-m3"],
    },
}


class ProviderConfig(BaseModel):
    """提供商配置信息"""
    name: str
    description: str
    base_url_required: bool
    api_key_required: bool
    default_base_url: str
    supports: dict[str, bool]


class ValidateProviderRequest(BaseModel):
    """验证提供商请求"""
    provider: str = Field(..., description="提供商名称")
    api_key: str | None = Field(None, description="API Key")
    base_url: str | None = Field(None, description="自定义 Base URL")


class ValidateProviderResponse(BaseModel):
    """验证提供商响应"""
    valid: bool
    message: str
    models: dict[str, list[str]] = Field(default_factory=dict, description="可用模型列表")


class ModelListResponse(BaseModel):
    """模型列表响应"""
    llm: list[str] = Field(default_factory=list)
    embedding: list[str] = Field(default_factory=list)
    rerank: list[str] = Field(default_factory=list)


@router.get("/", response_model=dict[str, ProviderConfig])
async def list_providers(
    _: APIKeyContext = Depends(get_current_api_key),
):
    """获取所有支持的模型提供商"""
    return {k: ProviderConfig(**v) for k, v in PROVIDER_CONFIGS.items()}


@router.post("/validate", response_model=ValidateProviderResponse)
async def validate_provider(
    request: ValidateProviderRequest,
    _: APIKeyContext = Depends(get_current_api_key),
):
    """
    验证提供商配置并获取可用模型列表
    
    对于 Ollama，会尝试获取实际安装的模型列表
    对于其他提供商，验证 API Key 有效性并返回默认模型列表
    """
    provider = request.provider.lower()
    
    if provider not in PROVIDER_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的提供商: {provider}",
        )
    
    config = PROVIDER_CONFIGS[provider]
    base_url = request.base_url or config["default_base_url"]
    
    # 检查必需的 API Key
    if config["api_key_required"] and not request.api_key:
        return ValidateProviderResponse(
            valid=False,
            message="此提供商需要 API Key",
            models={},
        )
    
    try:
        models = await _fetch_provider_models(provider, base_url, request.api_key)
        return ValidateProviderResponse(
            valid=True,
            message="连接成功",
            models=models,
        )
    except Exception as e:
        return ValidateProviderResponse(
            valid=False,
            message=f"连接失败: {str(e)}",
            models={},
        )


@router.get("/{provider}/models", response_model=ModelListResponse)
async def get_provider_models(
    provider: str,
    api_key: str | None = None,
    base_url: str | None = None,
    _: APIKeyContext = Depends(get_current_api_key),
):
    """获取指定提供商的模型列表"""
    provider = provider.lower()
    
    if provider not in PROVIDER_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的提供商: {provider}",
        )
    
    config = PROVIDER_CONFIGS[provider]
    base_url = base_url or config["default_base_url"]
    
    try:
        models = await _fetch_provider_models(provider, base_url, api_key)
        return ModelListResponse(**models)
    except Exception:
        # 返回默认模型列表
        default = DEFAULT_MODELS.get(provider, {})
        return ModelListResponse(
            llm=default.get("llm", []),
            embedding=default.get("embedding", []),
            rerank=default.get("rerank", []),
        )


async def _get_ollama_models(base_url: str) -> dict[str, list[str]]:
    """获取 Ollama 安装的模型列表"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}/api/tags")
        response.raise_for_status()
        data = response.json()
        
        models = [m["name"] for m in data.get("models", [])]
        
        # 分类模型（基于模型名称的启发式判断）
        llm_models = []
        embedding_models = []
        rerank_models = []
        
        for model in models:
            name_lower = model.lower()
            # rerank 判断优先（bge-reranker 等）
            if "rerank" in name_lower:
                rerank_models.append(model)
            elif "embed" in name_lower or "bge-m3" in name_lower:
                embedding_models.append(model)
            else:
                llm_models.append(model)
        
        return {
            "llm": llm_models,
            "embedding": embedding_models,
            "rerank": rerank_models,
        }


def _classify_models(model_ids: Iterable[str]) -> dict[str, list[str]]:
    """将模型 ID 分类为 llm / embedding / rerank"""
    llm_models: list[str] = []
    embedding_models: list[str] = []
    rerank_models: list[str] = []

    for model in model_ids:
        name_lower = model.lower()
        # rerank 判断优先（bge-reranker 等）
        if "rerank" in name_lower:
            rerank_models.append(model)
        elif "embed" in name_lower or "embedding" in name_lower or "bge-m3" in name_lower:
            # bge-m3 是 embedding 模型，但 bge-reranker 已被上面捕获
            embedding_models.append(model)
        else:
            llm_models.append(model)

    return {
        "llm": llm_models,
        "embedding": embedding_models,
        "rerank": rerank_models,
    }


async def _fetch_provider_models(
    provider: str,
    base_url: str,
    api_key: str | None,
) -> dict[str, list[str]]:
    """
    使用提供商的 /models 接口获取模型列表

    - Ollama: /api/tags
    - OpenAI 兼容: /models (Authorization: Bearer <api_key>)
    - Gemini: /models?key=<api_key>
    """
    provider = provider.lower()

    if provider == "ollama":
        return await _get_ollama_models(base_url)

    if provider == "gemini":
        if not api_key:
            raise ValueError("Gemini 需要提供 API Key")
        return await _get_gemini_models(base_url, api_key)

    # 其余默认按 OpenAI 兼容接口处理
    if not api_key and PROVIDER_CONFIGS.get(provider, {}).get("api_key_required"):
        raise ValueError("此提供商需要 API Key")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"} if api_key else None,
        )
        response.raise_for_status()
        data = response.json()

        # OpenAI 兼容接口通常返回 { data: [{id: "..."}] }
        ids = [item.get("id") for item in data.get("data", []) if item.get("id")]
        if not ids:
            # 一些厂商返回 list
            if isinstance(data, list):
                ids = [item.get("id") or item.get("name") or item for item in data if item]

        classified = _classify_models(ids)
        if not any(classified.values()):
            default_models = DEFAULT_MODELS.get(provider, {})
            return {
                "llm": default_models.get("llm", []),
                "embedding": default_models.get("embedding", []),
                "rerank": default_models.get("rerank", []),
            }
        return classified


async def _get_gemini_models(base_url: str, api_key: str) -> dict[str, list[str]]:
    """获取 Gemini 模型列表"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}/models", params={"key": api_key})
        response.raise_for_status()
        data = response.json()
        models = []
        for item in data.get("models", []):
            name = item.get("name")
            if not name:
                continue
            # name 形如 models/gemini-1.5-pro
            models.append(name.split("/")[-1])
        return _classify_models(models)
