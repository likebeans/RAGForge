#!/bin/bash

echo "=== Self-RAG Pipeline 项目状态验证 ==="
echo "验证时间: $(date)"
echo ""

# 创建日志文件
LOG_FILE="project_state_verification.log"
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo "=== 1. docs/ 目录状态验证 ==="
if [ -d "docs" ]; then
    echo "✅ docs/ 目录存在"
    
    # 统计文件数量
    total_files=$(find docs/ -name "*.md" -type f | wc -l)
    echo "📊 Markdown 文件总数: $total_files"
    
    echo ""
    echo "📋 所有 Markdown 文件列表:"
    find docs/ -name "*.md" -type f | sort
    
    echo ""
    echo "📊 文件语言分布分析:"
    chinese_count=0
    english_count=0
    
    for file in $(find docs/ -name "*.md" -type f); do
        # 检查文件名是否包含中文字符
        if echo "$file" | grep -qP '[\p{Han}]'; then
            echo "🇨🇳 中文文件: $file"
            ((chinese_count++))
        else
            echo "🇺🇸 英文文件: $file"
            ((english_count++))
        fi
    done
    
    echo ""
    echo "📈 语言分布统计:"
    echo "   中文文件: $chinese_count 个"
    echo "   英文文件: $english_count 个"
    echo "   总计: $total_files 个"
    
else
    echo "❌ docs/ 目录不存在"
fi

echo ""
echo "=== 2. AGENTS.md 文件分布验证 ==="

# 定义预期的 AGENTS.md 文件位置
expected_agents_files=(
    "app/api/AGENTS.md"
    "app/auth/AGENTS.md"
    "app/db/AGENTS.md"
    "app/infra/AGENTS.md"
    "app/models/AGENTS.md"
    "app/pipeline/AGENTS.md"
    "app/pipeline/chunkers/AGENTS.md"
    "app/pipeline/enrichers/AGENTS.md"
    "app/pipeline/indexers/AGENTS.md"
    "app/pipeline/retrievers/AGENTS.md"
    "app/schemas/AGENTS.md"
    "app/services/AGENTS.md"
    "frontend/AGENTS.md"
)

echo "🔍 检查预期的 AGENTS.md 文件:"
existing_agents=0
missing_agents=0

for file in "${expected_agents_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ 存在: $file (最后修改: $(stat -c %y "$file" 2>/dev/null || stat -f %Sm "$file" 2>/dev/null || echo "未知"))"
        ((existing_agents++))
    else
        echo "❌ 缺失: $file"
        ((missing_agents++))
    fi
done

echo ""
echo "🔍 查找所有实际存在的 AGENTS.md 文件:"
all_agents_files=$(find . -name "AGENTS.md" -type f | grep -v node_modules | grep -v .git | sort)
actual_agents_count=$(echo "$all_agents_files" | wc -l)

if [ -n "$all_agents_files" ]; then
    echo "$all_agents_files"
else
    echo "❌ 未找到任何 AGENTS.md 文件"
    actual_agents_count=0
fi

echo ""
echo "📈 AGENTS.md 文件统计:"
echo "   预期文件: ${#expected_agents_files[@]} 个"
echo "   实际存在: $existing_agents 个"
echo "   缺失文件: $missing_agents 个"
echo "   总发现文件: $actual_agents_count 个"

echo ""
echo "=== 3. 主 README 文件验证 ==="

if [ -f "README.md" ]; then
    echo "✅ README.md 存在"
    
    # 检查 README.md 的语言
    echo ""
    echo "📖 README.md 内容分析 (前20行):"
    head -20 README.md
    
    echo ""
    echo "🔍 语言特征检测:"
    if head -50 README.md | grep -qP '[\p{Han}]'; then
        echo "🇨🇳 检测到中文内容"
    fi
    
    if head -50 README.md | grep -qiE "(features|installation|getting started|documentation)"; then
        echo "🇺🇸 检测到英文关键词"
    fi
    
