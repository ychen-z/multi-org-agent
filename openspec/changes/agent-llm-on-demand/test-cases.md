# Agent LLM On-Demand 测试用例

## 测试概览

| 模块                 | P0 用例 | P1 用例 | P2 用例 | 总计   |
| -------------------- | ------- | ------- | ------- | ------ |
| Part 1: 单次洞察生成 | 8       | 6       | 4       | 18     |
| Part 2: 对话式 AI    | 10      | 8       | 5       | 23     |
| **总计**             | **18**  | **14**  | **9**   | **41** |

---

## 测试数据准备

### 数据库数据

```javascript
// MongoDB 测试数据
const testEmployees = [
  {
    employee_id: "E001",
    name: "张三",
    department: "技术部",
    risk_score: 0.85,
    tenure: 1.2,
  },
  {
    employee_id: "E002",
    name: "李四",
    department: "技术部",
    risk_score: 0.35,
    tenure: 5.0,
  },
  {
    employee_id: "E003",
    name: "王五",
    department: "销售部",
    risk_score: 0.72,
    tenure: 2.1,
  },
];

const testRecruitment = [
  { channel: "BOSS直聘", applications: 100, hires: 10, cost: 50000 },
  { channel: "内推", applications: 30, hires: 8, cost: 5000 },
  { channel: "猎头", applications: 20, hires: 5, cost: 100000 },
];

const testPerformance = [
  { employee_id: "E001", rating: "A", score: 95 },
  { employee_id: "E002", rating: "B", score: 78 },
  { employee_id: "E003", rating: "C", score: 62 },
];
```

### 环境配置

```yaml
# .env.test
LLM_PROVIDER: "openai"
LLM_API_KEY: "<test-key>"
LLM_TIMEOUT: 10 # 秒
MONGODB_URI: "mongodb://localhost:27017/test_db"
```

### Mock 数据

```python
# LLM Mock 响应
MOCK_LLM_INSIGHTS = "技术部离职风险较高，主要集中在入职1-2年的员工，建议加强留人计划。"
MOCK_LLM_PLAN = {
    "reasoning": "需要分析离职率和招聘质量的关联",
    "steps": [
        {"step": 1, "agent": "talent_risk", "action": "获取离职数据", "depends_on": []},
        {"step": 2, "agent": "recruitment", "action": "获取招聘质量", "depends_on": []},
        {"step": 3, "action": "关联分析", "depends_on": [1, 2]}
    ]
}
```

---

# Part 1: 单次洞察生成

## TC-1.1 LLM 触发条件判断

### TC-1.1.1 [P0] 包含"分析"关键词时触发 LLM

**前置条件:**

- Agent 已初始化
- LLM 服务可用

**Given:**

- task = "分析技术部的离职风险"

**When:**

- 调用 `_need_insights(task)`

**Then:**

- 返回 `True`
- LLM 被调用生成洞察

---

### TC-1.1.2 [P0] 包含"为什么"关键词时触发 LLM

**Given:**

- task = "为什么技术部离职率高"

**When:**

- 调用 `_need_insights(task)`

**Then:**

- 返回 `True`

---

### TC-1.1.3 [P0] 包含"建议"关键词时触发 LLM

**Given:**

- task = "给出留人建议"

**When:**

- 调用 `_need_insights(task)`

**Then:**

- 返回 `True`

---

### TC-1.1.4 [P0] 简单查询时不触发 LLM

**Given:**

- task = "列出所有高风险员工"

**When:**

- 调用 `_need_insights(task)`

**Then:**

- 返回 `False`
- LLM **不被调用**

---

### TC-1.1.5 [P0] include_insights=true 强制触发

**Given:**

- task = "有多少员工" (简单查询)
- include_insights = `True`

**When:**

- 调用 `process(message, include_insights=True)`

**Then:**

- 返回结果包含 `ai_insights` 字段

---

### TC-1.1.6 [P1] include_insights=false 强制禁用

**Given:**

- task = "分析离职原因" (包含触发词)
- include_insights = `False`

**When:**

- 调用 `process(message, include_insights=False)`

**Then:**

- 返回结果 **不包含** `ai_insights` 字段

