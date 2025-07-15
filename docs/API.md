# Terraform Assistant - API文档

## 概述

Terraform Assistant RESTful API提供了完整的代码生成、验证和管理功能。所有API端点都使用JSON格式进行数据交换。

## 基础信息

- **Base URL**: `https://api.terraform-assistant.com/api/v1`
- **Authentication**: Bearer Token (JWT)
- **Content-Type**: `application/json`
- **Rate Limiting**: 100 requests/minute

## 认证

```bash
# 获取访问令牌
curl -X POST "https://api.terraform-assistant.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-username",
    "password": "your-password"
  }'

# 使用令牌访问API
curl -X GET "https://api.terraform-assistant.com/api/v1/providers" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 错误处理

API使用标准HTTP状态码和统一的错误响应格式：

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource type not found",
    "details": {
      "resource_type": "aws_nonexistent",
      "provider": "aws"
    }
  },
  "metadata": {
    "request_id": "req_123456789",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## API端点

### 云提供商管理

#### 获取所有云提供商

```http
GET /api/v1/providers
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "aws",
      "display_name": "Amazon Web Services",
      "documentation_base_url": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs",
      "sync_status": "active",
      "last_sync_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

#### 同步提供商文档

```http
POST /api/v1/providers/{provider_id}/sync
```

**响应**:
```json
{
  "success": true,
  "data": {
    "status": "success",
    "stats": {
      "resources_processed": 150,
      "resources_created": 5,
      "resources_updated": 10,
      "resources_deleted": 2
    }
  }
}
```

### 资源类型管理

#### 获取资源类型列表

```http
GET /api/v1/resource-types
```

**查询参数**:
- `provider` (string): 过滤云提供商
- `category` (string): 过滤资源类别
- `search` (string): 搜索关键词
- `page` (int): 页码，默认1
- `limit` (int): 每页条数，默认20

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "resource_type": "aws_instance",
      "category": "Compute",
      "subcategory": "EC2",
      "description": "Amazon EC2 instance",
      "documentation_url": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/instance",
      "provider": {
        "id": 1,
        "name": "aws",
        "display_name": "Amazon Web Services"
      }
    }
  ],
  "metadata": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

#### 获取资源类型详情

```http
GET /api/v1/resource-types/{resource_type_id}
```

#### 获取资源参数

```http
GET /api/v1/resource-types/{resource_type_id}/parameters
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "parameter_name": "instance_type",
      "parameter_type": "string",
      "is_required": true,
      "is_computed": false,
      "default_value": null,
      "description": "EC2 instance type",
      "example_value": "t3.micro",
      "validation_rules": {
        "pattern": "^[a-z0-9.]+$"
      }
    }
  ]
}
```

### 代码生成

#### 生成Terraform代码

```http
POST /api/v1/generate
```

**请求体**:
```json
{
  "provider": "aws",
  "resource_type": "aws_instance",
  "action": "create",
  "natural_language_request": "Create a secure web server for production",
  "parameters": {
    "instance_type": "t3.medium",
    "ami": "ami-12345678",
    "vpc_security_group_ids": ["sg-12345678"]
  },
  "requirements": {
    "performance": {
      "max_response_time_ms": 500
    },
    "security": {
      "encryption_at_rest": true,
      "encryption_in_transit": true
    },
    "cost": {
      "max_monthly_cost": 100
    }
  },
  "existing_infrastructure": {
    "vpc_id": "vpc-12345678",
    "subnet_ids": ["subnet-12345678"]
  },
  "team_standards": {
    "naming_convention": "env-app-resource",
    "required_tags": {
      "Environment": "production",
      "Team": "platform"
    }
  },
  "deployment_environment": "prod",
  "output_format": ["main", "variables", "outputs"],
  "include_comments": true
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "main": "resource \"aws_instance\" \"web_server\" {\n  ami           = var.ami\n  instance_type = var.instance_type\n  \n  vpc_security_group_ids = var.security_group_ids\n  \n  tags = {\n    Name        = \"web-server\"\n    Environment = \"production\"\n    Team        = \"platform\"\n  }\n}",
    "variables": "variable \"ami\" {\n  description = \"AMI ID for the instance\"\n  type        = string\n}\n\nvariable \"instance_type\" {\n  description = \"EC2 instance type\"\n  type        = string\n  default     = \"t3.medium\"\n}",
    "outputs": "output \"instance_id\" {\n  description = \"ID of the EC2 instance\"\n  value       = aws_instance.web_server.id\n}\n\noutput \"public_ip\" {\n  description = \"Public IP address of the instance\"\n  value       = aws_instance.web_server.public_ip\n}",
    "readme": "# Web Server Instance\n\nThis module creates a secure web server instance in AWS...",
    "generation_metadata": {
      "generated_at": "2024-01-15T10:30:00Z",
      "provider": "aws",
      "resource_type": "aws_instance",
      "complexity_score": 3,
      "ai_enhanced": true,
      "processing_time_ms": 1250
    },
    "recommendations": [
      "Consider using an Application Load Balancer for high availability",
      "Enable CloudWatch monitoring for better observability",
      "Configure automated backups using AWS Backup"
    ],
    "warnings": [
      "Instance will be created in the default VPC if no VPC is specified",
      "Security group allows SSH access from anywhere"
    ]
  }
}
```

