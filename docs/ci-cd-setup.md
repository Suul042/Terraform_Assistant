# CI/CD 设置指南

由于 GitHub App 权限限制，workflow 文件需要手动添加。

## GitHub Actions Workflow

创建文件：`.github/workflows/ci.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  # Backend Tests
  backend-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: terraform_assistant_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run linters
        run: |
          black app/ --check
          isort app/ --check-only
          flake8 app/
          mypy app/ || true

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/terraform_assistant_test
          REDIS_URL: redis://localhost:6379
          SECRET_KEY: test-secret-key-for-ci
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          pytest tests/ -v --cov=app --cov-report=xml --cov-report=html

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: backend
          name: backend-coverage

  # Frontend Tests
  frontend-test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci

      - name: Run linter
        working-directory: ./frontend
        run: npm run lint

      - name: Type check
        working-directory: ./frontend
        run: npm run type-check

      - name: Run tests
        working-directory: ./frontend
        run: npm run test

      - name: Build
        working-directory: ./frontend
        env:
          NEXT_PUBLIC_API_BASE_URL: http://localhost:8000
        run: npm run build

  # Docker Build Test
  docker-build:
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build backend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          push: false
          tags: terraform-assistant-api:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          file: ./frontend/Dockerfile.prod
          push: false
          tags: terraform-assistant-frontend:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # Security Scan
  security-scan:
    runs-on: ubuntu-latest
    needs: [backend-test]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

## 手动添加步骤

1. 在 GitHub 仓库中，进入 **Settings** → **Actions** → **General**
2. 确保 Actions 已启用
3. 创建 `.github/workflows/` 目录（如果不存在）
4. 创建 `ci.yml` 文件，复制上面的内容
5. 提交并推送

## 配置 Secrets

在 GitHub 仓库的 **Settings** → **Secrets and variables** → **Actions** 中添加：

- `OPENAI_API_KEY` - OpenAI API 密钥（如果使用 AI 功能）

## 其他 CI/CD 选项

### GitLab CI

如果使用 GitLab，创建 `.gitlab-ci.yml`：

```yaml
stages:
  - test
  - build

backend-test:
  stage: test
  image: python:3.11
  services:
    - postgres:15-alpine
    - redis:7-alpine
  variables:
    POSTGRES_DB: terraform_assistant_test
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/terraform_assistant_test
    REDIS_URL: redis://redis:6379
  script:
    - pip install -r requirements.txt
    - pytest tests/ -v --cov=app

frontend-test:
  stage: test
  image: node:18
  script:
    - cd frontend
    - npm ci
    - npm run lint
    - npm run test
    - npm run build
```

## 本地 CI 测试

使用 `act` 在本地测试 GitHub Actions：

```bash
# 安装 act
brew install act  # macOS
# 或
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# 运行工作流
act push
```
