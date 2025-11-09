#!/bin/bash

###############################################################################
# Terraform Assistant - 生产环境部署脚本
#
# 用法:
#   ./scripts/deploy.sh [environment]
#
# 环境:
#   development - 开发环境
#   staging     - 测试环境
#   production  - 生产环境
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
Terraform Assistant 部署脚本

用法:
    ./scripts/deploy.sh [environment] [options]

环境:
    development     开发环境
    staging         测试环境
    production      生产环境 (默认)

选项:
    --skip-build    跳过镜像构建
    --skip-db       跳过数据库迁移
    --help          显示此帮助信息

示例:
    ./scripts/deploy.sh production
    ./scripts/deploy.sh staging --skip-build
EOF
}

# 检查前置条件
check_prerequisites() {
    log_info "检查前置条件..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi

    log_success "前置条件检查通过"
}

# 加载环境变量
load_environment() {
    local env=$1
    local env_file=".env.${env}"

    log_info "加载 ${env} 环境配置..."

    if [ ! -f "$env_file" ]; then
        log_error "环境配置文件 ${env_file} 不存在"
        log_info "请从 .env.example 复制并配置"
        exit 1
    fi

    export $(cat "$env_file" | grep -v '^#' | xargs)
    log_success "环境配置加载成功"
}

# 构建镜像
build_images() {
    if [ "$SKIP_BUILD" = true ]; then
        log_warning "跳过镜像构建"
        return
    fi

    log_info "构建 Docker 镜像..."

    # 构建后端镜像
    log_info "构建后端镜像..."
    docker build -t terraform-assistant-api:${VERSION:-latest} .

    # 构建前端镜像
    log_info "构建前端镜像..."
    docker build -f frontend/Dockerfile.prod -t terraform-assistant-frontend:${VERSION:-latest} ./frontend

    log_success "镜像构建完成"
}

# 停止现有服务
stop_services() {
    log_info "停止现有服务..."
    docker-compose -f docker-compose.${ENVIRONMENT}.yml down || true
    log_success "服务已停止"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    docker-compose -f docker-compose.${ENVIRONMENT}.yml up -d
    log_success "服务启动成功"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T api curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
            log_success "API 服务就绪"
            break
        fi

        log_info "等待 API 服务... (${attempt}/${max_attempts})"
        sleep 2
        attempt=$((attempt + 1))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "API 服务启动超时"
        exit 1
    fi
}

# 运行数据库迁移
run_migrations() {
    if [ "$SKIP_DB" = true ]; then
        log_warning "跳过数据库迁移"
        return
    fi

    log_info "运行数据库迁移..."
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T api alembic upgrade head
    log_success "数据库迁移完成"
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    docker-compose -f docker-compose.${ENVIRONMENT}.yml ps
}

# 显示访问信息
show_access_info() {
    log_success "========================================="
    log_success "部署完成!"
    log_success "========================================="
    echo ""
    log_info "访问地址:"

    if [ "$ENVIRONMENT" = "production" ]; then
        echo "  前端: https://yourdomain.com"
        echo "  API:  https://api.yourdomain.com"
        echo "  文档: https://api.yourdomain.com/docs"
    else
        echo "  前端: http://localhost:3000"
        echo "  API:  http://localhost:8000"
        echo "  文档: http://localhost:8000/docs"
    fi

    echo ""
    log_info "监控面板:"
    echo "  Prometheus: http://localhost:9090"
    echo "  Grafana:    http://localhost:3001"
    echo ""
    log_info "查看日志:"
    echo "  docker-compose -f docker-compose.${ENVIRONMENT}.yml logs -f"
}

# 备份数据
backup_data() {
    log_info "备份数据..."

    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # 备份数据库
    log_info "备份数据库..."
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T postgres pg_dump -U postgres terraform_assistant > "${backup_dir}/database.sql"

    # 备份Redis数据
    log_info "备份Redis数据..."
    docker-compose -f docker-compose.${ENVIRONMENT}.yml exec -T redis redis-cli --rdb "${backup_dir}/redis.rdb" SAVE

    log_success "数据备份完成: ${backup_dir}"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    # 检查API
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        log_success "API 健康检查通过"
    else
        log_error "API 健康检查失败"
        return 1
    fi

    # 检查前端
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_success "前端健康检查通过"
    else
        log_error "前端健康检查失败"
        return 1
    fi

    log_success "健康检查完成"
}

# 清理旧镜像
cleanup_old_images() {
    log_info "清理旧镜像..."
    docker image prune -f
    log_success "清理完成"
}

# 主函数
main() {
    # 默认值
    ENVIRONMENT="${1:-production}"
    SKIP_BUILD=false
    SKIP_DB=false

    # 解析参数
    shift || true
    while [ $# -gt 0 ]; do
        case "$1" in
            --skip-build)
                SKIP_BUILD=true
                ;;
            --skip-db)
                SKIP_DB=true
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done

    log_info "========================================="
    log_info "开始部署到 ${ENVIRONMENT} 环境"
    log_info "========================================="

    # 执行部署步骤
    check_prerequisites
    load_environment "$ENVIRONMENT"

    # 生产环境需要确认
    if [ "$ENVIRONMENT" = "production" ]; then
        read -p "确认要部署到生产环境吗? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log_warning "部署已取消"
            exit 0
        fi

        # 生产环境自动备份
        backup_data
    fi

    build_images
    stop_services
    start_services
    wait_for_services
    run_migrations
    health_check
    check_services
    cleanup_old_images
    show_access_info

    log_success "部署流程完成!"
}

# 执行主函数
main "$@"
