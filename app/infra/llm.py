"""
LLM 客户端模块

支持多种 LLM 提供商：
- OpenAI (GPT-4, GPT-3.5)
- Ollama (本地模型：qwen3, llama3 等)
- Gemini (Google)
- Qwen/通义千问 (阿里云 DashScope)
- Kimi/月之暗面 (Moonshot)
- DeepSeek
- 智谱 AI (GLM)
- SiliconFlow

使用示例：
    from app.infra.llm import get_llm_client, chat_completion
    
    # 简单调用
    response = await chat_completion("你好，请介绍一下自己")
    
    # 完整参数
    response = await chat_completion(
        prompt="总结以下文档",
        system_prompt="你是一个专业的文档摘要助手",
        temperature=0.3,
        max_tokens=500,
    )
"""

import json
import logging
from functools import lru_cache
from typing import Any, AsyncIterator

import httpx
from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def _get_openai_compatible_client(api_key: str | None, base_url: str | None) -> AsyncOpenAI:
    """获取 OpenAI 兼容客户端"""
    return AsyncOpenAI(
        api_key=api_key or "dummy",
        base_url=base_url,
        timeout=120.0,
    )


async def chat_completion(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs,
) -> str:
    """
    调用 LLM 进行对话补全
    
    Args:
        prompt: 用户输入
        system_prompt: 系统提示词
        temperature: 温度参数（0-2）
        max_tokens: 最大生成 token 数
        **kwargs: 其他参数
    
    Returns:
        str: LLM 生成的回复
    """
    settings = get_settings()
    config = settings.get_llm_config()
    provider = config["provider"]
    
    # 使用配置默认值
    if temperature is None:
        temperature = settings.llm_temperature
    if max_tokens is None:
        max_tokens = settings.llm_max_tokens
    
    try:
        if provider == "ollama":
            return await _ollama_chat(prompt, system_prompt, config, temperature, max_tokens)
        
        elif provider == "gemini":
            if not config.get("api_key"):
                raise ValueError("GEMINI_API_KEY 未配置")
            return await _gemini_chat(prompt, system_prompt, config, temperature, max_tokens)
        
        elif provider in ("openai", "qwen", "kimi", "deepseek", "zhipu", "siliconflow"):
            if not config.get("api_key"):
                raise ValueError(f"{provider.upper()}_API_KEY 未配置")
            return await _openai_compatible_chat(
                prompt, system_prompt, config, temperature, max_tokens
            )
        
        else:
            raise ValueError(f"未知的 LLM 提供者: {provider}")
            
    except Exception as e:
        logger.error(f"LLM 调用失败 ({provider}): {e}")
        raise


