## Context

当前各专业 Agent 只做数据查询，不调用 LLM。需要改为"按需调用"模式。
同时支持对话式交互，让用户能够多轮追问，并展示 AI 的思维过程。

## Goals / Non-Goals

**Goals:**

- Agent 能识别何时需要 AI 洞察
- 需要洞察时调用 LLM 生成分析
- 简单查询时不调用 LLM（节省成本和延迟）
- **支持多轮对话，保持上下文**
- **展示 AI 思维链（执行步骤 + LLM 思考）**
- **支持跨 Agent 的复杂问题**

**Non-Goals:**

- 不修改 Orchestrator 的报告生成逻辑
- 不引入新的 LLM 提供商
- 不支持语音输入

---

# Part 1: 单次洞察生成

## Decisions

### 1. 何时调用 LLM

**触发条件**（任一满足即调用）：

- 任务包含"分析"、"为什么"、"原因"
- 任务包含"建议"、"怎么办"、"如何"
- 任务包含"洞察"、"趋势"、"预测"
- 请求参数 include_insights=true

**不触发条件**：

- 简单查询："有多少"、"列出"、"显示"
- 请求参数 include_insights=false

### 2. LLM 调用模式

```python
async def process(self, message: AgentMessage) -> AgentResponse:
    # 1. 判断是否需要洞察
    need_insights = self._need_insights(message)

    # 2. 查询数据
    data = await self._query_data(message)

    # 3. 按需生成洞察
    if need_insights:
        insights = await self._generate_insights(data, message.payload.get("task"))
        return AgentResponse(data=data, ai_insights=insights)

    return AgentResponse(data=data)
```

### 3. 洞察生成 Prompt 模板

```python
INSIGHT_PROMPT = """
你是一位资深的 HR 数据分析专家。

## 数据
{data_summary}

## 用户问题
{user_query}

## 要求
请基于数据回答用户问题，提供：
1. 关键发现（2-3 条）
2. 原因分析（如适用）
3. 建议行动（如适用）

保持简洁，每条不超过 50 字。
"""
```

### 4. 超时和回退

- LLM 调用超时：10 秒
- 超时或失败时：返回数据 + 规则生成的简单洞察

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  用户请求: "分析技术部的离职风险"                                 │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  TalentRiskAgent.process()                                       │
│                                                                 │
│  1. _need_insights("分析技术部的离职风险")                        │
│     └── "分析" in task → True                                   │
│                                                                 │
│  2. _query_data()                                               │
│     └── MongoDB 查询风险数据                                     │
│                                                                 │
│  3. _generate_insights(data, task)                              │
│     └── self.chat(prompt) → "技术部高风险员工占比 15%..."         │
│                                                                 │
│  4. 返回 {data: {...}, ai_insights: "技术部高风险员工..."}        │
└─────────────────────────────────────────────────────────────────┘
```

---

# Part 2: 对话式 AI 洞察

## Design Decisions

### 1. 多轮对话记忆

**选择：前端记忆（LocalStorage）**

```typescript
// 前端保存最近 20 轮对话
interface ChatState {
  messages: Message[]; // max 40 条 (20轮 × 2)
  currentThinking: ThinkStep[];
  isStreaming: boolean;
}

// 持久化
useEffect(() => {
  const trimmed = messages.slice(-40); // 保留最近 20 轮
  localStorage.setItem("chat_history", JSON.stringify(trimmed));
}, [messages]);
```

**理由：**

- 简单，无需后端会话管理
- 用户刷新页面后可恢复对话
- 20 轮足够大多数分析场景

### 2. 思维链展示

**选择：Level 3（执行步骤 + LLM 思考内容）**

```
┌─ 思维过程 ──────────────────────────────── [展开/收起] ─┐
│ 💭 让我先了解技术部的离职情况...                        │
│                                                         │
│ 🔍 查询技术部离职数据                                   │
│    ├─ 技术部员工: 156 人                                │
│    └─ 年离职人数: 29 人 (18.5%)                         │
│                                                         │
│ 💭 这个离职率确实偏高，我来对比其他部门...              │
│                                                         │
│ 🔍 获取全公司部门离职率                                 │
│    ├─ 研发部: 12.3%                                     │
│    ├─ 销售部: 15.1%                                     │
│    └─ 运营部: 10.8%                                     │
│                                                         │
│ 💭 技术部确实是离职率最高的部门，现在分析原因...        │
└─────────────────────────────────────────────────────────┘
```

**思维链类型：**

- `thought` 💭 - LLM 的思考过程
- `action` 🔍 - 调用 Agent/查询数据
- `observation` 📊 - 查询结果

### 3. 页面入口

**选择：独立对话页面**

```
导航栏: [Dashboard] [人才风险] [招聘] [绩效] [组织健康] [🤖 AI 对话]
                                                            ↑
                                                      新增 Tab
