# Multi-Agent 组织智能分析系统 - 技术设计

## Context

构建一个可处理 500 万级 HR 数据的 Multi-Agent 系统，采用 Python + LangGraph 作为 Agent 框架，MongoDB 作为数据存储，React + ECharts 作为前端可视化。系统需要支持多种 LLM 后端的灵活切换。

---

## Goals / Non-Goals

### Goals

1. **可扩展的 Agent 架构**：易于新增专业 Agent，支持热插拔
2. **高效数据处理**：500 万级数据秒级查询响应
3. **多模型支持**：一套代码适配多种 LLM 提供商
4. **生产级可靠性**：完善的错误处理、日志、监控
5. **美观的可视化**：专业级管理看板

### Non-Goals

1. 实时流式数据处理（本期批处理即可）
2. 移动端适配
3. 多租户隔离
4. 细粒度权限控制

---

## Decisions

### Decision 1: Agent 架构设计

采用 **LangGraph 状态图** 作为 Agent 编排框架。

```
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator Agent                          │
│                   (LangGraph StateGraph)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    State                                 │   │
│  │  - messages: List[Message]                              │   │
│  │  - analysis_results: Dict[str, Any]                     │   │
│  │  - current_agent: str                                    │   │
│  │  - completed_agents: Set[str]                           │   │
│  │  - errors: List[Error]                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│            ┌─────────────────┼─────────────────┐                │
│            ▼                 ▼                 ▼                │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │   Router    │   │  Executor   │   │ Aggregator  │           │
│  │    Node     │──▶│    Node     │──▶│    Node     │           │
│  └─────────────┘   └─────────────┘   └─────────────┘           │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ DataGov Agent │    │Recruitment Agt│    │Performance Agt│
└───────────────┘    └───────────────┘    └───────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│TalentRisk Agt │    │ OrgHealth Agt │    │   Report Agt  │
└───────────────┘    └───────────────┘    └───────────────┘
```

**理由：**

- LangGraph 原生支持复杂的 Agent 工作流
- 状态图模式便于追踪和调试
- 支持条件路由和并行执行
- 与 LangChain 生态无缝集成

---

### Decision 2: Agent 通信协议

定义统一的 Agent 消息格式：

```python
@dataclass
class AgentMessage:
    agent_id: str           # 发送者 Agent ID
    message_type: str       # request / response / error
    task_type: str          # 任务类型
    payload: Dict[str, Any] # 数据载荷
    timestamp: datetime
    trace_id: str           # 追踪 ID

@dataclass
class AgentResponse:
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    metrics: Dict[str, float]  # 执行指标（耗时等）
```

**理由：**

- 统一格式便于日志和监控
- trace_id 支持全链路追踪
- metrics 支持性能监控

---

### Decision 3: 数据模型设计

MongoDB Collections 设计：

```javascript
// employees - 员工主数据
{
  _id: ObjectId,
  employee_id: "EMP001",        // 工号
  name: "张三",
  gender: "M",
  birth_date: ISODate,
  hire_date: ISODate,
  department_id: "DEPT001",
  position_id: "POS001",
  level: "P6",
  manager_id: "EMP000",
  status: "active",             // active/resigned/terminated
  salary: {
    base: 30000,
    bonus: 5000,
    total: 35000
  },
  created_at: ISODate,
  updated_at: ISODate
}

// departments - 部门
{
  _id: ObjectId,
  department_id: "DEPT001",
  name: "研发中心",
  parent_id: "DEPT000",
  level: 2,
  headcount_budget: 100,
  headcount_actual: 95
}

// performance_records - 绩效记录
{
  _id: ObjectId,
  employee_id: "EMP001",
  period: "2024-H1",
  rating: "A",                  // S/A/B/C/D
  okr_score: 0.85,
  reviewer_id: "EMP000",
  created_at: ISODate
}

// recruitment_records - 招聘记录
{
  _id: ObjectId,
  requisition_id: "REQ001",
  channel: "猎聘",
  stage: "offer_accepted",      // resume/screening/interview/offer/accepted/rejected
  candidate_name: "李四",
  position_id: "POS001",
  cost: 5000,
  created_at: ISODate,
  stage_history: [
    { stage: "resume", timestamp: ISODate },
    { stage: "screening", timestamp: ISODate }
  ]
}

// risk_assessments - 风险评估
{
  _id: ObjectId,
  employee_id: "EMP001",
  assessment_date: ISODate,
  turnover_risk_score: 0.75,
  risk_level: "high",           // low/medium/high/critical
  risk_factors: ["salary", "growth"],
  recommended_actions: ["retention_talk", "salary_review"]
}

// analytics_cache - 分析结果缓存
{
  _id: ObjectId,
  analysis_type: "recruitment_roi",
  parameters: { period: "2024-Q1" },
  result: { ... },
  expires_at: ISODate
}
```