### 代码验证

#### 验证Terraform代码

```http
POST /api/v1/validate
```

**请求体**:
```json
{
  "code": "resource \"aws_instance\" \"web\" {\n  ami           = \"ami-12345678\"\n  instance_type = \"t3.micro\"\n}",
  "provider": "aws"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "is_valid": true,
    "errors": [],
    "warnings": [
      "Consider adding tags for better resource organization"
    ],
    "suggestions": [
      "Add a security group to control network access",
      "Consider using a variable for the AMI ID"
    ]
  }
}
```

### 智能建议

#### 获取代码建议

```http
POST /api/v1/suggestions
```

**请求体**:
```json
{
  "current_code": "resource \"aws_instance\" \"web\" {\n  ami           = \"ami-12345678\"\n  instance_type = \"t3.micro\"\n}",
  "cursor_position": 85,
  "provider": "aws",
  "resource_type": "aws_instance"
}
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "type": "resource",
      "title": "Add Security Group",
      "description": "Add a security group to control network access",
      "code_snippet": "resource \"aws_security_group\" \"web\" {\n  name        = \"web-sg\"\n  description = \"Security group for web server\"\n  \n  ingress {\n    from_port   = 80\n    to_port     = 80\n    protocol    = \"tcp\"\n    cidr_blocks = [\"0.0.0.0/0\"]\n  }\n}",
      "priority": "high"
    }
  ]
}
```

### 模板管理

#### 获取模板列表

```http
GET /api/v1/templates
```

**查询参数**:
- `resource_type_id` (int): 过滤资源类型
- `template_type` (string): 模板类型 (main, variables, outputs, module)
- `complexity_score` (int): 复杂度评分 (1-5)
- `search` (string): 搜索关键词

#### 创建自定义模板

```http
POST /api/v1/templates
```

**请求体**:
```json
{
  "resource_type_id": 1,
  "template_name": "Production Instance",
  "template_type": "main",
  "template_content": "resource \"aws_instance\" \"{{ resource_name }}\" {\n  ami           = var.ami\n  instance_type = var.instance_type\n  \n  monitoring = true\n  \n  tags = {\n    Name        = \"{{ resource_name }}\"\n    Environment = \"{{ environment }}\"\n  }\n}",
  "use_cases": {
    "production": "Production-ready instance with monitoring"
  },
  "complexity_score": 3,
  "best_practices": {
    "monitoring": "Always enable detailed monitoring in production",
    "tags": "Use consistent tagging strategy"
  }
}
```

### 项目管理

#### 获取项目列表

```http
GET /api/v1/projects
```

#### 创建项目

```http
POST /api/v1/projects
```

**请求体**:
```json
{
  "project_name": "Web Application Infrastructure",
  "description": "Infrastructure for our web application",
  "default_provider": "aws",
  "default_region": "us-west-2",
  "project_config": {
    "naming_convention": "webapp-{env}-{resource}",
    "required_tags": {
      "Project": "webapp",
      "Owner": "platform-team"
    }
  }
}
```