```

### 4. 流式协议

**选择：SSE（Server-Sent Events）**

```
POST /api/v1/chat/stream
Content-Type: application/json
Accept: text/event-stream

Request:
{
  "message": "技术部离职率为什么高？",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}

Response (SSE):
event: think
data: {"type": "thought", "content": "让我分析一下这个问题..."}

event: plan
data: {"steps": [{"step": 1, "agent": "talent_risk", ...}]}

event: action
data: {"step": 1, "action": "查询技术部离职数据", "agent": "talent_risk"}

event: observation
data: {"step": 1, "result": {"turnover_rate": 18.5, ...}}

event: think
data: {"type": "thought", "content": "数据显示离职率确实偏高..."}

event: content
data: {"delta": "根据"}

event: content
data: {"delta": "分析，技术部"}

event: done
data: {"suggestions": ["研发部情况如何？", "有哪些高风险员工？"]}
```

### 5. 跨 Agent 问题处理

**选择：规划-执行模式**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       规划-执行模式                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Phase 1: 意图理解 + 计划生成                                           │
│  ─────────────────────────────────────────────────────────────────────  │
│  LLM 分析用户问题，生成执行计划：                                       │
│  [                                                                      │
│    {step: 1, agent: "talent_risk", action: "get_turnover", depends: []},│
│    {step: 2, agent: "recruitment", action: "get_quality", depends: []}, │
│    {step: 3, action: "correlate", depends: [1, 2]}                      │
│  ]                                                                      │
│                                                                         │
│  Phase 2: 并行数据收集                                                  │
│  ─────────────────────────────────────────────────────────────────────  │
│  按拓扑排序执行，无依赖的步骤可并行：                                   │
│                                                                         │
│     Step 1 ──────┬────── Step 2                                        │
│     (TalentRisk) │      (Recruitment)                                  │
│         │        │           │                                         │
│         └────────┴───────────┘                                         │
│                  │                                                      │
│                  ▼                                                      │
│              Step 3 (correlate)                                        │
│              依赖 Step 1 & 2 的结果                                    │
│                                                                         │
│  Phase 3: 综合洞察                                                      │
│  ─────────────────────────────────────────────────────────────────────  │
│  LLM 综合所有数据，生成最终回复                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Architecture

### 整体架构

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        对话式 AI 洞察架构                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Frontend (React)                                                       │
│   ────────────────                                                       │
│   ┌──────────────────────────────────────────────────────────────┐      │
│   │  ChatPage                                                     │      │
│   │  ├── MessageList                                              │      │
│   │  │   ├── UserMessage                                          │      │
│   │  │   └── AssistantMessage                                     │      │
│   │  │       ├── ThinkingChain (可折叠)                           │      │
│   │  │       │   ├── ThoughtStep 💭                               │      │
│   │  │       │   ├── ActionStep 🔍                                │      │
│   │  │       │   └── ObservationStep 📊                           │      │
│   │  │       └── ResponseContent (Markdown)                       │      │
│   │  ├── SuggestionChips                                          │      │
│   │  └── InputBox                                                 │      │
│   │                                                               │      │
│   │  Hooks:                                                       │      │
│   │  ├── useChat() - 管理对话状态和 SSE 连接                      │      │
│   │  └── useChatStorage() - LocalStorage 持久化                   │      │
│   └──────────────────────────────────────────────────────────────┘      │
│                                    │                                     │
│                                    │ SSE                                 │
│                                    ▼                                     │
│   Backend (FastAPI)                                                      │
│   ─────────────────                                                      │
│   ┌──────────────────────────────────────────────────────────────┐      │
│   │  POST /api/v1/chat/stream                                     │      │
│   │                     │                                         │      │
│   │                     ▼                                         │      │
│   │  ┌─────────────────────────────────────────────────────────┐ │      │
│   │  │  ConversationalAgent                                     │ │      │
│   │  │  ├── _understand_intent()    # 意图理解                  │ │      │
│   │  │  ├── _generate_plan()        # 生成执行计划              │ │      │
│   │  │  ├── _execute_plan()         # 执行计划（调用专业Agent） │ │      │
│   │  │  ├── _synthesize_response()  # 综合生成回复              │ │      │
│   │  │  └── _generate_suggestions() # 生成后续问题建议          │ │      │
│   │  └─────────────────────────────────────────────────────────┘ │      │
│   │                     │                                         │      │
│   │        ┌────────────┼────────────┬───────────┐               │      │
│   │        ▼            ▼            ▼           ▼               │      │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │      │
│   │  │TalentRisk│ │Recruitment│ │Performance│ │OrgHealth │        │      │
│   │  │  Agent   │ │  Agent    │ │  Agent    │ │  Agent   │        │      │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │      │
│   │        │            │            │           │               │      │
│   │        └────────────┴────────────┴───────────┘               │      │
│   │                          │                                    │      │
│   │                          ▼                                    │      │
│   │                     MongoDB                                   │      │
│   └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 数据类型定义

```typescript
// Frontend Types (TypeScript)

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  thinking?: ThinkStep[]; // AI 消息的思维链
  suggestions?: string[]; // 建议的后续问题
}