---

### TC-1.1.7 [P1] 空 task 时不触发

**Given:**

- task = "" 或 `None`

**When:**

- 调用 `_need_insights(task)`

**Then:**

- 返回 `False`

---

### TC-1.1.8 [P2] 多个触发词同时存在

**Given:**

- task = "分析离职原因并给出建议"

**When:**

- 调用 `_need_insights(task)`

**Then:**

- 返回 `True`（只需触发一次）

---

## TC-1.2 TalentRiskAgent 洞察生成

### TC-1.2.1 [P0] 正常生成风险洞察

**前置条件:**

- 数据库有 3 条高风险员工记录
- LLM 服务可用

**Given:**

- task = "分析技术部离职风险"
- 技术部高风险员工: E001 (risk=0.85)

**When:**

- 调用 `TalentRiskAgent.process(message)`

**Then:**

- 返回 `data.high_risk_employees` 包含 E001
- 返回 `ai_insights` 非空
- `ai_insights` 内容与数据相关

---

### TC-1.2.2 [P0] 无数据时的洞察

**Given:**

- task = "分析市场部离职风险"
- 市场部无员工数据

**When:**

- 调用 `TalentRiskAgent.process(message)`

**Then:**

- 返回 `data.high_risk_employees = []`
- 返回 `ai_insights` 说明"暂无高风险员工"

---

### TC-1.2.3 [P0] LLM 超时回退

**前置条件:**

- 配置 LLM_TIMEOUT = 10s
- Mock LLM 延迟 15s

**Given:**

- task = "分析离职趋势"

**When:**

- 调用 `_generate_insights()`

**Then:**

- 10 秒后超时
- 返回回退洞察（规则生成）
- 不抛出异常

---

### TC-1.2.4 [P1] LLM 调用失败回退

**前置条件:**

- Mock LLM 返回 500 错误

**Given:**

- task = "分析离职原因"

**When:**

- 调用 `_generate_insights()`

**Then:**

- 返回回退洞察
- 记录错误日志
- 不影响数据返回

---

### TC-1.2.5 [P2] 洞察内容格式验证

**Given:**

- task = "分析技术部离职风险"

**When:**

- 调用 `_generate_insights()`

**Then:**

- 洞察包含"关键发现"
- 洞察包含"原因分析"或"建议行动"
- 每条不超过 50 字

---

## TC-1.3 RecruitmentAgent 洞察生成

### TC-1.3.1 [P0] 渠道 ROI 分析洞察

**前置条件:**

- 有 3 个招聘渠道数据

**Given:**

- task = "分析招聘渠道 ROI"

**When:**

- 调用 `RecruitmentAgent.process(message)`

**Then:**

- 返回 `data.channel_stats`
- 返回 `ai_insights` 包含渠道对比分析

---

### TC-1.3.2 [P1] 漏斗分析洞察

**Given:**

- task = "分析招聘漏斗"

**When:**

- 调用 `RecruitmentAgent.process(message)`

**Then:**

- 返回漏斗数据
- 洞察指出转化率瓶颈

---

## TC-1.4 PerformanceAgent 洞察生成

### TC-1.4.1 [P0] 绩效分布洞察

**Given:**

- task = "分析绩效分布"
- 测试数据: A=1, B=1, C=1

**When:**

- 调用 `PerformanceAgent.process(message)`

**Then:**

- 返回绩效分布数据
- 洞察说明分布是否合理

---

### TC-1.4.2 [P1] 高潜人才识别洞察

**Given:**

- task = "识别高潜人才"

**When:**

- 调用 `PerformanceAgent.process(message)`

**Then:**

- 返回高潜员工列表
- 洞察包含识别标准说明

---

## TC-1.5 OrgHealthAgent 洞察生成

### TC-1.5.1 [P0] 组织健康度洞察

**Given:**

- task = "分析组织健康度"

**When:**

- 调用 `OrgHealthAgent.process(message)`

**Then:**

- 返回健康度评分
- 洞察说明薄弱环节

---

### TC-1.5.2 [P2] 管理幅度分析洞察

**Given:**

- task = "分析管理幅度"

**When:**

