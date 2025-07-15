# Terraform多云辅助工具

基于AI的智能Terraform代码生成和管理工具，支持AWS、Azure、Google Cloud三大云平台。

## 🚀 功能特性

### 🎯 核心功能
- **智能代码生成**: 基于自然语言描述生成Terraform代码
- **多云支持**: 统一支持AWS、Azure、Google Cloud Provider
- **AI增强**: 集成GPT-4提供智能建议和最佳实践
- **实时验证**: 即时代码验证和语法检查
- **模板管理**: 可重用的代码模板和模块
- **参数化配置**: 灵活的参数配置和变量管理

### 🛠️ 技术特性
- **高性能**: 多层缓存架构，响应时间<200ms
- **可扩展**: 微服务架构，支持水平扩展
- **实时同步**: 自动同步云提供商文档更新
- **智能缓存**: Redis多层缓存优化
- **类型安全**: 全面的TypeScript支持
- **测试覆盖**: 单元测试和集成测试覆盖率>90%

### 🌐 用户界面
- **Web应用**: 现代化的React界面
- **CLI工具**: 强大的命令行接口
- **IDE集成**: VS Code插件支持
- **API接口**: RESTful API，支持第三方集成

## 📋 项目结构

```
terraform-assistant/
├── app/                          # 后端应用
│   ├── core/                     # 核心配置
│   │   ├── config.py            # 应用配置
│   │   ├── database.py          # 数据库连接
│   │   └── exceptions.py        # 异常定义
│   ├── models/                   # 数据模型
│   │   ├── database.py          # SQLAlchemy模型
│   │   └── schemas.py           # Pydantic模型
│   ├── services/                 # 业务服务
│   │   ├── ai_service.py        # AI推理服务
│   │   ├── cache_service.py     # 缓存服务
│   │   ├── code_generation.py   # 代码生成服务
│   │   └── documentation_sync.py # 文档同步服务
│   ├── api/                      # API路由
│   │   ├── v1/                  # API v1版本
│   │   └── dependencies.py      # 依赖注入
│   └── main.py                   # 应用入口
├── frontend/                     # 前端应用
│   ├── src/
│   │   ├── components/          # React组件
│   │   ├── lib/                 # 工具库
│   │   ├── store/               # 状态管理
│   │   └── app/                 # 页面组件
│   ├── public/                  # 静态资源
│   └── package.json             # 前端依赖
├── tests/                        # 测试文件
│   ├── test_code_generation.py  # 代码生成测试
│   ├── test_ai_service.py       # AI服务测试
│   └── test_integration.py      # 集成测试
├── docs/                         # 文档
├── scripts/                      # 脚本工具
├── docker-compose.yml           # 开发环境
├── Dockerfile                   # 镜像构建
└── requirements.txt             # Python依赖
```

## 🔧 技术栈

### 后端技术
- **API框架**: FastAPI + Uvicorn
- **数据库**: PostgreSQL + SQLAlchemy
- **缓存**: Redis + Hiredis
- **AI服务**: OpenAI GPT-4 + LangChain
- **搜索**: Elasticsearch
- **任务队列**: Celery + RabbitMQ

### 前端技术
- **框架**: Next.js 14 + React 18
- **语言**: TypeScript
- **状态管理**: Zustand
- **UI组件**: Headless UI + Tailwind CSS
- **代码编辑器**: Monaco Editor
- **表单**: React Hook Form + Zod

### 开发工具
- **容器化**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **代码质量**: ESLint + Prettier + Black
- **测试**: Jest + Pytest
- **类型检查**: TypeScript + MyPy

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### 1. 克隆项目
```bash
git clone https://github.com/your-org/terraform-assistant.git
cd terraform-assistant
```

### 2. 环境配置
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

### 3. 启动开发环境
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 4. 安装依赖
```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend && npm install
```

### 5. 数据库初始化
```bash
# 运行数据库迁移
python -m alembic upgrade head

# 初始化基础数据
python scripts/init_data.py
```

### 6. 启动应用
```bash
# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动前端服务
cd frontend && npm run dev
```

### 7. 访问应用
- 前端界面: http://localhost:3000
- API文档: http://localhost:8000/docs
- 管理界面: http://localhost:8000/admin

## 📖 使用指南

### Web界面使用

1. **选择云提供商**: 从下拉列表选择AWS、Azure或GCP
2. **选择资源类型**: 浏览或搜索所需的资源类型
3. **配置参数**: 填写必需参数，可选参数根据需要配置
4. **自然语言描述**: 输入需求描述，AI会提供智能建议
5. **生成代码**: 点击生成按钮获取Terraform代码
6. **验证代码**: 使用内置验证器检查代码质量
7. **导出代码**: 下载生成的代码文件

