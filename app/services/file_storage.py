# 文件存储服务
# 统一管理原始文件、图片、解析结果的 OSS 存储

import uuid
import json
import logging
from typing import Any

from app.infra.oss_client import get_oss_client, OSSClient

logger = logging.getLogger(__name__)


class FileStorageService:
    """
    文件存储服务
    
    存储路径规则：
    - 原始文件: {tenant_id}/raw/{doc_id}/{filename}
    - PDF 图片: {tenant_id}/images/{doc_id}/{image_id}.{format}
    - 解析结果: {tenant_id}/parsed/{doc_id}/result.json
    - 缩略图: {tenant_id}/thumbnails/{doc_id}/page_{n}.png
    """
    
    def __init__(self, oss_client: OSSClient | None = None):
        """
        Args:
            oss_client: OSS 客户端，默认自动获取
        """
        self._oss = oss_client
    
    @property
    def oss(self) -> OSSClient | None:
        """延迟初始化 OSS 客户端"""
        if self._oss is None:
            self._oss = get_oss_client()
        return self._oss
    
    @property
    def enabled(self) -> bool:
        """OSS 是否启用"""
        return self.oss is not None
    
    async def store_raw_file(
        self,
        tenant_id: str,
        doc_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str | None:
        """
        存储原始上传文件
        
        Args:
            tenant_id: 租户 ID
            doc_id: 文档 ID
            filename: 原始文件名
            content: 文件内容
            content_type: MIME 类型
        
        Returns:
            OSS 路径，如果 OSS 未启用则返回 None
        """
        if not self.oss:
            return None
        
        key = f"{tenant_id}/raw/{doc_id}/{filename}"
        
        # 自动推断 content_type
        if not content_type:
            content_type = self._guess_content_type(filename)
        
        try:
            oss_path = await self.oss.upload(key, content, content_type)
            logger.info(f"原始文件已存储: {oss_path}, size={len(content)}")
            return oss_path
        except Exception as e:
            logger.error(f"原始文件存储失败: {key}, {e}")
            return None
    
    async def store_image(
        self,
        tenant_id: str,
        doc_id: str,
        image_data: bytes,
        image_format: str = "png",
        image_id: str | None = None,
    ) -> str | None:
        """
        存储文档中提取的图片
        
        Args:
            tenant_id: 租户 ID
            doc_id: 文档 ID
            image_data: 图片二进制数据
            image_format: 图片格式（png/jpg/webp）
            image_id: 图片 ID，默认自动生成
        
        Returns:
            OSS 路径
        """
        if not self.oss:
            return None
        
        if not image_id:
            image_id = str(uuid.uuid4())[:8]
        
        key = f"{tenant_id}/images/{doc_id}/{image_id}.{image_format}"
        content_type = f"image/{image_format}"
        
        try:
            oss_path = await self.oss.upload(key, image_data, content_type)
            logger.debug(f"图片已存储: {oss_path}")
            return oss_path
        except Exception as e:
            logger.error(f"图片存储失败: {key}, {e}")
            return None
    
    async def store_images_batch(
        self,
        tenant_id: str,
        doc_id: str,
        images: list[bytes],
        image_format: str = "png",
    ) -> list[str]:
        """
        批量存储图片
        
        Args:
            tenant_id: 租户 ID
            doc_id: 文档 ID
            images: 图片列表
            image_format: 图片格式
        
        Returns:
            OSS 路径列表
        """
        if not self.oss or not images:
            return []
        
        paths = []
        for i, image_data in enumerate(images):
            image_id = f"{i:04d}"
            path = await self.store_image(
                tenant_id, doc_id, image_data, image_format, image_id
            )
            if path:
                paths.append(path)
        
        return paths
    
    async def store_parsed_result(
        self,
        tenant_id: str,
        doc_id: str,
        result: dict[str, Any],
    ) -> str | None:
        """
        存储文件解析结果（JSON 格式）
        
        Args:
            tenant_id: 租户 ID
            doc_id: 文档 ID
            result: 解析结果字典
        
        Returns:
            OSS 路径
        """
        if not self.oss:
            return None
        
        key = f"{tenant_id}/parsed/{doc_id}/result.json"
        content = json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
        
        try:
            oss_path = await self.oss.upload(key, content, "application/json")
            logger.info(f"解析结果已存储: {oss_path}")
            return oss_path
        except Exception as e:
            logger.error(f"解析结果存储失败: {key}, {e}")
            return None
    
    async def store_thumbnail(
        self,
        tenant_id: str,
        doc_id: str,
        page_number: int,
        image_data: bytes,
        image_format: str = "png",
    ) -> str | None:
        """
        存储文档缩略图
        
        Args:
            tenant_id: 租户 ID
            doc_id: 文档 ID
            page_number: 页码（从 1 开始）
            image_data: 缩略图数据
            image_format: 图片格式
        
        Returns:
            OSS 路径
        """
        if not self.oss:
            return None
        
        key = f"{tenant_id}/thumbnails/{doc_id}/page_{page_number}.{image_format}"
        content_type = f"image/{image_format}"
        
        try:
            oss_path = await self.oss.upload(key, image_data, content_type)
            logger.debug(f"缩略图已存储: {oss_path}")
            return oss_path
        except Exception as e:
            logger.error(f"缩略图存储失败: {key}, {e}")
            return None
    
    async def get_file_url(
        self,
        oss_path: str,
        expires: int = 3600,
    ) -> str | None:
        """
        获取文件的预签名访问 URL
        
        Args:
            oss_path: OSS 路径（oss://bucket/key 格式）
            expires: URL 有效期（秒）
        
        Returns:
            预签名 URL
        """
        if not self.oss or not oss_path:
            return None
        
        # 解析 oss://bucket/key 格式
        key = self._parse_oss_path(oss_path)
        if not key:
            return None
        
        try:
            return await self.oss.get_url(key, expires)
        except Exception as e:
            logger.error(f"获取预签名 URL 失败: {oss_path}, {e}")
            return None
    
    async def download_file(self, oss_path: str) -> bytes | None:
        """
        下载文件
        
        Args:
            oss_path: OSS 路径
        
        Returns:
            文件内容
        """
        if not self.oss or not oss_path:
            return None
        
        key = self._parse_oss_path(oss_path)
        if not key:
            return None
        
        try:
            return await self.oss.download(key)
        except Exception as e:
            logger.error(f"文件下载失败: {oss_path}, {e}")
            return None
    
    async def delete_document_files(
        self,
        tenant_id: str,
        doc_id: str,
    ) -> int:
        """
        删除文档相关的所有文件
        
        Args:
            tenant_id: 租户 ID
            doc_id: 文档 ID
        
        Returns:
            删除的文件数量
        """
        if not self.oss:
            return 0
        
        deleted = 0
        
        # 删除各类文件
        prefixes = [
            f"{tenant_id}/raw/{doc_id}/",
            f"{tenant_id}/images/{doc_id}/",
            f"{tenant_id}/parsed/{doc_id}/",
            f"{tenant_id}/thumbnails/{doc_id}/",
        ]
        
        for prefix in prefixes:
            try:
                objects = await self.oss.list_objects(prefix)
                for key in objects:
                    if await self.oss.delete(key):
                        deleted += 1
            except Exception as e:
                logger.warning(f"删除文件失败: prefix={prefix}, {e}")
        
        if deleted > 0:
            logger.info(f"已删除文档 {doc_id} 的 {deleted} 个文件")
        
        return deleted
    
    def _parse_oss_path(self, oss_path: str) -> str | None:
        """解析 OSS 路径，提取 key"""
        if not oss_path:
            return None
        
        # oss://bucket/key -> key
        if oss_path.startswith("oss://"):
            parts = oss_path[6:].split("/", 1)
            return parts[1] if len(parts) > 1 else None
        
        # 直接返回 key
        return oss_path
    
    def _guess_content_type(self, filename: str) -> str:
        """根据文件名推断 MIME 类型"""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        
        content_types = {
            # 文本
            "txt": "text/plain",
            "md": "text/markdown",
            "markdown": "text/markdown",
            "json": "application/json",
            # Office
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xls": "application/vnd.ms-excel",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            # PDF
            "pdf": "application/pdf",
            # 图片
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "svg": "image/svg+xml",
        }
        
        return content_types.get(ext, "application/octet-stream")


# 全局单例
_file_storage: FileStorageService | None = None


def get_file_storage() -> FileStorageService:
    """获取文件存储服务（单例）"""
    global _file_storage
    if _file_storage is None:
        _file_storage = FileStorageService()
    return _file_storage