- 调用 `OrgHealthAgent.process(message)`

**Then:**

- 返回各级别管理幅度
- 洞察对比行业标准

---

## TC-1.6 API 路由集成

### TC-1.6.1 [P0] API 返回 AI 洞察

**Given:**

- POST /api/v1/analysis/talent-risk
- body: `{"task": "分析技术部离职风险"}`

**When:**

- 发送请求

**Then:**

- 状态码 200
- 响应包含 `data.ai_insights`

---

### TC-1.6.2 [P1] API 支持 include_insights 参数

**Given:**

- POST /api/v1/analysis/talent-risk
- body: `{"task": "列出员工", "include_insights": true}`

**When:**

- 发送请求

**Then:**

- 响应包含 `ai_insights`（即使是简单查询）

---

---

# Part 2: 对话式 AI 洞察

## TC-2.1 ConversationalAgent 核心

### TC-2.1.1 [P0] 单 Agent 问题处理

**前置条件:**

- ConversationalAgent 已初始化
- 专业 Agent 已注册

**Given:**

- message = "技术部有多少高风险员工？"
- history = []

**When:**

- 调用 `process_stream(message, history)`

**Then:**

- 生成计划只包含 talent_risk Agent
- 返回正确的员工数量
- 发送 SSE 事件序列: think → plan → action → observation → content → done

---

### TC-2.1.2 [P0] 跨 Agent 问题处理

**Given:**

- message = "技术部离职率高是否和招聘质量有关？"

**When:**

- 调用 `process_stream(message, history)`

**Then:**

- 生成计划包含 talent_risk 和 recruitment Agent
- Step 3 依赖 Step 1 和 Step 2
- 最终洞察综合两个数据源

---

### TC-2.1.3 [P0] 多轮对话上下文理解

**Given:**

- history = [
  {"role": "user", "content": "技术部离职率是多少？"},
  {"role": "assistant", "content": "技术部离职率是 18.5%..."}
  ]
- message = "那研发部呢？"

**When:**

- 调用 `process_stream(message, history)`

**Then:**

- 理解"那研发部呢"指的是离职率
- 返回研发部离职率数据

---

### TC-2.1.4 [P1] 空 history 处理

**Given:**

- message = "分析离职风险"
- history = []

**When:**

- 调用 `process_stream(message, history)`

**Then:**

- 正常处理
- 不依赖上下文

---

### TC-2.1.5 [P1] 超长 history 截断

**Given:**

- history 包含 50 轮对话（100 条消息）
- message = "继续分析"

**When:**

- 调用 `process_stream(message, history)`

**Then:**

- 只使用最近 20 轮（40 条消息）
- 不超出 LLM token 限制

---

## TC-2.2 执行计划生成

### TC-2.2.1 [P0] 简单问题生成单步计划

**Given:**

- message = "技术部有多少人？"

**When:**

- 调用 `_generate_plan(message, history)`

**Then:**

- 返回 ExecutionPlan
- steps 只有 1 步
- agent = "org_health" 或 "talent_risk"

---

### TC-2.2.2 [P0] 复杂问题生成多步计划

**Given:**

- message = "对比各部门离职率和招聘成本"

**When:**

- 调用 `_generate_plan(message, history)`

**Then:**

- steps >= 2 步
- 包含 talent_risk 和 recruitment Agent
- 最后一步做关联分析

---

### TC-2.2.3 [P0] 依赖关系正确

**Given:**

- 计划包含关联分析步骤

**When:**

- 解析 ExecutionPlan

**Then:**

- 关联步骤的 depends_on 包含前置步骤
- 无循环依赖

---

### TC-2.2.4 [P1] 拓扑排序正确

**Given:**

- steps = [
  {step: 1, depends_on: []},
  {step: 2, depends_on: []},
  {step: 3, depends_on: [1, 2]}
  ]

**When:**

- 调用 `_topological_sort(steps)`

**Then:**

- Step 1 和 Step 2 可并行（同一批次）
- Step 3 在 Step 1、2 之后

---

### TC-2.2.5 [P2] 计划生成失败回退

**Given:**

- LLM 返回非法 JSON

**When:**

- 调用 `_generate_plan()`

