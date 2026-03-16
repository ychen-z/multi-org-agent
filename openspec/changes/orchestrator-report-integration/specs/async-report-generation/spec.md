## 新增需求

### 需求: 异步报告生成并返回任务ID

系统必须在收到报告生成请求时立即返回任务ID，允许客户端异步跟踪进度。

#### 场景: 成功创建任务

- **当** 客户端发送 POST /api/v1/reports/generate
- **则** 系统返回 HTTP 200，响应体为 {"success": true, "task_id": "<uuid>"}
- **且** task_id 是有效的 UUID

#### 场景: 任务在后台开始处理

- **当** task_id 返回给客户端后
- **则** 系统在后台开始执行 OrchestratorAgent.generate_strategic_report()
- **且** 客户端可以立即连接 WebSocket

### 需求: WebSocket 进度流推送

系统必须通过 WebSocket 连接实时推送进度更新。

#### 场景: 客户端连接进度流

- **当** 客户端连接到 WS /ws/analysis/{task_id}
- **则** 连接建立成功
- **且** 客户端开始接收进度消息

#### 场景: 进度消息格式

- **当** 系统完成一个处理步骤
- **则** 系统推送消息 {"type": "progress", "data": {"step": "<描述>", "progress": <0-100>}}

#### 场景: 完成消息

- **当** 报告生成成功完成
- **则** 系统推送消息 {"type": "completed", "data": {<完整报告>}}
- **且** WebSocket 连接保持 5 秒后关闭

#### 场景: 错误消息

- **当** 报告生成失败
- **则** 系统推送消息 {"type": "error", "data": {"error": "<错误信息>"}}

### 需求: 进度回调集成

系统必须通过进度回调将 OrchestratorAgent 与 WebSocket 管理器集成。

#### 场景: 进度回调调用

- **当** OrchestratorAgent 到达里程碑（数据治理、招聘分析、风险分析、交叉归因、LLM 生成）
- **则** 调用 progress_callback 传递步骤描述和百分比
- **且** WebSocket 管理器将进度推送给已连接的客户端

#### 场景: 回调是可选的

- **当** 调用 OrchestratorAgent.generate_strategic_report() 时未提供回调
- **则** 报告生成正常进行，不推送进度更新

### 需求: 任务状态查询

系统必须允许通过 REST API 查询任务状态。

#### 场景: 查询进行中的任务

- **当** 客户端发送 GET /api/v1/reports/status/{task_id}
- **且** 任务仍在运行
- **则** 系统返回 {"status": "running", "progress": <0-100>, "current_step": "<描述>"}

#### 场景: 查询已完成的任务

- **当** 客户端发送 GET /api/v1/reports/status/{task_id}
- **且** 任务已完成
- **则** 系统返回 {"status": "completed", "result": {<完整报告>}}

#### 场景: 查询失败的任务

- **当** 客户端发送 GET /api/v1/reports/status/{task_id}
- **且** 任务已失败
- **则** 系统返回 {"status": "failed", "error": "<错误信息>"}

#### 场景: 查询不存在的任务

- **当** 客户端发送 GET /api/v1/reports/status/{task_id}
- **且** task_id 不存在
- **则** 系统返回 HTTP 404，响应体为 {"error": "任务不存在"}