async def _ollama_chat(
    prompt: str,
    system_prompt: str | None,
    config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> str:
    """Ollama Chat API"""
    url = f"{config['base_url']}/api/chat"
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            url,
            json={
                "model": config["model"],
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


async def _openai_compatible_chat(
    prompt: str,
    system_prompt: str | None,
    config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> str:
    """OpenAI 兼容 API Chat"""
    client = _get_openai_compatible_client(config.get("api_key"), config.get("base_url"))
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = await client.chat.completions.create(
        model=config["model"],
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


async def _gemini_chat(
    prompt: str,
    system_prompt: str | None,
    config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> str:
    """Gemini API Chat"""
    url = f"{config['base_url']}/models/{config['model']}:generateContent"
    
    contents = []
    if system_prompt:
        contents.append({
            "role": "user",
            "parts": [{"text": f"System: {system_prompt}"}]
        })
        contents.append({
            "role": "model", 
            "parts": [{"text": "Understood."}]
        })
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            url,
            params={"key": config["api_key"]},
            json={
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            },
        )
        response.raise_for_status()
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]


def get_llm_client() -> AsyncOpenAI | None:
    """
    获取 OpenAI 兼容的 LLM 客户端
    
    注意：仅适用于 OpenAI 兼容的提供商
    对于 Ollama/Gemini 等，请使用 chat_completion 函数
    """
    settings = get_settings()
    config = settings.get_llm_config()
    
    if config["provider"] in ("openai", "qwen", "kimi", "deepseek", "zhipu", "siliconflow"):
        return _get_openai_compatible_client(config.get("api_key"), config.get("base_url"))
    
    return None


# ==================== 流式输出 ====================


async def chat_completion_stream(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs,
) -> AsyncIterator[str]:
    """
    流式调用 LLM 进行对话补全
    
    Args:
        prompt: 用户输入
        system_prompt: 系统提示词
        temperature: 温度参数（0-2）
        max_tokens: 最大生成 token 数
        **kwargs: 其他参数
    
    Yields:
        str: LLM 生成的文本片段
    """
    settings = get_settings()
    config = settings.get_llm_config()
    provider = config["provider"]
    
    # 使用配置默认值
    if temperature is None:
        temperature = settings.llm_temperature
    if max_tokens is None:
        max_tokens = settings.llm_max_tokens
    
    try:
        if provider == "ollama":
            async for chunk in _ollama_chat_stream(prompt, system_prompt, config, temperature, max_tokens):
                yield chunk
        
        elif provider in ("openai", "qwen", "kimi", "deepseek", "zhipu", "siliconflow"):
            if not config.get("api_key"):
                raise ValueError(f"{provider.upper()}_API_KEY 未配置")
            async for chunk in _openai_compatible_chat_stream(
                prompt, system_prompt, config, temperature, max_tokens
            ):
                yield chunk
        
        elif provider == "gemini":
            # Gemini 暂不支持流式，降级为非流式
            logger.warning("Gemini 暂不支持流式输出，将使用非流式模式")
            result = await _gemini_chat(prompt, system_prompt, config, temperature, max_tokens)
            yield result
        
        else:
            raise ValueError(f"未知的 LLM 提供者: {provider}")
            
    except Exception as e:
        logger.error(f"LLM 流式调用失败 ({provider}): {e}")
        raise


async def _ollama_chat_stream(
    prompt: str,
    system_prompt: str | None,
    config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[str]:
    """Ollama Chat API 流式输出"""
    url = f"{config['base_url']}/api/chat"
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            url,
            json={
                "model": config["model"],
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if content := data.get("message", {}).get("content"):
                        yield content


async def _openai_compatible_chat_stream(
    prompt: str,
    system_prompt: str | None,
    config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[str]:
    """OpenAI 兼容 API Chat 流式输出"""
    client = _get_openai_compatible_client(config.get("api_key"), config.get("base_url"))
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    stream = await client.chat.completions.create(
        model=config["model"],
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


# ==================== 动态配置支持 ====================


async def chat_completion_with_config(
    prompt: str,
    provider_config: dict[str, Any],
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs,
) -> str:
    """
    使用指定配置调用 LLM 进行对话补全
    
    此函数支持动态配置，配置来自 ModelConfigResolver 解析的结果。
    
    Args:
        prompt: 用户输入
        provider_config: 提供商配置，包含 provider, model, api_key, base_url
        system_prompt: 系统提示词
        temperature: 温度参数（0-2）
        max_tokens: 最大生成 token 数
        **kwargs: 其他参数
    
    Returns:
        str: LLM 生成的回复
    
    Example:
        config = await model_config_resolver.get_llm_config(session, tenant)
        provider_config = settings._get_provider_config(
            config["llm_provider"], 
            config["llm_model"]
        )
        response = await chat_completion_with_config(
            prompt="你好",
            provider_config=provider_config,
            temperature=config.get("llm_temperature"),
            max_tokens=config.get("llm_max_tokens"),
        )
    """
    provider = provider_config.get("provider")
    
    # 使用默认值
    settings = get_settings()
    if temperature is None:
        temperature = settings.llm_temperature
    if max_tokens is None:
        max_tokens = settings.llm_max_tokens
    
    try:
        if provider == "ollama":
            return await _ollama_chat(prompt, system_prompt, provider_config, temperature, max_tokens)
        
        elif provider == "gemini":
            if not provider_config.get("api_key"):
                raise ValueError("GEMINI_API_KEY 未配置")
            return await _gemini_chat(prompt, system_prompt, provider_config, temperature, max_tokens)
        
        elif provider in ("openai", "qwen", "kimi", "deepseek", "zhipu", "siliconflow"):
            if not provider_config.get("api_key"):
                raise ValueError(f"{provider.upper()}_API_KEY 未配置")
            return await _openai_compatible_chat(
                prompt, system_prompt, provider_config, temperature, max_tokens
            )
        
        else:
            raise ValueError(f"未知的 LLM 提供者: {provider}")
            
    except Exception as e:
        logger.error(f"LLM 调用失败 ({provider}): {e}")
        raise


async def chat_completion_stream_with_config(
    prompt: str,
    provider_config: dict[str, Any],
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs,
) -> AsyncIterator[str]:
    """
    使用指定配置流式调用 LLM 进行对话补全
    
    Args:
        prompt: 用户输入
        provider_config: 提供商配置
        system_prompt: 系统提示词
        temperature: 温度参数
        max_tokens: 最大生成 token 数
    
    Yields:
        str: LLM 生成的文本片段
    """
    provider = provider_config.get("provider")
    
    settings = get_settings()
    if temperature is None:
        temperature = settings.llm_temperature
    if max_tokens is None:
        max_tokens = settings.llm_max_tokens
    
    try:
        if provider == "ollama":
            async for chunk in _ollama_chat_stream(prompt, system_prompt, provider_config, temperature, max_tokens):
                yield chunk
        
        elif provider in ("openai", "qwen", "kimi", "deepseek", "zhipu", "siliconflow"):
            if not provider_config.get("api_key"):
                raise ValueError(f"{provider.upper()}_API_KEY 未配置")
            async for chunk in _openai_compatible_chat_stream(
                prompt, system_prompt, provider_config, temperature, max_tokens
            ):
                yield chunk
        
        elif provider == "gemini":
            logger.warning("Gemini 暂不支持流式输出，将使用非流式模式")
            result = await _gemini_chat(prompt, system_prompt, provider_config, temperature, max_tokens)
            yield result
        
        else:
            raise ValueError(f"未知的 LLM 提供者: {provider}")
            
    except Exception as e:
        logger.error(f"LLM 流式调用失败 ({provider}): {e}")
        raise
