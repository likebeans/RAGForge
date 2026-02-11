# MinerU PDF 解析服务客户端

import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MinerUClient:
    """MinerU PDF 解析服务客户端"""
    
    def __init__(self, base_url: str, timeout: int = 300, api_key: str | None = None):
        """
        Args:
            base_url: MinerU 服务地址，如 http://localhost:8010
            timeout: 请求超时时间（秒），PDF 解析可能较慢
            api_key: API Key（可选，用于云服务认证）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(float(timeout))
        self.api_key = api_key
    
    async def parse_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        output_format: str = "markdown",
    ) -> dict[str, Any]:
        """
        调用 MinerU 解析 PDF
        
        Args:
            file_bytes: PDF 文件二进制
            filename: 文件名
            output_format: 输出格式（markdown/json）
        
        Returns:
            {
                "markdown": "...",          # Markdown 格式全文
                "blocks": [...],            # 分块内容
                "tables": [...],            # 表格数据
                "page_count": 10,           # 页数
            }
        """
        # 构建请求头（如果有 API Key）
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            files = {"file": (filename, file_bytes, "application/pdf")}
            data = {"output_format": output_format}
            
            try:
                # 尝试标准 MinerU API
                response = await client.post(
                    f"{self.base_url}/api/v1/parse",
                    files=files,
                    data=data,
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"MinerU 解析完成: {filename}, "
                    f"页数: {result.get('page_count', 'N/A')}, "
                    f"内容长度: {len(result.get('markdown', ''))}"
                )
                return self._normalize_result(result)
                
            except httpx.HTTPStatusError as e:
                # 尝试备用 API 路径
                if e.response.status_code == 404:
                    return await self._try_alternative_api(client, files, data, filename)
                
                logger.error(f"MinerU 服务返回错误: {e.response.status_code} - {e.response.text[:200]}")
                raise ValueError(f"MinerU 解析失败: HTTP {e.response.status_code}")
            
            except httpx.ConnectError:
                logger.error(f"无法连接 MinerU 服务: {self.base_url}")
                raise ValueError(f"无法连接 MinerU 服务: {self.base_url}")
            
            except httpx.TimeoutException:
                logger.error(f"MinerU 服务响应超时: {self.timeout.read}s")
                raise ValueError("MinerU 服务响应超时，请增加超时时间或减小文件大小")
    
    async def _try_alternative_api(
        self,
        client: httpx.AsyncClient,
        files: dict,
        data: dict,
        filename: str,
    ) -> dict[str, Any]:
        """尝试备用 API 路径（兼容不同版本的 MinerU）"""
        alternative_paths = [
            "/parse",
            "/api/parse",
            "/v1/parse",
            "/pdf/parse",
        ]
        
        for path in alternative_paths:
            try:
                response = await client.post(
                    f"{self.base_url}{path}",
                    files=files,
                    data=data,
                )
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"MinerU 备用 API 成功: {path}")
                    return self._normalize_result(result)
            except Exception:
                continue
        
        raise ValueError("MinerU API 不可用，已尝试所有路径")
    
    def _normalize_result(self, result: dict) -> dict[str, Any]:
        """规范化 MinerU 返回结果"""
        normalized = {
            "markdown": "",
            "blocks": [],
            "tables": [],
            "page_count": 0,
        }
        
        # 处理不同版本 MinerU 的返回格式
        if "markdown" in result:
            normalized["markdown"] = result["markdown"]
        elif "content" in result:
            normalized["markdown"] = result["content"]
        elif "text" in result:
            normalized["markdown"] = result["text"]
        
        if "blocks" in result:
            normalized["blocks"] = result["blocks"]
        elif "elements" in result:
            # 转换 elements 格式为 blocks
            normalized["blocks"] = [
                {
                    "type": elem.get("type", "text"),
                    "content": elem.get("text", elem.get("content", "")),
                    "page": elem.get("page", elem.get("page_number")),
                    "bbox": elem.get("bbox", elem.get("bounding_box")),
                    "table_data": elem.get("table_data"),
                }
                for elem in result["elements"]
            ]
        
        if "tables" in result:
            normalized["tables"] = result["tables"]
        
        if "page_count" in result:
            normalized["page_count"] = result["page_count"]
        elif "pages" in result:
            normalized["page_count"] = len(result["pages"])
        elif "num_pages" in result:
            normalized["page_count"] = result["num_pages"]
        
        return normalized
    
    async def health_check(self) -> bool:
        """检查 MinerU 服务是否可用"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                # 尝试多个健康检查路径
                for path in ["/health", "/api/health", "/", "/api/v1/health"]:
                    try:
                        response = await client.get(f"{self.base_url}{path}")
                        if response.status_code == 200:
                            return True
                    except Exception:
                        continue
                return False
            except Exception:
                return False
    
    async def get_service_info(self) -> dict | None:
        """获取 MinerU 服务信息"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                response = await client.get(f"{self.base_url}/api/v1/info")
                if response.status_code == 200:
                    return response.json()
            except Exception:
                pass
            return None