**索引设计：**

```javascript
// employees 索引
db.employees.createIndex({ employee_id: 1 }, { unique: true });
db.employees.createIndex({ department_id: 1 });
db.employees.createIndex({ status: 1, department_id: 1 });
db.employees.createIndex({ hire_date: 1 });

// performance_records 索引
db.performance_records.createIndex({ employee_id: 1, period: 1 });
db.performance_records.createIndex({ period: 1, rating: 1 });

// recruitment_records 索引
db.recruitment_records.createIndex({ channel: 1, created_at: 1 });
db.recruitment_records.createIndex({ stage: 1 });
```

**理由：**

- MongoDB 文档模型灵活适配 HR 数据的多样性
- 嵌入式设计减少关联查询
- 合理索引支撑大数据量查询性能

---

### Decision 4: LLM 抽象层

设计多模型适配层：

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs) -> str:
        pass

    @abstractmethod
    async def chat_with_tools(self, messages: List[Message], tools: List[Tool], **kwargs) -> ToolCallResult:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

class QwenProvider(LLMProvider):
    # 通义千问实现

class GLMProvider(LLMProvider):
    # 智谱 GLM 实现

class OllamaProvider(LLMProvider):
    # 本地模型实现

# 工厂模式
class LLMFactory:
    @staticmethod
    def create(provider: str, **kwargs) -> LLMProvider:
        providers = {
            "openai": OpenAIProvider,
            "qwen": QwenProvider,
            "glm": GLMProvider,
            "ollama": OllamaProvider
        }
        return providers[provider](**kwargs)
```

**配置方式：**

```yaml
# config.yaml
llm:
  default_provider: openai
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

**理由：**

- 抽象层解耦业务逻辑与模型提供商
- 支持运行时切换模型
- 便于成本优化（不同任务用不同模型）

---

### Decision 5: 数据生成器设计

采用 **Faker + 分布控制** 生成真实感数据：

```python
class HRDataGenerator:
    def __init__(self, seed: int = 42):
        self.fake = Faker('zh_CN')
        Faker.seed(seed)

    def generate_employees(self, count: int) -> Generator[dict, None, None]:
        # 生成符合真实分布的员工数据
        # - 年龄：正态分布 (μ=32, σ=8)
        # - 薪资：对数正态分布
        # - 司龄：指数分布
        # - 绩效：正态分布 + 强制分布约束

    def generate_org_structure(self, depth: int, span: int) -> dict:
        # 生成组织架构
        # 保持管理幅度在合理范围

    def generate_recruitment_funnel(self, openings: int) -> List[dict]:
        # 生成招聘数据
        # 符合漏斗转化规律
```

**批量写入优化：**

```python
async def bulk_insert(collection, documents, batch_size=10000):
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        await collection.insert_many(batch, ordered=False)
```

**理由：**

- Faker 提供中文数据支持
- 可控的随机种子保证可重现性
- 分布控制确保数据真实感
- 批量写入优化性能

---

