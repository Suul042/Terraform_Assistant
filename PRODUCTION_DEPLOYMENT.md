# Terraform Assistant - 生产环境部署指南

## 📋 目录
- [前置要求](#前置要求)
- [快速部署](#快速部署)
- [前端构建](#前端构建)
- [后端构建](#后端构建)
- [Docker部署](#docker部署)
- [环境配置](#环境配置)
- [性能优化](#性能优化)
- [监控和日志](#监控和日志)

---

## 🔧 前置要求

### 系统要求
- **操作系统**: Linux (Ubuntu 20.04+ / CentOS 8+ 推荐)
- **CPU**: 4核以上
- **内存**: 8GB以上
- **磁盘**: 50GB以上 SSD

### 软件依赖
- Docker 24.0+
- Docker Compose 2.20+
- Node.js 18+ (本地构建时)
- Python 3.11+ (本地构建时)
- Git

### 域名和SSL证书
- 已配置的域名
- SSL证书 (推荐使用 Let's Encrypt)

---

## ⚡ 快速部署

### 方式一：使用一键部署脚本
```bash
# 克隆仓库
git clone https://github.com/your-org/terraform-assistant.git
cd terraform-assistant

# 配置环境变量
cp .env.example .env.production
vim .env.production  # 编辑配置

# 执行一键部署脚本
chmod +x scripts/deploy.sh
./scripts/deploy.sh production
```

### 方式二：使用Docker Compose
```bash
# 构建并启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 🎨 前端构建

### 本地构建方式

#### 1. 安装依赖
```bash
cd frontend
npm install
```

#### 2. 配置生产环境变量
创建 `frontend/.env.production`:
```env
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
NODE_ENV=production
```

#### 3. 构建生产版本
```bash
npm run build
```

#### 4. 测试生产构建
```bash
npm run start
# 访问 http://localhost:3000
```

### Docker构建方式

使用专门的前端Dockerfile构建:
```bash
cd frontend
docker build -f Dockerfile.prod -t terraform-assistant-frontend:latest .

# 运行容器
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com \
  terraform-assistant-frontend:latest
```

### 构建产物
- 位置: `frontend/.next/`
- 静态资源: `frontend/.next/static/`
- 服务端渲染: `frontend/.next/server/`

---

## 🔨 后端构建

### 本地构建方式

#### 1. 创建虚拟环境
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

#### 2. 安装依赖
```bash
pip install -r requirements.txt
```

#### 3. 配置生产环境变量
创建 `.env.production`:
```env
APP_NAME=Terraform Assistant
DEBUG=false
SECRET_KEY=your-production-secret-key

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/terraform_assistant
REDIS_URL=redis://localhost:6379

OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview

CORS_ORIGINS=["https://yourdomain.com"]
ALLOWED_HOSTS=["yourdomain.com"]
```

#### 4. 数据库迁移
```bash
# 运行数据库迁移
alembic upgrade head

# 初始化基础数据（可选）
python scripts/init_data.py
```

#### 5. 启动生产服务器
```bash
# 使用 Gunicorn (推荐)
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -

# 或使用 Uvicorn
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

### Docker构建方式

使用生产Dockerfile:
```bash
# 构建镜像
docker build -t terraform-assistant-api:latest .

# 运行容器
docker run -p 8000:8000 \
  --env-file .env.production \
  terraform-assistant-api:latest
```

---

## 🐳 Docker部署

### 完整的生产环境部署

#### 1. 准备配置文件

**docker-compose.prod.yml** (已创建在项目根目录)

#### 2. 构建所有镜像
```bash
# 构建所有服务
docker-compose -f docker-compose.prod.yml build

# 或单独构建
docker-compose -f docker-compose.prod.yml build api
docker-compose -f docker-compose.prod.yml build frontend
```

#### 3. 启动服务
```bash
# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

#### 4. 初始化数据库
```bash
# 进入API容器
docker-compose -f docker-compose.prod.yml exec api bash

# 运行迁移
alembic upgrade head

# 退出容器
exit
```

#### 5. 查看日志
```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f frontend
```

---

## ⚙️ 环境配置

### 生产环境变量清单

创建 `.env.production`:
```env
# ===================
# 应用配置
# ===================
APP_NAME=Terraform Assistant
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=your-super-secret-key-min-32-chars

# ===================
# 数据库配置
# ===================
DATABASE_URL=postgresql+asyncpg://postgres:strongpassword@postgres:5432/terraform_assistant

# ===================
# Redis配置
# ===================
REDIS_URL=redis://:redispassword@redis:6379

# ===================
# OpenAI配置
# ===================
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview

# ===================
# 文档URL
# ===================
AWS_DOCS_BASE_URL=https://registry.terraform.io/providers/hashicorp/aws/latest/docs
AZURE_DOCS_BASE_URL=https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs
GCP_DOCS_BASE_URL=https://registry.terraform.io/providers/hashicorp/google/latest/docs

# ===================
# 缓存设置
# ===================
CACHE_TTL=3600
TEMPLATE_CACHE_TTL=7200

# ===================
# 限流设置
# ===================
RATE_LIMIT_PER_MINUTE=100

# ===================
# 后台任务
# ===================
CELERY_BROKER_URL=pyamqp://admin:strongpassword@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://:redispassword@redis:6379

# ===================
# Elasticsearch
# ===================
ELASTICSEARCH_URL=http://elasticsearch:9200

# ===================
# 安全配置
# ===================
CORS_ORIGINS=["https://yourdomain.com"]
ALLOWED_HOSTS=["yourdomain.com", "www.yourdomain.com"]

# ===================
# 日志配置
# ===================
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# ===================
# 前端配置
# ===================
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com

# ===================
# 监控配置
# ===================
PROMETHEUS_ENABLED=true
```

### 安全建议

1. **生成强密钥**
```bash
# 生成SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成数据库密码
openssl rand -base64 32
```

2. **保护环境变量文件**
```bash
chmod 600 .env.production
```

3. **不要提交到Git**
确保 `.env.production` 在 `.gitignore` 中

---

## 🚀 性能优化

### 1. Nginx配置优化
见 `nginx/nginx.prod.conf` (已创建)

### 2. 数据库优化
```sql
-- PostgreSQL性能优化
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET checkpoint_completion_target = '0.9';
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = '100';
ALTER SYSTEM SET random_page_cost = '1.1';
ALTER SYSTEM SET effective_io_concurrency = '200';
ALTER SYSTEM SET work_mem = '10MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';
```

### 3. Redis优化
```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### 4. 应用层优化
- 启用Gzip压缩
- 使用CDN加速静态资源
- 启用HTTP/2
- 配置缓存策略

---

## 📊 监控和日志

### 健康检查端点
```bash
# API健康检查
curl https://api.yourdomain.com/api/v1/health

# 查看metrics
curl https://api.yourdomain.com/metrics
```

### 日志查看
```bash
# Docker日志
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs -f worker

# 系统日志
tail -f /var/log/terraform-assistant/app.log
```

### Prometheus监控
访问: `http://yourdomain.com:9090`

### Grafana仪表板
访问: `http://yourdomain.com:3001`
- 默认用户: admin
- 默认密码: admin (首次登录后请修改)

---

## 🔄 更新和回滚

### 更新应用
```bash
# 拉取最新代码
git pull origin main

# 重新构建镜像
docker-compose -f docker-compose.prod.yml build

# 滚动更新
docker-compose -f docker-compose.prod.yml up -d --no-deps --build api frontend

# 运行数据库迁移（如需要）
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### 回滚
```bash
# 查看镜像历史
docker images terraform-assistant-api

# 使用特定版本
docker tag terraform-assistant-api:old-version terraform-assistant-api:latest
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🆘 故障排查

### 常见问题

1. **容器无法启动**
```bash
docker-compose -f docker-compose.prod.yml logs api
```

2. **数据库连接失败**
检查 DATABASE_URL 配置和数据库服务状态

3. **前端API请求失败**
检查 CORS 配置和 NEXT_PUBLIC_API_BASE_URL

4. **Redis连接失败**
检查 REDIS_URL 配置

### 性能问题
```bash
# 查看资源使用
docker stats

# 查看API性能
docker-compose -f docker-compose.prod.yml exec api top
```

---

## 📞 支持

如有问题，请：
1. 查看日志文件
2. 检查 GitHub Issues
3. 联系技术支持团队

---

**祝您部署顺利！** 🎉
