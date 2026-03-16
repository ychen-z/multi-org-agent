# 部署指南

## 环境要求

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- MongoDB 7+

## 快速部署（Docker Compose）

### 1. 克隆项目

```bash
git clone <repository-url>
cd multi-agent-org-sys
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下内容：

```env
# LLM API Keys（至少配置一个）
OPENAI_API_KEY=sk-your-openai-key
QWEN_API_KEY=your-qwen-key        # 可选
GLM_API_KEY=your-glm-key          # 可选

# 默认 LLM Provider
DEFAULT_LLM_PROVIDER=openai

# MongoDB（Docker Compose 自动配置）
MONGODB_URI=mongodb://mongo:27017
```

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 4. 访问服务

- **前端看板**: http://localhost:3000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 5. 生成测试数据

```bash
# 生成 10000 条测试数据
curl -X POST http://localhost:8000/api/v1/data/generate \
  -H "Content-Type: application/json" \
  -d '{"employee_count": 10000}'

# 生成 500 万条数据（需要较长时间）
curl -X POST http://localhost:8000/api/v1/data/generate \
  -H "Content-Type: application/json" \
  -d '{"employee_count": 5000000}'
```

---

## 手动部署

### 后端部署

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 MongoDB
docker run -d -p 27017:27017 --name mongo mongo:7

# 4. 启动后端
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端部署

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 开发模式
npm run dev

# 3. 生产构建
npm run build

# 4. 预览构建结果
npm run preview
```

---

## 生产环境部署

### 使用 Gunicorn + Nginx

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动后端（4 个 worker）
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/hr-analytics/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 代理
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 监控和日志

### 日志位置

- 应用日志: `logs/app.log`
- MongoDB 日志: Docker 容器日志

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# MongoDB 连接检查
mongosh --eval "db.adminCommand('ping')"
```

---

## 常见问题

### Q: MongoDB 连接失败

检查 MongoDB 是否运行：

```bash
docker ps | grep mongo
```

### Q: LLM API 调用失败

1. 检查 API Key 是否正确配置
2. 检查网络连接
3. 查看日志获取详细错误信息

### Q: 500 万数据生成很慢

这是正常的，500 万数据生成可能需要 5-15 分钟。建议：

1. 先用小数据集测试（10000 条）
2. 使用 SSD 存储
3. 确保 MongoDB 有足够内存

### Q: 前端无法连接后端

检查 API 代理配置：

1. 开发环境: `vite.config.ts` 中的 proxy 配置
2. 生产环境: Nginx 代理配置