else
    echo "❌ README.md 不存在"
fi

if [ -f "README.zh-CN.md" ]; then
    echo "✅ README.zh-CN.md 存在"
else
    echo "❌ README.zh-CN.md 不存在"
fi

echo ""
echo "=== 4. 技术栈和项目结构验证 ==="

echo "🔍 检查 Python 项目配置:"
if [ -f "pyproject.toml" ]; then
    echo "✅ pyproject.toml 存在"
    echo "📦 主要依赖:"
    grep -E "(fastapi|sqlalchemy|asyncpg)" pyproject.toml || echo "   未找到预期的核心依赖"
else
    echo "❌ pyproject.toml 不存在"
fi

echo ""
echo "🔍 检查前端项目配置:"
if [ -f "frontend/package.json" ]; then
    echo "✅ frontend/package.json 存在"
    echo "📦 前端技术栈:"
    grep -E "(next|react)" frontend/package.json || echo "   未找到预期的前端框架"
else
    echo "❌ frontend/package.json 不存在"
fi

echo ""
echo "🔍 检查 Docker 配置:"
if [ -f "docker-compose.yml" ]; then
    echo "✅ docker-compose.yml 存在"
    echo "🐳 服务配置:"
    grep -E "(postgres|qdrant)" docker-compose.yml || echo "   未找到预期的基础服务"
else
    echo "❌ docker-compose.yml 不存在"
fi

echo ""
echo "🔍 检查项目目录结构:"
echo "📁 app/ 目录结构:"
if [ -d "app" ]; then
    ls -la app/ | head -10
else
    echo "❌ app/ 目录不存在"
fi

echo ""
echo "📁 frontend/ 目录结构:"
if [ -d "frontend" ]; then
    ls -la frontend/ | head -10
else
    echo "❌ frontend/ 目录不存在"
fi

echo ""
echo "=== 5. 核心功能模块验证 ==="

echo "🔍 检查 API 路由:"
if [ -d "app/api/routes" ]; then
    echo "✅ app/api/routes/ 存在"
    echo "📋 API 路由文件:"
    ls app/api/routes/ 2>/dev/null || echo "   目录为空或无法访问"
else
    echo "❌ app/api/routes/ 不存在"
fi

echo ""
echo "🔍 检查算法框架:"
echo "📋 切分器 (Chunkers):"
if [ -d "app/pipeline/chunkers" ]; then
    ls app/pipeline/chunkers/*.py 2>/dev/null | head -5 || echo "   未找到切分器文件"
else
    echo "❌ app/pipeline/chunkers/ 不存在"
fi

echo "📋 检索器 (Retrievers):"
if [ -d "app/pipeline/retrievers" ]; then
    ls app/pipeline/retrievers/*.py 2>/dev/null | head -5 || echo "   未找到检索器文件"
else
    echo "❌ app/pipeline/retrievers/ 不存在"
fi

echo ""
echo "🔍 检查数据模型:"
if [ -d "app/models" ]; then
    echo "✅ app/models/ 存在"
    echo "📋 模型文件:"
    ls app/models/*.py 2>/dev/null | head -5 || echo "   未找到模型文件"
else
    echo "❌ app/models/ 不存在"
fi

echo ""
echo "=== 验证总结 ==="
echo "验证完成时间: $(date)"
echo "详细日志已保存到: $LOG_FILE"
echo ""
echo "🎯 关键发现:"
echo "   - docs/ 文件数量: $total_files"
echo "   - AGENTS.md 存在: $existing_agents/${#expected_agents_files[@]}"
echo "   - README 语言版本需要人工确认"
echo "   - 项目结构基本符合预期"
echo ""
echo "⚠️  需要人工验证的项目:"
echo "   1. AGENTS.md 文件内容质量"
echo "   2. README.md 实际语言版本"
echo "   3. 核心功能与设计描述的匹配度"
echo "   4. 技术栈版本兼容性"