**Then:**

- 使用默认单步计划
- 记录错误日志
- 不中断流程

---

## TC-2.3 SSE 流式输出

### TC-2.3.1 [P0] SSE 事件格式正确

**Given:**

- 发起对话请求

**When:**

- 接收 SSE 流

**Then:**

- 每个事件格式: `event: <type>\ndata: <json>\n\n`
- event 类型: think/plan/action/observation/content/done/error

---

### TC-2.3.2 [P0] 事件顺序正确

**Given:**

- 一次完整对话

**When:**

- 记录所有 SSE 事件

**Then:**

- 第一个事件是 think
- 紧接着是 plan
- 然后是 action/observation 交替
- content 事件在 observation 之后
- 最后是 done

---

### TC-2.3.3 [P0] content 事件流式输出

**Given:**

- 长回复文本

**When:**

- 接收 content 事件

**Then:**

- 收到多个 content 事件
- 每个 delta 是文本片段
- 拼接后得到完整回复

---

### TC-2.3.4 [P1] done 事件包含建议

**Given:**

- 完成对话

**When:**

- 接收 done 事件

**Then:**

- data.suggestions 是数组
- 包含 2-4 个后续问题建议

---

### TC-2.3.5 [P1] error 事件处理

**Given:**

- 处理过程中发生错误

**When:**

- 发送 error 事件

**Then:**

- event 类型是 "error"
- data.error 包含错误信息
- 流终止

---

## TC-2.4 前端 SSE 通信

### TC-2.4.1 [P0] 建立 SSE 连接

**前置条件:**

- 后端服务运行中

**Given:**

- 用户发送消息

**When:**

- 调用 useChat().sendMessage()

**Then:**

- 建立到 /api/v1/chat/stream 的连接
- 正确接收 SSE 事件

---

### TC-2.4.2 [P0] 实时更新思维链

**Given:**

- 收到 think/action/observation 事件

**When:**

- 处理事件

**Then:**

- currentThinking 状态实时更新
- UI 显示新的思维步骤

---

### TC-2.4.3 [P0] 流式内容显示

**Given:**

- 收到多个 content 事件

**When:**

- 处理事件

**Then:**

- streamingContent 逐步拼接
- UI 显示打字机效果

---

### TC-2.4.4 [P1] 停止生成

**Given:**

- 正在流式输出

**When:**

- 用户点击"停止"

**Then:**

- 中止 fetch 请求
- isStreaming 变为 false
- 保留已收到的内容

---

### TC-2.4.5 [P1] 网络断开重连

**Given:**

- SSE 连接中断

**When:**

- 网络恢复

**Then:**

- 显示错误提示
- 用户可重新发送

---

## TC-2.5 LocalStorage 持久化

### TC-2.5.1 [P0] 保存对话历史

**Given:**

- 完成一轮对话

**When:**

- 检查 LocalStorage

**Then:**

- 存在 chat_history key
- 内容是 JSON 格式的消息数组

---

### TC-2.5.2 [P0] 页面刷新恢复

**Given:**

- LocalStorage 有历史对话

**When:**

- 刷新页面

**Then:**

- 消息列表恢复
- 可继续对话

---

### TC-2.5.3 [P1] 20 轮截断

**Given:**

- 已有 25 轮对话

**When:**

- 保存到 LocalStorage

**Then:**

- 只保留最近 20 轮（40 条消息）
- 旧消息被删除

---

### TC-2.5.4 [P2] LocalStorage 满时处理

**Given:**

- LocalStorage 接近配额

**When:**

- 尝试保存

**Then:**

- 捕获异常
- 显示警告
- 不影响当前对话

---

## TC-2.6 思维链 UI

### TC-2.6.1 [P0] 思维链默认收起

**Given:**

- AI 回复完成

**When:**

- 查看消息

**Then:**

- 思维链默认收起
- 显示"思维过程 (N 步)"

---

### TC-2.6.2 [P0] 展开显示详情

**Given:**

- 点击"思维过程"

**When:**

- 展开思维链

**Then:**

- 显示所有步骤
- 每步显示对应图标 (💭/🔍/📊)

---