interface ThinkStep {
  type: "thought" | "action" | "observation" | "plan";
  content: string;
  data?: any; // observation 的具体数据
  timestamp: number;
}

interface SSEEvent {
  event:
    | "think"
    | "plan"
    | "action"
    | "observation"
    | "content"
    | "done"
    | "error";
  data: any;
}
```

```python
# Backend Types (Python)

class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str

class ChatStreamRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

class PlanStep(BaseModel):
    step: int
    agent: Optional[str] = None      # talent_risk, recruitment, etc.
    action: str                       # 具体动作描述
    depends_on: List[int] = []       # 依赖的步骤

class ExecutionPlan(BaseModel):
    steps: List[PlanStep]
    reasoning: str                    # 为什么这样规划
```

### ConversationalAgent 核心接口

```python
class ConversationalAgent(BaseAgent):
    """对话式 AI 洞察 Agent"""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id="conversational",
            name="对话式 AI 助手",
            description="支持多轮对话的智能分析助手",
            **kwargs
        )
        # 注册专业 Agent
        self.agents = {
            "talent_risk": TalentRiskAgent(),
            "recruitment": RecruitmentAgent(),
            "performance": PerformanceAgent(),
            "org_health": OrgHealthAgent(),
        }

    async def process_stream(
        self,
        message: str,
        history: List[ChatMessage]
    ) -> AsyncGenerator[SSEEvent, None]:
        """流式处理对话，返回 SSE 事件流"""

        # Phase 1: 意图理解
        yield SSEEvent(event="think", data={
            "type": "thought",
            "content": "让我分析一下这个问题..."
        })

        # Phase 2: 生成执行计划
        plan = await self._generate_plan(message, history)
        yield SSEEvent(event="plan", data=plan.dict())

        # Phase 3: 执行计划
        results = {}
        for step in self._topological_sort(plan.steps):
            # 发送 action 事件
            yield SSEEvent(event="action", data={
                "step": step.step,
                "action": step.action,
                "agent": step.agent
            })

            # 执行步骤
            if step.agent:
                result = await self._execute_agent_step(step, results)
            else:
                result = await self._execute_correlation(step, results)

            results[step.step] = result

            # 发送 observation 事件
            yield SSEEvent(event="observation", data={
                "step": step.step,
                "result": result
            })

            # 发送思考
            yield SSEEvent(event="think", data={
                "type": "thought",
                "content": await self._generate_step_reflection(step, result)
            })

        # Phase 4: 综合生成回复
        yield SSEEvent(event="think", data={
            "type": "thought",
            "content": "综合以上数据，生成分析结论..."
        })

        async for chunk in self._stream_synthesis(message, results, history):
            yield SSEEvent(event="content", data={"delta": chunk})

        # Phase 5: 生成建议问题
        suggestions = await self._generate_suggestions(message, results)
        yield SSEEvent(event="done", data={"suggestions": suggestions})

    async def _generate_plan(
        self,
        message: str,
        history: List[ChatMessage]
    ) -> ExecutionPlan:
        """LLM 生成执行计划"""
        prompt = f"""
用户问题: {message}

对话历史:
{self._format_history(history)}

可用的专业 Agent:
- talent_risk: 离职分析、风险预警、团队稳定性、高风险员工识别
- recruitment: 招聘渠道 ROI、漏斗分析、招聘质量、招聘周期
- performance: 绩效分布、高潜人才、绩效趋势、绩效与薪酬关联
- org_health: 组织健康度、人员结构、管理幅度、文化指标

请生成执行计划，JSON 格式:
{{
  "reasoning": "解释为什么这样规划",
  "steps": [
    {{"step": 1, "agent": "agent_name", "action": "具体动作", "depends_on": []}},
    ...
  ]
}}

规则:
1. 简单问题只需 1-2 个步骤
2. 跨领域问题需要多个 Agent 协作
3. 需要关联分析时，添加 depends_on
4. action 用中文描述
"""
        response = await self.chat(prompt)
        return ExecutionPlan.parse_raw(response)

    def _topological_sort(self, steps: List[PlanStep]) -> List[PlanStep]:
        """拓扑排序，确保依赖关系正确"""
        # ... 实现拓扑排序，支持并行执行无依赖步骤
        pass
```

## Open Questions

无
