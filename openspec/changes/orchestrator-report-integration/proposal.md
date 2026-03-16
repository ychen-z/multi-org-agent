## Why

当前 API 路由直接查询 MongoDB 返回简单聚合数据，没有真正调用 OrchestratorAgent。这意味着：

- 报告生成只是数据聚合，没有 AI 智能分析
- 交叉归因能力（招聘→绩效、绩效→离职、管理者→团队）完全未被使用
- LLM 层空转，所有 Agent 实际上没有发挥作用

需要将 API 层与 Agent 层打通，让报告生成真正调用 OrchestratorAgent，并通过 WebSocket 实时推送进度。

## What Changes

- **异步报告生成**: `POST /reports/generate` 改为异步模式，返回 `task_id`，通过 WebSocket 推送进度
- **Agent 调用 LLM**: 在关键分析点调用 `self.chat()` 生成 AI 洞察，最终报告由 LLM 生成 Markdown
- **交叉归因缓存**: 为耗时的交叉归因分析添加 MongoDB 缓存层（TTL 1小时）
- **进度回调机制**: OrchestratorAgent 支持 `progress_callback` 参数，在每个阶段报告进度

## Capabilities

### New Capabilities

- `async-report-generation`: 异步报告生成流程，包含后台任务管理、进度推送、结果缓存
- `agent-llm-insights`: Agent 调用 LLM 生成智能洞察，包含系统提示词设计和分析结果增强
- `cross-analysis-cache`: 交叉归因分析缓存层，包含 MongoDB TTL 索引和缓存失效策略

### Modified Capabilities

<!-- 无现有 spec 需要修改 -->

## Impact

- **API 路由**: `src/api/routes/reports.py` - 改为异步模式
- **Orchestrator**: `src/agents/orchestrator.py` - 添加进度回调、增强 LLM 调用
- **子 Agent**: `src/agents/*.py` - 在关键分析点添加 LLM 调用
- **WebSocket**: `src/api/websocket.py` - 与后台任务集成
- **MongoDB**: 新增 `analysis_cache` 集合
- **前端**: 需要处理异步任务流程和 WebSocket 连接
