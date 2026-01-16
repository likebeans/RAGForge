#!/bin/bash
# =============================================================================
# RAGForge 标准化部署脚本
# =============================================================================
# 用法：
#   ./deploy.sh up              # 启动生产环境（pg + opensearch）
#   ./deploy.sh up qdrant       # 启动开发环境（pg + qdrant）
#   ./deploy.sh down            # 停止服务
#   ./deploy.sh restart         # 重启服务
#   ./deploy.sh logs            # 查看日志
#   ./deploy.sh migrate         # 仅运行数据库迁移
#   ./deploy.sh status          # 查看服务状态
#   ./deploy.sh backup          # 备份数据库
#   ./deploy.sh create-tenant   # 创建新租户
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="ragforge"

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 解析参数
parse_args() {
    case "$2" in
        qdrant|Qdrant|QDRANT)
            COMPOSE_FILE="docker-compose.qdrant.yml"
            log_info "使用 Qdrant 配置: $COMPOSE_FILE"
            ;;
        *)
            COMPOSE_FILE="docker-compose.yml"
            log_info "使用默认配置: $COMPOSE_FILE (pg + opensearch)"
            ;;
    esac
}

# 检查依赖
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
}

# 等待数据库就绪
wait_for_db() {
    log_info "等待数据库就绪..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U kb -d kb &>/dev/null; then
            log_success "数据库已就绪"
            return 0
        fi
        log_info "等待中... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    log_error "数据库启动超时"
    return 1
}

# 运行数据库迁移
run_migration() {
    log_info "运行数据库迁移..."
    docker compose -f "$COMPOSE_FILE" run --rm api uv run alembic upgrade head
    log_success "数据库迁移完成"
}

# 启动服务
cmd_up() {
    parse_args "$@"
    check_dependencies
    
    log_info "构建镜像..."
    docker compose -f "$COMPOSE_FILE" build
    
    log_info "启动基础服务 (db, redis)..."
    docker compose -f "$COMPOSE_FILE" up -d db redis
    
    # 如果是默认配置，启动 opensearch
    if [ "$COMPOSE_FILE" == "docker-compose.yml" ]; then
        log_info "启动 OpenSearch..."
        docker compose -f "$COMPOSE_FILE" up -d opensearch
    fi
    
    # 如果是 qdrant 配置，启动 qdrant
    if [ "$COMPOSE_FILE" == "docker-compose.qdrant.yml" ]; then
        log_info "启动 Qdrant..."
        docker compose -f "$COMPOSE_FILE" up -d qdrant
    fi
    
    wait_for_db
    run_migration
    
    log_info "启动 API 服务..."
    docker compose -f "$COMPOSE_FILE" up -d api
    
    log_info "启动前端..."
    docker compose -f "$COMPOSE_FILE" up -d frontend
    
    log_success "所有服务已启动！"
    echo ""
    echo "=========================================="
    echo "  服务地址："
    echo "    - API:      http://localhost:8020"
    echo "    - 前端:     http://localhost:3003"
    echo "    - 健康检查: http://localhost:8020/health"
    echo "=========================================="
}

# 停止服务
cmd_down() {
    parse_args "$@"
    log_info "停止服务..."
    docker compose -f "$COMPOSE_FILE" down
    log_success "服务已停止"
}

# 重启服务
cmd_restart() {
    parse_args "$@"
    log_info "重启服务..."
    docker compose -f "$COMPOSE_FILE" restart
    log_success "服务已重启"
}

# 查看日志
cmd_logs() {
    parse_args "$@"
    docker compose -f "$COMPOSE_FILE" logs -f --tail 100 api
}

# 仅运行迁移
cmd_migrate() {
    parse_args "$@"
    check_dependencies
    
    log_info "启动数据库..."
    docker compose -f "$COMPOSE_FILE" up -d db
    wait_for_db
    run_migration
}

# 查看状态
cmd_status() {
    parse_args "$@"
    docker compose -f "$COMPOSE_FILE" ps
}

# 备份数据库
cmd_backup() {
    parse_args "$@"
    local backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
    
    log_info "备份数据库到 $backup_file..."
    docker compose -f "$COMPOSE_FILE" exec -T db pg_dump -U kb kb > "$backup_file"
    log_success "备份完成: $backup_file"
}

# 创建租户
cmd_create_tenant() {
    local tenant_name="${2:-default-tenant}"
    local admin_token="${ADMIN_TOKEN:-ragforge-admin-2024}"
    
    log_info "创建租户: $tenant_name"
    
    response=$(curl -s -X POST http://localhost:8020/admin/tenants \
        -H "X-Admin-Token: $admin_token" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"$tenant_name\"}")
    
    if echo "$response" | grep -q "initial_api_key"; then
        log_success "租户创建成功！"
        echo ""
        echo "=========================================="
        echo "  租户信息："
        echo "$response" | python3 -m json.tool
        echo "=========================================="
    else
        log_error "创建失败: $response"
    fi
}

# 主入口
main() {
    case "$1" in
        up)
            cmd_up "$@"
            ;;
        down)
            cmd_down "$@"
            ;;
        restart)
            cmd_restart "$@"
            ;;
        logs)
            cmd_logs "$@"
            ;;
        migrate)
            cmd_migrate "$@"
            ;;
        status)
            cmd_status "$@"
            ;;
        backup)
            cmd_backup "$@"
            ;;
        create-tenant)
            cmd_create_tenant "$@"
            ;;
        *)
            echo "RAGForge 部署脚本"
            echo ""
            echo "用法: $0 <命令> [选项]"
            echo ""
            echo "命令:"
            echo "  up [qdrant]      启动服务（默认 pg+opensearch，可选 qdrant）"
            echo "  down             停止服务"
            echo "  restart          重启服务"
            echo "  logs             查看 API 日志"
            echo "  migrate          仅运行数据库迁移"
            echo "  status           查看服务状态"
            echo "  backup           备份数据库"
            echo "  create-tenant    创建新租户"
            echo ""
            echo "示例:"
            echo "  $0 up                 # 启动生产环境 (pg + opensearch)"
            echo "  $0 up qdrant          # 启动开发环境 (pg + qdrant)"
            echo "  $0 logs               # 查看日志"
            echo "  $0 create-tenant test # 创建名为 test 的租户"
            ;;
    esac
}

main "$@"
