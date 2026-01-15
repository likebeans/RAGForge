#!/bin/bash
#
# RAG Pipeline 生产环境恢复脚本
# 用途: 从备份恢复 PostgreSQL、Qdrant 和配置文件
# 使用: ./scripts/restore.sh <备份日期>
# 示例: ./scripts/restore.sh 20260115_020000
#

set -e

# ==================== 配置 ====================
BACKUP_BASE_DIR="${BACKUP_DIR:-/backup/rag-pipeline}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 容器名称
POSTGRES_CONTAINER="rag_kb_postgres"
REDIS_CONTAINER="rag_kb_redis"

# 日志文件
LOG_FILE="/var/log/rag-pipeline-restore.log"

# ==================== 函数 ====================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "❌ 错误: $1"
    exit 1
}

usage() {
    echo "用法: $0 <备份日期>"
    echo ""
    echo "示例:"
    echo "  $0 20260115_020000"
    echo ""
    echo "可用的备份:"
    ls -1 "$BACKUP_BASE_DIR"/postgres/kb_*.sql.gz 2>/dev/null | \
        sed 's/.*kb_\(.*\)\.sql\.gz/  \1/' || echo "  无可用备份"
    exit 1
}

confirm_restore() {
    echo ""
    echo "⚠️  警告: 恢复操作将覆盖现有数据！"
    echo ""
    echo "备份时间: $BACKUP_DATE"
    echo "恢复内容:"
    echo "  - PostgreSQL 数据库"
    echo "  - Qdrant 向量数据"
    echo "  - 配置文件"
    echo ""
    read -p "确认继续恢复? (输入 YES 确认): " confirm
    
    if [ "$confirm" != "YES" ]; then
        log "❌ 恢复已取消"
        exit 1
    fi
}

backup_current_data() {
    log "备份当前数据（以防恢复失败）..."
    local emergency_backup_dir="$BACKUP_BASE_DIR/emergency_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$emergency_backup_dir"
    
    # 备份当前 PostgreSQL
    if docker ps --format '{{.Names}}' | grep -q "$POSTGRES_CONTAINER"; then
        docker exec "$POSTGRES_CONTAINER" pg_dump -U kb kb | gzip > \
            "$emergency_backup_dir/kb_emergency.sql.gz" || log "⚠️  紧急备份失败"
    fi
    
    # 备份当前 Qdrant
    if [ -d "$PROJECT_DIR/qdrant_data" ]; then
        tar -czf "$emergency_backup_dir/qdrant_emergency.tar.gz" \
            -C "$PROJECT_DIR" qdrant_data/ || log "⚠️  Qdrant 紧急备份失败"
    fi
    
    log "✅ 紧急备份已保存到: $emergency_backup_dir"
}

# ==================== 主逻辑 ====================

# 检查参数
if [ $# -ne 1 ]; then
    usage
fi

BACKUP_DATE="$1"
POSTGRES_BACKUP="$BACKUP_BASE_DIR/postgres/kb_${BACKUP_DATE}.sql.gz"
QDRANT_BACKUP="$BACKUP_BASE_DIR/qdrant/qdrant_${BACKUP_DATE}.tar.gz"
CONFIG_DIR="$BACKUP_BASE_DIR/config"

log "========== 开始恢复 =========="
log "备份日期: $BACKUP_DATE"

# 检查备份文件是否存在
if [ ! -f "$POSTGRES_BACKUP" ]; then
    error_exit "PostgreSQL 备份不存在: $POSTGRES_BACKUP"
fi

if [ ! -f "$QDRANT_BACKUP" ]; then
    log "⚠️  Qdrant 备份不存在: $QDRANT_BACKUP"
fi

# 确认恢复
confirm_restore

# 创建紧急备份
backup_current_data

# 1. 停止服务
log "停止服务..."
cd "$PROJECT_DIR"
docker-compose stop api frontend || log "⚠️  停止服务失败或服务未运行"

# 2. 恢复 PostgreSQL
log "恢复 PostgreSQL 数据库..."
if docker ps --format '{{.Names}}' | grep -q "$POSTGRES_CONTAINER"; then
    # 清空现有数据库
    docker exec "$POSTGRES_CONTAINER" psql -U kb -d postgres -c "DROP DATABASE IF EXISTS kb;"
    docker exec "$POSTGRES_CONTAINER" psql -U kb -d postgres -c "CREATE DATABASE kb;"
    
    # 恢复备份
    gunzip -c "$POSTGRES_BACKUP" | docker exec -i "$POSTGRES_CONTAINER" psql -U kb -d kb
    
    log "✅ PostgreSQL 恢复完成"
else
    error_exit "PostgreSQL 容器未运行"
fi

# 3. 恢复 Qdrant
if [ -f "$QDRANT_BACKUP" ]; then
    log "恢复 Qdrant 向量数据..."
    
    # 停止 Qdrant
    docker-compose stop qdrant
    
    # 删除旧数据
    if [ -d "$PROJECT_DIR/qdrant_data" ]; then
        mv "$PROJECT_DIR/qdrant_data" "$PROJECT_DIR/qdrant_data.old_$(date +%Y%m%d_%H%M%S)"
    fi
    
    # 解压备份
    tar -xzf "$QDRANT_BACKUP" -C "$PROJECT_DIR"
    
    log "✅ Qdrant 恢复完成"
fi

# 4. 恢复配置文件（可选）
log "恢复配置文件..."
if [ -f "$CONFIG_DIR/.env_${BACKUP_DATE}" ]; then
    read -p "恢复 .env 文件? (y/N): " restore_env
    if [ "$restore_env" = "y" ] || [ "$restore_env" = "Y" ]; then
        cp "$PROJECT_DIR/.env" "$PROJECT_DIR/.env.old_$(date +%Y%m%d_%H%M%S)"
        cp "$CONFIG_DIR/.env_${BACKUP_DATE}" "$PROJECT_DIR/.env"
        log "✅ .env 文件已恢复"
    fi
fi

# 5. 重启服务
log "重启服务..."
docker-compose up -d

# 6. 等待服务就绪
log "等待服务启动..."
sleep 30

# 7. 健康检查
log "执行健康检查..."
for i in {1..10}; do
    if curl -sf http://localhost:8020/health > /dev/null 2>&1; then
        log "✅ API 健康检查通过"
        break
    fi
    
    if [ $i -eq 10 ]; then
        error_exit "API 健康检查失败，请检查日志"
    fi
    
    log "等待 API 启动... ($i/10)"
    sleep 5
done

log "========== 恢复完成 =========="
log "恢复时间: $(date)"
log "备份来源: $BACKUP_DATE"
log ""
log "下一步:"
log "1. 验证数据完整性"
log "2. 测试核心功能"
log "3. 检查日志是否有异常"
log ""
log "如需回滚，紧急备份位于: $BACKUP_BASE_DIR/emergency_*"

exit 0
