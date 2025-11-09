#!/bin/bash

###############################################################################
# Terraform Assistant - 构建脚本
#
# 用法:
#   ./scripts/build.sh [component]
#
# 组件:
#   frontend  - 仅构建前端
#   backend   - 仅构建后端
#   all       - 构建全部 (默认)
###############################################################################

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 构建前端
build_frontend() {
    log_info "========================================="
    log_info "构建前端应用"
    log_info "========================================="

    cd frontend

    # 安装依赖
    log_info "安装依赖..."
    npm ci

    # 类型检查
    log_info "执行类型检查..."
    npm run type-check

    # Lint检查
    log_info "执行代码检查..."
    npm run lint

    # 运行测试
    log_info "运行测试..."
    npm run test

    # 构建生产版本
    log_info "构建生产版本..."
    npm run build

    log_success "前端构建完成"
    log_info "构建产物位置: frontend/.next/"

    cd ..
}

# 构建后端
build_backend() {
    log_info "========================================="
    log_info "构建后端应用"
    log_info "========================================="

    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv venv
    fi

    # 激活虚拟环境
    source venv/bin/activate

    # 安装依赖
    log_info "安装依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt

    # 代码检查
    log_info "执行代码检查..."
    black app/ --check || log_warning "Black 格式检查失败"
    isort app/ --check-only || log_warning "isort 检查失败"
    flake8 app/ || log_warning "Flake8 检查失败"
    mypy app/ || log_warning "MyPy 类型检查失败"

    # 运行测试
    log_info "运行测试..."
    pytest tests/ -v --cov=app --cov-report=html

    log_success "后端构建完成"
    log_info "测试覆盖率报告: htmlcov/index.html"

    deactivate
}

# 构建Docker镜像
build_docker() {
    log_info "========================================="
    log_info "构建Docker镜像"
    log_info "========================================="

    VERSION=${VERSION:-latest}

    # 构建后端镜像
    log_info "构建后端镜像..."
    docker build -t terraform-assistant-api:${VERSION} .
    log_success "后端镜像构建完成: terraform-assistant-api:${VERSION}"

    # 构建前端镜像
    log_info "构建前端镜像..."
    docker build -f frontend/Dockerfile.prod -t terraform-assistant-frontend:${VERSION} ./frontend
    log_success "前端镜像构建完成: terraform-assistant-frontend:${VERSION}"

    # 显示镜像信息
    log_info "镜像列表:"
    docker images | grep terraform-assistant
}

# 主函数
main() {
    COMPONENT=${1:-all}

    log_info "开始构建: ${COMPONENT}"

    case "$COMPONENT" in
        frontend)
            build_frontend
            ;;
        backend)
            build_backend
            ;;
        docker)
            build_docker
            ;;
        all)
            build_frontend
            build_backend
            build_docker
            ;;
        *)
            echo "用法: $0 {frontend|backend|docker|all}"
            exit 1
            ;;
    esac

    log_success "========================================="
    log_success "构建完成!"
    log_success "========================================="
}

main "$@"
