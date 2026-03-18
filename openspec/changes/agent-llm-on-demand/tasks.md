# Part 1: 单次洞察生成

## 1. BaseAgent 增强

- [x] 1.1 在 BaseAgent 添加 \_need_insights() 方法判断是否需要洞察
- [x] 1.2 在 BaseAgent 添加 generate_insights() 方法
- [x] 1.3 添加 LLM 调用超时处理 (10秒)

## 2. TalentRiskAgent 改进

- [x] 2.1 重写 process() 方法，支持按需调用 LLM
- [x] 2.2 实现 \_generate_risk_insights() 方法
- [x] 2.3 在 get_high_risk_employees() 中集成洞察生成
- [x] 2.4 在 analyze_team_stability() 中集成洞察生成
- [x] 2.5 实现 \_get_fallback_insight() 回退方法

## 3. RecruitmentAgent 改进

- [x] 3.1 实现 \_generate_recruitment_insights() 方法
- [x] 3.2 在渠道分析中集成洞察生成
- [x] 3.3 在漏斗分析中集成洞察生成

## 4. PerformanceAgent 改进

- [x] 4.1 实现 \_generate_performance_insights() 方法
- [x] 4.2 在绩效分布分析中集成洞察生成

## 5. OrgHealthAgent 改进

- [x] 5.1 实现 \_generate_health_insights() 方法
- [x] 5.2 在健康度分析中集成洞察生成

## 6. API 路由更新

- [x] 6.1 更新 /talent-risk 路由支持 Agent 调用
- [x] 6.2 添加 include_insights 和 task 参数支持
- [x] 6.3 按需决定是否使用 Agent

## 7. 测试验证

- [ ] 7.1 测试 LLM 调用是否按需触发
- [ ] 7.2 测试超时回退是否正常
- [ ] 7.3 测试前端是否正确显示 AI 洞察

---

# Part 2: 对话式 AI 洞察

## 8. ConversationalAgent 实现

### 8.1 核心框架

- [x] 8.1.1 创建 ConversationalAgent 类，继承 BaseAgent
- [x] 8.1.2 实现专业 Agent 注册机制
- [x] 8.1.3 实现 process_stream() 流式处理方法

### 8.2 执行计划生成

- [x] 8.2.1 定义 PlanStep 和 ExecutionPlan 数据模型
- [x] 8.2.2 实现 \_generate_plan() 方法（LLM 生成执行计划）
- [x] 8.2.3 实现 \_topological_sort() 拓扑排序方法
- [x] 8.2.4 支持并行执行无依赖步骤

### 8.3 计划执行

- [x] 8.3.1 实现 \_execute_agent_step() 调用专业 Agent
- [x] 8.3.2 实现 \_execute_correlation() 关联分析
- [x] 8.3.3 实现 \_generate_step_reflection() 步骤反思

### 8.4 响应生成

- [x] 8.4.1 实现 \_stream_synthesis() 流式生成最终回复
- [x] 8.4.2 实现 \_generate_suggestions() 生成后续问题建议

## 9. SSE API 端点

### 9.1 路由实现

- [x] 9.1.1 创建 POST /api/v1/chat/stream 端点
- [x] 9.1.2 实现 StreamingResponse 返回 SSE
- [x] 9.1.3 定义 SSE 事件格式（think/plan/action/observation/content/done）

### 9.2 请求处理

- [x] 9.2.1 解析 ChatStreamRequest（message + history）
- [x] 9.2.2 调用 ConversationalAgent.process_stream()
- [x] 9.2.3 错误处理和 event: error 返回

## 10. 前端 - 对话页面

### 10.1 页面结构

- [ ] 10.1.1 创建 ChatPage.tsx 页面组件
- [ ] 10.1.2 添加导航栏 "AI 对话" Tab
- [ ] 10.1.3 实现页面布局（消息列表 + 输入框）

### 10.2 消息组件

- [ ] 10.2.1 创建 MessageList 组件
- [ ] 10.2.2 创建 UserMessage 组件
- [ ] 10.2.3 创建 AssistantMessage 组件
- [ ] 10.2.4 创建 ThinkingChain 组件（可折叠思维链）

### 10.3 思维链展示

- [ ] 10.3.1 实现 ThoughtStep 组件 (💭)
- [ ] 10.3.2 实现 ActionStep 组件 (🔍)
- [ ] 10.3.3 实现 ObservationStep 组件 (📊)
- [ ] 10.3.4 实现折叠/展开动画

### 10.4 输入交互

- [ ] 10.4.1 创建 InputBox 组件（支持 Enter 发送）
- [ ] 10.4.2 创建 SuggestionChips 组件（快捷问题）
- [ ] 10.4.3 实现发送状态管理（禁用/加载中）

## 11. 前端 - SSE 通信

### 11.1 SSE Hook

- [ ] 11.1.1 创建 useChat() hook
- [ ] 11.1.2 实现 SSE 连接管理（fetch + ReadableStream）
- [ ] 11.1.3 实现事件解析和状态更新
- [ ] 11.1.4 实现流式内容拼接

### 11.2 状态管理

- [ ] 11.2.1 管理 messages[] 状态
- [ ] 11.2.2 管理 currentThinking[] 状态
- [ ] 11.2.3 管理 isStreaming 状态
- [ ] 11.2.4 管理 streamingContent 状态

### 11.3 持久化

- [ ] 11.3.1 创建 useChatStorage() hook
- [ ] 11.3.2 实现 LocalStorage 读写
- [ ] 11.3.3 实现 20 轮对话截断

## 12. 前端 - 类型定义

- [ ] 12.1 定义 Message 接口
- [ ] 12.2 定义 ThinkStep 接口
- [ ] 12.3 定义 SSEEvent 接口
- [ ] 12.4 定义 ChatState 接口

## 13. 集成测试

### 13.1 后端测试

- [ ] 13.1.1 测试单 Agent 问题处理
- [ ] 13.1.2 测试跨 Agent 问题（规划-执行）
- [ ] 13.1.3 测试 SSE 流式输出
- [ ] 13.1.4 测试执行计划并行优化

### 13.2 前端测试

- [ ] 13.2.1 测试 SSE 事件接收
- [ ] 13.2.2 测试思维链展示
- [ ] 13.2.3 测试多轮对话上下文
- [ ] 13.2.4 测试 LocalStorage 持久化

### 13.3 端到端测试

- [ ] 13.3.1 完整对话流程测试
- [ ] 13.3.2 刷新页面恢复对话测试
- [ ] 13.3.3 建议问题点击测试