### TC-2.6.3 [P1] 流式时自动展开

**Given:**

- 正在接收思维链事件

**When:**

- 收到 think/action/observation

**Then:**

- 思维链自动展开
- 显示加载中状态

---

### TC-2.6.4 [P2] 长内容截断

**Given:**

- observation 内容超过 200 字

**When:**

- 显示思维步骤

**Then:**

- 内容被截断
- 显示"..."

---

## TC-2.7 建议问题交互

### TC-2.7.1 [P0] 显示建议问题

**Given:**

- 收到 done 事件，suggestions 非空

**When:**

- 渲染消息

**Then:**

- 显示建议问题 chips
- 可点击

---

### TC-2.7.2 [P0] 点击填充输入框

**Given:**

- 点击建议问题 chip

**When:**

- 处理点击

**Then:**

- 输入框填充问题内容
- 聚焦输入框
- 不自动发送

---

### TC-2.7.3 [P1] 编辑后发送

**Given:**

- 建议问题已填充到输入框

**When:**

- 用户编辑内容后按 Enter

**Then:**

- 发送编辑后的内容
- 正常处理请求

---

## TC-2.8 边界和异常

### TC-2.8.1 [P1] 空消息处理

**Given:**

- message = "" 或只有空格

**When:**

- 尝试发送

**Then:**

- 不发送请求
- 发送按钮禁用

---

### TC-2.8.2 [P1] 超长消息处理

**Given:**

- message 超过 2000 字符

**When:**

- 发送请求

**Then:**

- 后端返回 400 错误
- 前端显示"消息过长"提示

---

### TC-2.8.3 [P2] 并发请求处理

**Given:**

- 快速连续发送两条消息

**When:**

- 处理请求

**Then:**

- 第一个请求被取消
- 只处理最后一个

---

### TC-2.8.4 [P2] 无可用 Agent

**Given:**

- 问题不匹配任何 Agent

**When:**

- 生成执行计划

**Then:**

- 直接由 ConversationalAgent 回答
- 不调用专业 Agent

---

---

## 测试执行清单

### P0 用例 (必须通过)

- [ ] TC-1.1.1 包含"分析"关键词时触发 LLM
- [ ] TC-1.1.4 简单查询时不触发 LLM
- [ ] TC-1.1.5 include_insights=true 强制触发
- [ ] TC-1.2.1 正常生成风险洞察
- [ ] TC-1.2.2 无数据时的洞察
- [ ] TC-1.2.3 LLM 超时回退
- [ ] TC-1.3.1 渠道 ROI 分析洞察
- [ ] TC-1.4.1 绩效分布洞察
- [ ] TC-1.5.1 组织健康度洞察
- [ ] TC-1.6.1 API 返回 AI 洞察
- [ ] TC-2.1.1 单 Agent 问题处理
- [ ] TC-2.1.2 跨 Agent 问题处理
- [ ] TC-2.1.3 多轮对话上下文理解
- [ ] TC-2.2.1 简单问题生成单步计划
- [ ] TC-2.2.2 复杂问题生成多步计划
- [ ] TC-2.3.1 SSE 事件格式正确
- [ ] TC-2.4.1 建立 SSE 连接
- [ ] TC-2.5.1 保存对话历史

### P1 用例 (应该通过)

- [ ] TC-1.1.2, TC-1.1.3, TC-1.1.6, TC-1.1.7
- [ ] TC-1.2.4
- [ ] TC-1.3.2, TC-1.4.2
- [ ] TC-1.6.2
- [ ] TC-2.1.4, TC-2.1.5
- [ ] TC-2.2.4
- [ ] TC-2.3.4, TC-2.3.5
- [ ] TC-2.4.4, TC-2.4.5
- [ ] TC-2.5.3
- [ ] TC-2.6.3
- [ ] TC-2.7.3
- [ ] TC-2.8.1, TC-2.8.2

### P2 用例 (最好通过)

- [ ] TC-1.1.8
- [ ] TC-1.2.5
- [ ] TC-1.5.2
- [ ] TC-2.2.5
- [ ] TC-2.5.4
- [ ] TC-2.6.4
- [ ] TC-2.8.3, TC-2.8.4
