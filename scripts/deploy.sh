#!/bin/bash

# 股票预测系统部署脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_info "Docker环境检查通过"
}

# 检查端口占用
check_ports() {
    local ports=("5000" "5432" "6379" "80" "443" "9090" "3001")
    
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_warn "端口 $port 已被占用"
        fi
    done
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p logs
    mkdir -p ssl
    mkdir -p scripts
    mkdir -p grafana/provisioning/datasources
    mkdir -p grafana/provisioning/dashboards
    
    log_info "目录创建完成"
}

# 生成自签名SSL证书
generate_ssl_cert() {
    if [ ! -f "ssl/cert.pem" ]; then
        log_info "生成自签名SSL证书..."
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout ssl/key.pem \
            -out ssl/cert.pem \
            -subj "/C=CN/ST=State/L=City/O=Organization/CN=localhost"
        
        log_info "SSL证书生成完成"
    else
        log_info "SSL证书已存在，跳过生成"
    fi
}

# 初始化数据库脚本
create_init_sql() {
    if [ ! -f "scripts/init.sql" ]; then
        log_info "创建数据库初始化脚本..."
        
        cat > scripts/init.sql << 'EOF'
-- 创建数据库初始化脚本
-- 基础表结构会在应用启动时自动创建

-- 设置时区
SET timezone = 'UTC';

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 创建监控用户
CREATE USER monitoring WITH PASSWORD 'monitoring123';
GRANT pg_read_all_stats TO monitoring;

COMMIT;
EOF
        
        log_info "数据库初始化脚本创建完成"
    else
        log_info "数据库初始化脚本已存在，跳过创建"
    fi
}

# 构建Docker镜像
build_images() {
    log_info "构建Docker镜像..."
    
    docker-compose build --no-cache
    
    log_info "Docker镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 先启动基础服务
    docker-compose up -d postgres redis
    
    # 等待数据库启动
    log_info "等待数据库启动..."
    sleep 10
    
    # 启动应用服务
    docker-compose up -d app
    
    # 等待应用启动
    log_info "等待应用启动..."
    sleep 15
    
    # 启动其他服务
    docker-compose up -d nginx prometheus grafana
    
    log_info "所有服务启动完成"
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    # 检查应用健康状态
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        log_info "应用服务运行正常"
    else
        log_error "应用服务启动失败"
        return 1
    fi
    
    # 检查数据库连接
    if docker-compose exec -T postgres pg_isready -U stockuser -d stock_prediction > /dev/null 2>&1; then
        log_info "数据库服务运行正常"
    else
        log_error "数据库服务启动失败"
        return 1
    fi
    
    # 检查Redis连接
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_info "Redis服务运行正常"
    else
        log_error "Redis服务启动失败"
        return 1
    fi
    
    log_info "所有服务检查通过"
}

# 显示访问信息
show_access_info() {
    log_info "部署完成！访问信息："
    echo ""
    echo "🌐 应用访问地址:"
    echo "   HTTP:  http://localhost"
    echo "   HTTPS: https://localhost"
    echo ""
    echo "📊 监控面板:"
    echo "   Prometheus: http://localhost:9090"
    echo "   Grafana:    http://localhost:3001 (admin/REDACTED)"
    echo ""
    echo "🔧 管理命令:"
    echo "   查看日志:   docker-compose logs -f app"
    echo "   重启服务:   docker-compose restart app"
    echo "   停止服务:   docker-compose down"
    echo ""
}

# 主函数
main() {
    log_info "开始部署股票预测系统..."
    
    # 检查环境
    check_docker
    check_ports
    
    # 准备环境
    create_directories
    generate_ssl_cert
    create_init_sql
    
    # 构建和启动
    build_images
    start_services
    
    # 检查服务
    if check_services; then
        show_access_info
        log_info "部署成功！"
    else
        log_error "部署失败，请检查日志"
        docker-compose logs
        exit 1
    fi
}

# 命令行参数处理
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log_info "停止所有服务..."
        docker-compose down
        log_info "服务已停止"
        ;;
    "restart")
        log_info "重启所有服务..."
        docker-compose restart
        log_info "服务已重启"
        ;;
    "logs")
        docker-compose logs -f "${2:-app}"
        ;;
    "status")
        docker-compose ps
        ;;
    "clean")
        log_info "清理所有容器和镜像..."
        docker-compose down -v --rmi all
        log_info "清理完成"
        ;;
    *)
        echo "用法: $0 {deploy|stop|restart|logs|status|clean}"
        echo "  deploy  - 部署应用"
        echo "  stop    - 停止所有服务"
        echo "  restart - 重启所有服务"
        echo "  logs    - 查看日志 (默认app服务)"
        echo "  status  - 查看服务状态"
        echo "  clean   - 清理所有容器和镜像"
        exit 1
        ;;
esac
