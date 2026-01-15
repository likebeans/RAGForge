class KBConfigError(Exception):
    """知识库配置错误"""


class EmbeddingError(Exception):
    """向量化错误"""


class VectorStoreError(Exception):
    """向量存储错误"""


class BM25Error(Exception):
    """BM25 存储错误"""


class LLMError(Exception):
    """LLM 调用错误"""


class RerankError(Exception):
    """重排模型错误"""


class IngestionError(Exception):
    """文档摄取错误"""


class RetrievalError(Exception):
    """检索错误"""


class ACLError(Exception):
    """权限控制错误"""
