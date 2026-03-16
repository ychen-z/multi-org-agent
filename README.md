# Multi-Agent 组织智能分析系统

一个可处理 500 万级 HR 数据的多智能体组织分析系统，提供招聘效能、绩效目标、人才风险、组织健康等多维度智能分析，并生成可执行的战略建议。

## 🎯 系统特性

- **6 个专业 Agent**：数据治理、招聘效能、绩效目标、人才风险、组织健康、主控调度
- **500 万级数据处理**：支持大规模 HR 数据的高效分析
- **多模型支持**：可切换 OpenAI、通义千问、智谱 GLM、Ollama 本地模型
- **智能报告生成**：自动生成 CEO 一页纸战略报告和可执行 Action List
- **可视化看板**：React + ECharts 构建的专业管理看板

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     主控 Agent (Orchestrator)                    │
│                调度所有 Agent，交叉归因，战略报告                  │
└─────────────────────────────────────────────────────────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
       ▼                        ▼                        ▼
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│ 数据治理     │        │ 招聘效能     │        │ 绩效目标     │
│ Agent       │        │ Agent       │        │ Agent       │
└─────────────┘        └─────────────┘        └─────────────┘
       │                        │                        │
       ▼                        ▼                        ▼
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│ 人才风险     │        │ 组织健康     │        │ 报告生成     │
│ Agent       │        │ Agent       │        │ Module      │
└─────────────┘        └─────────────┘        └─────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- MongoDB 7+
- Docker & Docker Compose (推荐)

### 安装步骤

1. **克隆项目**

```bash
git clone <repository-url>
cd multi-agent-org-sys
```

2. **配置环境变量**

```bash
cp .env.example .env
# 编辑 .env 文件，填入 LLM API Keys
```

3. **使用 Docker Compose 启动**

```bash
docker-compose up -d
```

或者手动安装：

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install

# 启动 MongoDB
docker run -d -p 27017:27017 --name mongo mongo:7

# 启动后端
uvicorn src.api.main:app --reload

# 启动前端
cd frontend && npm run dev
```

4. **生成模拟数据**

```bash
python -m src.data.generator --count 5000000
```

5. **访问系统**

- 前端看板：http://localhost:3000
- API 文档：http://localhost:8000/docs

## 📁 项目结构

```
multi-agent-org-sys/
├── src/
│   ├── agents/              # Agent 实现
│   │   ├── base_agent.py    # Agent 基类
│   │   ├── orchestrator.py  # 主控 Agent
│   │   ├── data_governance.py
│   │   ├── recruitment.py
│   │   ├── performance.py
│   │   ├── talent_risk.py
│   │   └── org_health.py
│   ├── data/                # 数据层
│   │   ├── mongodb.py       # MongoDB 连接
│   │   ├── models.py        # 数据模型
│   │   ├── generator.py     # 模拟数据生成
│   │   └── importer.py      # 数据导入
│   ├── llm/                 # LLM 抽象层
│   │   ├── base.py          # LLM Provider 基类
│   │   └── providers/       # 各模型实现
│   ├── reports/             # 报告生成
│   └── api/                 # FastAPI 后端
├── frontend/                # React 前端
│   ├── src/
│   │   ├── components/      # 组件
│   │   ├── pages/           # 页面
│   │   └── services/        # API 调用
│   └── package.json
├── config.yaml              # 配置文件
├── docker-compose.yml       # Docker 编排
└── requirements.txt         # Python 依赖
```

## 🔧 配置说明

### LLM 配置

系统支持多种 LLM Provider，在 `config.yaml` 中配置：

```yaml
llm:
  default_provider: openai # 默认使用的 Provider
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      model: gpt-4o
    qwen:
      api_key: ${QWEN_API_KEY}
      model: qwen-max
    ollama:
      base_url: http://localhost:11434
      model: llama3
```

### Agent 配置

各 Agent 的行为参数可在 `config.yaml` 的 `agents` 部分调整。

## 📊 主要功能

### 1. 数据治理

- 自动数据清洗（缺失值、重复、异常值）
- 口径统一（部门、职级、日期格式）
- 数据质量评估与血缘追踪

### 2. 招聘效能分析

- 渠道 ROI 分析
- 招聘漏斗转化分析
- 人岗匹配度评估

### 3. 绩效目标分析

- OKR 完成度分析
- 绩效分布健康度评估
- 管理者风格识别

### 4. 人才风险预警

- 离职概率预测
- 高潜人才识别与流失预警
- 团队稳定性评估

### 5. 组织健康评估

- 人效分析
- 编制合理性评估
- 人口结构分析

### 6. 战略报告生成

- CEO 一页纸报告
- 可执行 Action List
- 智能策略建议

## 🔌 API 接口

| 接口                           | 方法 | 说明         |
| ------------------------------ | ---- | ------------ |
| `/api/v1/analysis/full`        | POST | 全面分析     |
| `/api/v1/analysis/recruitment` | POST | 招聘分析     |
| `/api/v1/analysis/performance` | POST | 绩效分析     |
| `/api/v1/analysis/talent-risk` | POST | 人才风险分析 |
| `/api/v1/analysis/org-health`  | POST | 组织健康分析 |
| `/api/v1/data/generate`        | POST | 生成模拟数据 |
| `/api/v1/reports/strategic`    | GET  | 获取战略报告 |
| `/api/v1/chat`                 | POST | 对话式分析   |

详细 API 文档请访问：http://localhost:8000/docs

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_agents.py

# 带覆盖率报告
pytest --cov=src
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
