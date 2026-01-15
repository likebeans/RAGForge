#!/bin/bash
#
# RAG Pipeline 生产环境备份脚本
# 用途: 自动备份 PostgreSQL、Qdrant 和配置文件
# 使用: ./scripts/backup.sh
# 定时任务: 0 2 * * * /path/to/scripts/backup.sh
#

set -e

# ==================== 配置 ====================
BACKUP_BASE_DIR="${BACKUP_DIR:-/backup/rag-pipeline}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 备份子目录
POSTGRES_BACKUP_DIR="$BACKUP_BASE_DIR/postgres"
QDRANT_BACKUP_DIR="$BACKUP_BASE_DIR/qdrant"
CONFIG_BACKUP_DIR="$BACKUP_BASE_DIR/config"

# 容器名称（根据实际情况修改）
POSTGRES_CONTAINER="rag_kb_postgres"
REDIS_CONTAINER="rag_kb_redis"

# 日志文件
LOG_FILE="/var/log/rag-pipeline-backup.log"

# ==================== 函数 ====================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "❌ 错误: $1"
    exit 1
}

check_disk_space() {
    local required_space_gb=10
    local available_space=$(df -BG "$BACKUP_BASE_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    
    if [ "$available_space" -lt "$required_space_gb" ]; then
        error_exit "磁盘空间不足! 需要至少 ${required_space_gb}GB，当前可用: ${available_space}GB"
    fi
}

# ==================== 主逻辑 ====================

log "========== 开始备份 =========="

# 1. 创建备份目录
log "创建备份目录..."
mkdir -p "$POSTGRES_BACKUP_DIR" "$QDRANT_BACKUP_DIR" "$CONFIG_BACKUP_DIR"

# 2. 检查磁盘空间
log "检查磁盘空间..."
check_disk_space

# 3. 备份 PostgreSQL
log "备份 PostgreSQL..."
if docker ps --format '{{.Names}}' | grep -q "$POSTGRES_CONTAINER"; then
    docker exec "$POSTGRES_CONTAINER" pg_dump -U kb kb | gzip > \
        "$POSTGRES_BACKUP_DIR/kb_${DATE}.sql.gz" || error_exit "PostgreSQL 备份失败"
    log "✅ PostgreSQL 备份完成: kb_${DATE}.sql.gz"
else
    log "⚠️  PostgreSQL 容器未运行，跳过备份"
fi

# 4. 备份 Qdrant
log "备份 Qdrant..."
if [ -d "$PROJECT_DIR/qdrant_data" ]; then
    tar -czf "$QDRANT_BACKUP_DIR/qdrant_${DATE}.tar.gz" \
        -C "$PROJECT_DIR" qdrant_data/ || error_exit "Qdrant 备份失败"
    log "✅ Qdrant 备份完成: qdrant_${DATE}.tar.gz"
else
    log "⚠️  Qdrant 数据目录不存在，跳过备份"
fi

# 5. 备份 Redis (AOF 文件)
log "备份 Redis..."
if docker ps --format '{{.Names}}' | grep -q "$REDIS_CONTAINER"; then
    docker exec "$REDIS_CONTAINER" redis-cli BGSAVE
    sleep 5
    docker cp "$REDIS_CONTAINER:/data/dump.rdb" \
        "$BACKUP_BASE_DIR/redis_${DATE}.rdb" 2>/dev/null || log "⚠️  Redis 备份失败或无数据"
    if [ -f "$BACKUP_BASE_DIR/redis_${DATE}.rdb" ]; then
        log "✅ Redis 备份完成: redis_${DATE}.rdb"
    fi
else
    log "⚠️  Redis 容器未运行，跳过备份"
fi

# 6. 备份配置文件
log "备份配置文件..."
if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "$CONFIG_BACKUP_DIR/.env_${DATE}"
    log "✅ .env 备份完成"
fi

if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
    cp "$PROJECT_DIR/docker-compose.yml" "$CONFIG_BACKUP_DIR/docker-compose_${DATE}.yml"
    log "✅ docker-compose.yml 备份完成"
fi

if [ -f "$PROJECT_DIR/alembic.ini" ]; then
    cp "$PROJECT_DIR/alembic.ini" "$CONFIG_BACKUP_DIR/alembic_${DATE}.ini"
    log "✅ alembic.ini 备份完成"
fi

# 7. 创建备份清单
log "生成备份清单..."
cat > "$BACKUP_BASE_DIR/backup_${DATE}.manifest" << EOF
备份时间: $(date)
备份目录: $BACKUP_BASE_DIR

文件列表:
PostgreSQL: $(ls -lh "$POSTGRES_BACKUP_DIR/kb_${DATE}.sql.gz" 2>/dev/null || echo "未备份")
Qdrant:     $(ls -lh "$QDRANT_BACKUP_DIR/qdrant_${DATE}.tar.gz" 2>/dev/null || echo "未备份")
Redis:      $(ls -lh "$BACKUP_BASE_DIR/redis_${DATE}.rdb" 2>/dev/null || echo "未备份")
配置文件:   $(ls -1 "$CONFIG_BACKUP_DIR"/*_${DATE}* 2>/dev/null | wc -l) 个

磁盘使用:
$(df -h "$BACKUP_BASE_DIR")
EOF

# 8. 清理旧备份
log "清理 ${RETENTION_DAYS} 天前的旧备份..."
find "$BACKUP_BASE_DIR" -type f -mtime +$RETENTION_DAYS -delete
log "✅ 旧备份清理完成"

# 9. 生成备份统计
BACKUP_SIZE=$(du -sh "$BACKUP_BASE_DIR" | cut -f1)
BACKUP_COUNT=$(find "$BACKUP_BASE_DIR" -type f -name "*.gz" -o -name "*.rdb" | wc -l)

log "========== 备份完成 =========="
log "备份位置: $BACKUP_BASE_DIR"
log "备份大小: $BACKUP_SIZE"
log "备份文件数: $BACKUP_COUNT"
log "保留天数: $RETENTION_DAYS"

# 10. 发送通知（可选，需要配置 mail 或其他通知方式）
if command -v mail &> /dev/null; then
    echo "RAG Pipeline 备份完成

备份时间: $(date)
备份大小: $BACKUP_SIZE
备份文件数: $BACKUP_COUNT

详情请查看: $BACKUP_BASE_DIR/backup_${DATE}.manifest
" | mail -s "RAG Pipeline 备份成功 - $DATE" "${ADMIN_EMAIL:-admin@localhost}"
fi

log "✅ 所有备份任务完成"
exit 0
