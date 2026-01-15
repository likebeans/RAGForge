# 向量维度不匹配问题修复说明

## 问题描述

在使用不同 embedding 模型时，系统会出现向量维度不匹配的警告：

```
WARNING [5282870d] app.infra.vector_store - 追加向量字段失败 kb_shared:vec_qwen_qwen3_embedding_8b_4096 - collection kb_shared default vector dim 1024 != requested 4096
WARNING [5282870d] app.infra.vector_store - kb_shared 向量字段不可用，回退到 kb_shared_4096: collection kb_shared default vector dim 1024 != requested 4096
```

## 问题原因

1. **配置不一致**：系统默认配置使用 1024 维的 embedding 模型（如 `bge-m3`），但知识库配置中使用了 4096 维的模型（如 `Qwen/Qwen3-Embedding-8B`）
2. **向量字段冲突**：当向量库中已存在默认向量字段（1024维）时，尝试添加不同维度的向量字段会失败
3. **回退机制不够智能**：系统简单地回退到按维度分离的 collection，而不是在同一 collection 中支持多维度向量字段

## 解决方案

### 1. 优化向量字段处理逻辑

修改 `_ensure_vector_field` 方法，使其能够智能处理不同维度的向量字段：

- **维度匹配时复用**：如果默认向量字段的维度与请求的维度匹配，直接复用
- **维度不匹配时创建新字段**：不抛出异常，而是创建新的命名向量字段
- **字段名冲突处理**：自动生成不冲突的字段名

### 2. 改进向量字段命名

优化 `get_vector_field_name` 函数：

- **简化常见模型**：对于 1024 维的常见模型（如 `bge-m3`），使用简化名称
- **包含维度信息**：对于非标准维度，在字段名中包含维度信息
- **避免冲突**：确保不同模型和维度的组合生成唯一的字段名

### 3. 向量字段命名规则

| 模型 | 维度 | 字段名 | 说明 |
|------|------|--------|------|
| `bge-m3` | 1024 | `vec_bge_m3` | 常见模型简化名称 |
| `text-embedding-v3` | 1024 | `vec_text_embedding_v3` | 常见模型简化名称 |
| `Qwen/Qwen3-Embedding-8B` | 4096 | `vec_qwen_qwen3_embedding_8b_4096` | 包含维度信息 |
| `text-embedding-3-large` | 3072 | `vec_text_embedding_3_large_3072` | 包含维度信息 |

## 修复效果

### 修复前
```
WARNING - 追加向量字段失败 kb_shared:vec_qwen_qwen3_embedding_8b_4096 - collection kb_shared default vector dim 1024 != requested 4096
WARNING - kb_shared 向量字段不可用，回退到 kb_shared_4096
```

### 修复后
```
INFO - 为 kb_shared 追加向量字段 vec_qwen_qwen3_embedding_8b_4096 (dim=4096)
INFO - 检索使用知识库配置: siliconflow/Qwen/Qwen3-Embedding-8B
```

## 技术细节

### 多维度向量字段支持

Qdrant 支持在同一个 collection 中使用多个命名向量字段，每个字段可以有不同的维度：

```python
# Collection 配置示例
vectors_config = {
    "": VectorParams(size=1024, distance="Cosine"),  # 默认字段
    "vec_qwen_qwen3_embedding_8b_4096": VectorParams(size=4096, distance="Cosine"),
    "vec_text_embedding_3_large_3072": VectorParams(size=3072, distance="Cosine"),
}
```

### 向量存储和检索

- **存储时**：根据 embedding 模型自动选择正确的向量字段
- **检索时**：使用与入库时相同的向量字段，确保向量空间一致性
- **兼容性**：保持与现有数据的完全兼容

## 最佳实践

### 1. 配置一致性

确保系统配置与知识库配置的一致性：

```bash
# 环境变量配置
EMBEDDING_PROVIDER=siliconflow
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
EMBEDDING_DIM=4096
```

### 2. 知识库配置

在知识库配置中明确指定 embedding 模型：

```json
{
  "embedding": {
    "provider": "siliconflow",
    "model": "Qwen/Qwen3-Embedding-8B"
  }
}
```

### 3. 模型切换

如需切换 embedding 模型：

1. **新知识库**：直接使用新模型配置
2. **现有知识库**：需要重新入库或使用混合检索策略

## 相关文件

- `app/infra/vector_store.py` - 向量存储核心逻辑
- `app/services/query.py` - 检索服务
- `app/config.py` - 配置管理
- `app/infra/embeddings.py` - Embedding 生成

## 测试验证

修复已通过以下测试：

1. ✅ 向量字段维度不匹配处理
2. ✅ 多维度向量字段共存
3. ✅ 向量字段名称生成
4. ✅ 维度映射和动态注册
5. ✅ 向后兼容性

这个修复确保了系统能够灵活处理不同维度的 embedding 模型，避免了维度不匹配导致的警告和回退问题。