### CLI使用

```bash
# 初始化项目
terraform-assistant init --provider aws --region us-west-2

# 生成资源
terraform-assistant generate ec2 --name web-server --instance-type t3.medium

# 创建模块
terraform-assistant module create --type vpc --name production-vpc

# 验证代码
terraform-assistant validate --file main.tf

# 部署预览
terraform-assistant deploy --plan-only
```

### API使用

```bash
# 生成代码
curl -X POST "http://localhost:8000/api/v1/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "resource_type": "aws_instance",
    "action": "create",
    "parameters": {
      "instance_type": "t3.micro",
      "ami": "ami-12345678"
    }
  }'

# 验证代码
curl -X POST "http://localhost:8000/api/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "resource \"aws_instance\" \"web\" { ... }",
    "provider": "aws"
  }'
```

## 🔧 配置说明

### 环境变量

```bash
# 应用配置
APP_NAME=Terraform Assistant
DEBUG=false

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost/terraform_assistant

# Redis配置
REDIS_URL=redis://localhost:6379

# AI服务配置
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview

# 安全配置
SECRET_KEY=your-secret-key

# 外部服务
AWS_DOCS_BASE_URL=https://registry.terraform.io/providers/hashicorp/aws/latest/docs
AZURE_DOCS_BASE_URL=https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs
GCP_DOCS_BASE_URL=https://registry.terraform.io/providers/hashicorp/google/latest/docs
```

### 高级配置

```python
# app/core/config.py
class Settings(BaseSettings):
    # 缓存配置
    CACHE_TTL: int = 3600
    TEMPLATE_CACHE_TTL: int = 7200
    
    # 性能配置
    RATE_LIMIT_PER_MINUTE: int = 100
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # AI配置
    AI_MAX_TOKENS: int = 4000
    AI_TEMPERATURE: float = 0.3
    AI_TIMEOUT: int = 30
```

## 🧪 测试

### 运行测试

```bash
# 后端测试
pytest tests/ -v --cov=app --cov-report=html

# 前端测试
cd frontend && npm test

# 集成测试
pytest tests/test_integration.py -v

# 性能测试
pytest tests/test_performance.py -v
```

### 测试覆盖率

- 单元测试覆盖率: >90%
- 集成测试覆盖率: >80%
- 端到端测试覆盖率: >70%

## 📊 监控与日志

### 应用监控

```bash
# 查看应用状态
curl http://localhost:8000/api/v1/health

# 查看指标
curl http://localhost:8000/metrics

# 查看缓存状态
curl http://localhost:8000/api/v1/cache/stats
```

### 日志配置

```python
# 日志级别
LOG_LEVEL=INFO

# 日志格式
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# 日志文件
LOG_FILE=/var/log/terraform-assistant/app.log
```

## 🚀 部署

### Docker部署

```bash
# 构建镜像
docker build -t terraform-assistant .

# 运行容器
docker run -p 8000:8000 terraform-assistant
```

### Kubernetes部署

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: terraform-assistant
spec:
  replicas: 3
  selector:
    matchLabels:
      app: terraform-assistant
  template:
    metadata:
      labels:
        app: terraform-assistant
    spec:
      containers:
      - name: app
        image: terraform-assistant:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

### 生产环境配置

```bash
# 性能优化
WORKERS=4
WORKER_CLASS=uvicorn.workers.UvicornWorker
WORKER_CONNECTIONS=1000

# 安全配置
CORS_ORIGINS=["https://yourapp.com"]
ALLOWED_HOSTS=["yourapp.com"]
```

## 🤝 贡献指南

### 开发流程

1. Fork项目
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -am 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 创建Pull Request

### 代码规范

- Python: Black + isort + flake8
- TypeScript: ESLint + Prettier
- 提交信息: Conventional Commits
- 分支命名: feature/xxx, bugfix/xxx, hotfix/xxx

### 测试要求

- 新功能必须包含单元测试
- 测试覆盖率不低于80%
- 所有测试必须通过CI检查

## 📄 许可证

MIT License. 详见 [LICENSE](LICENSE) 文件。

## 📞 支持

- 文档: https://docs.terraform-assistant.com
- 问题反馈: https://github.com/your-org/terraform-assistant/issues
- 讨论: https://github.com/your-org/terraform-assistant/discussions
- 邮件: support@terraform-assistant.com

## 🔄 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 支持AWS、Azure、GCP三大云平台
- 智能代码生成和AI增强功能
- Web界面和CLI工具
- 完整的测试覆盖

### v1.1.0 (计划中)
- 增强AI推理能力
- 支持更多云服务商
- 团队协作功能
- 企业级安全特性

---

**Terraform Assistant** - 让云基础设施管理更简单、更智能！