### Decision 6: API 设计

采用 **FastAPI** 构建 RESTful API：

```python
# API 结构
/api/v1/
├── /analysis/                    # 分析接口
│   ├── POST /full                # 全面分析
│   ├── POST /recruitment         # 招聘分析
│   ├── POST /performance         # 绩效分析
│   ├── POST /talent-risk         # 人才风险
│   └── POST /org-health          # 组织健康
├── /data/                        # 数据接口
│   ├── POST /generate            # 生成模拟数据
│   ├── POST /import              # 导入数据
│   └── GET /stats                # 数据统计
├── /reports/                     # 报告接口
│   ├── GET /strategic/{id}       # 战略报告
│   ├── POST /generate            # 生成报告
│   └── GET /action-list/{id}     # Action List
├── /chat/                        # 对话接口
│   └── POST /                    # 对话分析
└── /ws/                          # WebSocket
    └── /analysis/{task_id}       # 分析进度推送
```

**响应格式：**

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "req_xxx",
    "duration_ms": 1234
  }
}
```

---

### Decision 7: 前端架构

React + TypeScript + Tailwind CSS + ECharts：

```
frontend/
├── src/
│   ├── components/
│   │   ├── charts/              # ECharts 封装
│   │   │   ├── BarChart.tsx
│   │   │   ├── LineChart.tsx
│   │   │   ├── PieChart.tsx
│   │   │   ├── FunnelChart.tsx
│   │   │   ├── RadarChart.tsx
│   │   │   └── HeatmapChart.tsx
│   │   ├── cards/               # 指标卡片
│   │   ├── filters/             # 筛选器
│   │   └── layout/              # 布局组件
│   ├── pages/
│   │   ├── Dashboard.tsx        # 总览
│   │   ├── Recruitment.tsx      # 招聘分析
│   │   ├── Performance.tsx      # 绩效分析
│   │   ├── TalentRisk.tsx       # 人才风险
│   │   ├── OrgHealth.tsx        # 组织健康
│   │   └── StrategicReport.tsx  # 战略报告
│   ├── hooks/                   # 自定义 hooks
│   ├── services/                # API 调用
│   ├── stores/                  # 状态管理 (Zustand)
│   └── types/                   # TypeScript 类型
└── package.json
```

**理由：**

- React 生态成熟，组件复用性强
- ECharts 图表丰富，性能优秀
- Tailwind 快速构建美观 UI
- Zustand 轻量状态管理

---

### Decision 8: 部署架构

Docker Compose 本地部署：

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URI=mongodb://mongo:27017/hr_analytics
    depends_on:
      - mongo

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

volumes:
  mongo_data:
```

---

## Technical Risks

### Risk 1: LLM 响应延迟

**风险：** 大规模分析时 LLM 调用耗时长，用户等待体验差

**缓解：**

- 实现分析结果缓存
- 使用 WebSocket 推送分析进度
- 支持后台任务异步执行
- 针对简单查询使用规则引擎而非 LLM

### Risk 2: MongoDB 查询性能

**风险：** 500 万数据量下复杂聚合查询可能超时

**缓解：**

- 合理设计索引
- 预计算常用指标并缓存
- 分页加载大数据集
- 考虑使用 MongoDB 聚合管道优化

### Risk 3: 数据生成质量

**风险：** 模拟数据不够真实，影响分析结果可信度

**缓解：**

- 研究真实 HR 数据分布特征
- 确保数据间逻辑一致性
- 支持导入真实数据进行验证

---

## Dependencies

- **Python 3.11+**
- **LangChain / LangGraph**: Agent 框架
- **FastAPI**: Web 框架
- **Motor**: 异步 MongoDB 驱动
- **Faker**: 数据生成
- **Pydantic**: 数据验证
- **React 18+**: 前端框架
- **ECharts 5+**: 图表库
- **Tailwind CSS 3+**: 样式框架
- **MongoDB 7+**: 数据库