#### 获取项目详情

```http
GET /api/v1/projects/{project_id}
```

#### 更新项目

```http
PUT /api/v1/projects/{project_id}
```

#### 删除项目

```http
DELETE /api/v1/projects/{project_id}
```

### 系统状态

#### 健康检查

```http
GET /api/v1/health
```

**响应**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0",
    "dependencies": {
      "database": "healthy",
      "redis": "healthy",
      "elasticsearch": "healthy",
      "ai_service": "healthy"
    },
    "metrics": {
      "requests_per_minute": 45,
      "average_response_time_ms": 150,
      "error_rate": 0.01
    }
  }
}
```

#### 获取系统指标

```http
GET /api/v1/metrics
```

**响应**:
```json
{
  "success": true,
  "data": {
    "code_generations": {
      "total": 12500,
      "today": 150,
      "success_rate": 0.98
    },
    "cache_performance": {
      "hit_rate": 0.85,
      "memory_usage": "45%"
    },
    "resource_types": {
      "total": 450,
      "aws": 180,
      "azure": 150,
      "gcp": 120
    }
  }
}
```

## SDK和客户端库

### Python SDK

```python
from terraform_assistant import TerraformAssistant

# 初始化客户端
client = TerraformAssistant(
    api_key="your-api-key",
    base_url="https://api.terraform-assistant.com"
)

# 生成代码
result = client.generate_code(
    provider="aws",
    resource_type="aws_instance",
    parameters={
        "instance_type": "t3.micro",
        "ami": "ami-12345678"
    }
)

print(result.main)
```

### JavaScript SDK

```javascript
import { TerraformAssistant } from 'terraform-assistant-js';

const client = new TerraformAssistant({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.terraform-assistant.com'
});

const result = await client.generateCode({
  provider: 'aws',
  resourceType: 'aws_instance',
  parameters: {
    instanceType: 't3.micro',
    ami: 'ami-12345678'
  }
});

console.log(result.main);
```

### CLI工具

```bash
# 安装CLI
npm install -g terraform-assistant-cli

# 配置
terraform-assistant config set api-key YOUR_API_KEY

# 生成代码
terraform-assistant generate aws_instance \
  --instance-type t3.micro \
  --ami ami-12345678 \
  --output ./infrastructure/

# 验证代码
terraform-assistant validate ./infrastructure/main.tf
```

## 速率限制

API使用令牌桶算法实现速率限制：

- **默认限制**: 100 requests/minute
- **Burst限制**: 10 requests/second
- **企业版**: 1000 requests/minute

当达到限制时，API将返回HTTP 429状态码：

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "details": {
      "retry_after": 60,
      "limit": 100,
      "remaining": 0
    }
  }
}
```

## Webhooks

### 配置Webhook

```http
POST /api/v1/webhooks
```

**请求体**:
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["code.generated", "sync.completed"],
  "secret": "your-webhook-secret"
}
```

### Webhook事件

#### 代码生成完成

```json
{
  "event": "code.generated",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "request_id": "req_123456789",
    "provider": "aws",
    "resource_type": "aws_instance",
    "status": "success",
    "generation_time_ms": 1250
  }
}
```

#### 文档同步完成

```json
{
  "event": "sync.completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "provider": "aws",
    "status": "success",
    "resources_updated": 15,
    "sync_duration_ms": 30000
  }
}
```

## 错误代码参考

| 错误代码 | HTTP状态码 | 描述 |
|---------|-----------|------|
| `INVALID_REQUEST` | 400 | 请求格式错误 |
| `UNAUTHORIZED` | 401 | 认证失败 |
| `FORBIDDEN` | 403 | 权限不足 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `RATE_LIMIT_EXCEEDED` | 429 | 速率限制 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

## 版本控制

API使用语义化版本控制：

- **v1.0.x**: 稳定版本，向后兼容
- **v1.1.x**: 新功能，向后兼容
- **v2.0.x**: 重大更改，不向后兼容

## 支持

- **文档**: https://docs.terraform-assistant.com
- **API状态**: https://status.terraform-assistant.com
- **支持邮箱**: api-support@terraform-assistant.com
- **GitHub**: https://github.com/terraform-assistant/api