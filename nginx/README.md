# Nginx配置说明

## SSL证书设置

### 使用Let's Encrypt (推荐)

1. 安装Certbot:
```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
```

2. 获取SSL证书:
```bash
sudo certbot certonly --webroot -w /var/www/certbot \
  -d yourdomain.com \
  -d www.yourdomain.com \
  -d api.yourdomain.com \
  --email your-email@example.com \
  --agree-tos
```

3. 复制证书到nginx/ssl目录:
```bash
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/
```

4. 设置权限:
```bash
sudo chmod 644 nginx/ssl/fullchain.pem
sudo chmod 600 nginx/ssl/privkey.pem
```

### 自签名证书 (仅用于测试)

```bash
cd nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout privkey.pem \
  -out fullchain.pem \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=YourOrg/CN=yourdomain.com"
```

## 配置说明

### 修改域名

编辑 `nginx.prod.conf`，替换所有的 `yourdomain.com` 为您的实际域名。

### 性能调优

根据服务器配置调整以下参数：

```nginx
worker_processes auto;  # CPU核心数
worker_connections 2048;  # 根据系统限制调整
```

### 安全加固

1. 限流配置已启用
2. SSL/TLS最佳实践
3. 安全响应头
4. IP白名单（metrics端点）

## 测试配置

```bash
# 测试配置文件语法
nginx -t -c nginx/nginx.prod.conf

# 重新加载配置
nginx -s reload
```

## 日志位置

- 访问日志: `/var/log/nginx/access.log`
- 错误日志: `/var/log/nginx/error.log`

## 监控

查看Nginx状态:
```bash
docker-compose -f docker-compose.prod.yml logs -f nginx
```
