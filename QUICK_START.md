# 🚀 Terraform Assistant - 快速部署指南

## 📋 前提条件

确保您的服务器已安装：
- ✅ Docker 24.0+
- ✅ Docker Compose 2.20+
- ✅ Git

## ⚡ 5分钟快速部署

### 步骤 1: 克隆项目

```bash
git clone https://github.com/your-org/terraform-assistant.git
cd terraform-assistant
```

### 步骤 2: 配置环境变量

```bash
# 复制生产环境配置模板
cp .env.production.example .env.production

# 编辑配置文件
vim .env.production
```

**必须修改的配置项：**

```env
# 1. 生成随机密钥
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. 设置强密码
POSTGRES_PASSWORD=your-strong-postgres-password
REDIS_PASSWORD=your-strong-redis-password
RABBITMQ_PASSWORD=your-strong-rabbitmq-password
GRAFANA_PASSWORD=your-grafana-admin-password

# 3. 配置OpenAI API密钥
OPENAI_API_KEY=sk-your-openai-api-key

# 4. 修改域名
DOMAIN=yourdomain.com
API_BASE_URL=https://api.yourdomain.com
FRONTEND_URL=https://yourdomain.com
```

### 步骤 3: 配置SSL证书

#### 方式A: 使用Let's Encrypt (推荐)

```bash
# 安装certbot
sudo apt-get update
sudo apt-get install certbot

# 获取证书
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d www.yourdomain.com \
  -d api.yourdomain.com \
  --email your-email@example.com

# 复制证书
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/
sudo chmod 644 nginx/ssl/fullchain.pem
sudo chmod 600 nginx/ssl/privkey.pem
```

#### 方式B: 自签名证书 (仅测试)

```bash
mkdir -p nginx/ssl
cd nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout privkey.pem -out fullchain.pem \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=YourOrg/CN=yourdomain.com"
cd ../..
```

### 步骤 4: 更新Nginx配置中的域名

```bash
# 在 nginx/nginx.prod.conf 中替换所有 yourdomain.com 为您的实际域名
sed -i 's/yourdomain.com/your-actual-domain.com/g' nginx/nginx.prod.conf
```

### 步骤 5: 一键部署

```bash
# 方式A: 使用部署脚本（推荐）
chmod +x scripts/deploy.sh
./scripts/deploy.sh production

# 方式B: 手动部署
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 步骤 6: 检查服务状态

```bash
# 查看所有服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 步骤 7: 访问应用

- 🌐 **前端**: https://yourdomain.com
- 🔌 **API**: https://api.yourdomain.com
- 📚 **API文档**: https://api.yourdomain.com/docs
- 📊 **Prometheus**: http://your-server-ip:9090
- 📈 **Grafana**: http://your-server-ip:3001

---

## 🔧 常用命令

### 查看日志
```bash
# 所有服务
docker-compose -f docker-compose.prod.yml logs -f

# 特定服务
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f frontend
```

### 重启服务
```bash
# 重启所有服务
docker-compose -f docker-compose.prod.yml restart

# 重启特定服务
docker-compose -f docker-compose.prod.yml restart api
```

### 停止服务
```bash
docker-compose -f docker-compose.prod.yml down
```

### 更新应用
```bash
git pull origin main
./scripts/deploy.sh production --skip-db
```

### 数据库备份
```bash
# 手动备份
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U postgres terraform_assistant > backup_$(date +%Y%m%d).sql

# 恢复
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres terraform_assistant < backup.sql
```

---

## 🛠️ 仅构建（不部署）

### 前端构建

```bash
cd frontend

# 安装依赖
npm install

# 构建
npm run build

# 测试构建结果
npm run start
```

### 后端构建

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest

# 启动开发服务器
uvicorn app.main:app --reload
```

### Docker镜像构建

```bash
# 使用构建脚本
./scripts/build.sh all

# 或手动构建
# 后端
docker build -t terraform-assistant-api:latest .

# 前端
docker build -f frontend/Dockerfile.prod -t terraform-assistant-frontend:latest ./frontend
```

---

## 📊 监控和健康检查

### 健康检查端点

```bash
# API健康检查
curl https://api.yourdomain.com/api/v1/health

# 前端健康检查
curl https://yourdomain.com/
```

### Prometheus Metrics

```bash
curl https://api.yourdomain.com/metrics
```

### 查看资源使用

```bash
docker stats
```

---

## 🔒 安全检查清单

- [ ] 修改了所有默认密码
- [ ] 配置了强密钥（SECRET_KEY）
- [ ] 设置了正确的CORS域名
- [ ] 配置了SSL证书
- [ ] .env.production 文件权限设置为 600
- [ ] 更新了Nginx配置中的域名
- [ ] 配置了防火墙规则
- [ ] 启用了限流保护

---

## 🆘 故障排查

### 问题1: 容器无法启动

```bash
# 查看详细日志
docker-compose -f docker-compose.prod.yml logs api

# 检查配置
docker-compose -f docker-compose.prod.yml config
```

### 问题2: 数据库连接失败

```bash
# 检查数据库状态
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# 测试连接
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d terraform_assistant -c "SELECT 1;"
```

### 问题3: 前端无法连接API

检查：
1. NEXT_PUBLIC_API_BASE_URL 是否正确
2. CORS配置是否包含前端域名
3. Nginx配置是否正确

### 问题4: SSL证书问题

```bash
# 检查证书有效期
openssl x509 -in nginx/ssl/fullchain.pem -noout -dates

# 测试SSL配置
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

---

## 📞 获取帮助

- 📖 详细文档: [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)
- 🐛 问题反馈: [GitHub Issues](https://github.com/your-org/terraform-assistant/issues)
- 📧 技术支持: support@yourdomain.com

---

**祝您部署顺利！** 🎉
