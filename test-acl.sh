#!/bin/bash

# RAGForge 权限测试脚本
BASE_URL="http://192.168.168.105:8020"
ADMIN_KEY="kb_sk_yvmEUfH-E4R9CgNKxeo_9m2L4wzHcy8bxI3BSo0XxcQ"

echo "========================================"
echo "1. 检查现有知识库"
echo "========================================"
curl -s -X GET "$BASE_URL/v1/knowledge-bases" \
  -H "Authorization: Bearer $ADMIN_KEY" | jq .

echo ""
echo "========================================"
echo "2. 创建测试知识库"
echo "========================================"
KB_RESULT=$(curl -s -X POST "$BASE_URL/v1/knowledge-bases" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "ACL测试库", "description": "用于测试文档级权限控制"}')
echo "$KB_RESULT" | jq .
KB_ID=$(echo "$KB_RESULT" | jq -r '.id // empty')

if [ -z "$KB_ID" ]; then
  echo "知识库创建失败或已存在，尝试获取现有的..."
  KB_ID=$(curl -s -X GET "$BASE_URL/v1/knowledge-bases" \
    -H "Authorization: Bearer $ADMIN_KEY" | jq -r '.items[] | select(.name=="ACL测试库") | .id')
fi

echo "知识库ID: $KB_ID"
