## Context

当前系统有完整的 Agent 层实现（OrchestratorAgent + 5 个子 Agent），但 API 路由绕过了 Agent 层，直接查询 MongoDB。这导致：

- 6 个 Agent 的 LLM 能力完全未使用
- 交叉归因分析（招聘渠道→员工绩效、绩效→离职风险、管理者→团队稳定性）未被调用
- 报告只是简单数据聚合，没有 AI 洞察

现有基础设施：

- `src/agents/orchestrator.py`: 已实现 `generate_strategic_report()`, `cross_analysis()` 等方法
- `src/api/websocket.py`: 已实现 `ConnectionManager` 支持进度推送
- `src/llm/`: 多 LLM Provider 支持（OpenAI/Qwen/GLM/Ollama）

## Goals / Non-Goals

**Goals:**

- API 调用 OrchestratorAgent 生成报告，而不是直接查 MongoDB
- 报告生成使用异步模式 + WebSocket 进度推送（预计 30-60 秒）
- Agent 在关键分析点调用 LLM 生成智能洞察
- 为耗时的交叉归因分析添加缓存（TTL 1小时）

**Non-Goals:**

- 不修改 Agent 的核心分析逻辑（已实现）
- 不引入新的外部依赖（Redis 等）
- 不修改前端 UI 组件（仅更新 API 调用方式）
- 不实现报告的增量更新（每次全量生成）

## Decisions

### 1. 异步任务管理：FastAPI BackgroundTasks

**选择**: 使用 FastAPI 内置 BackgroundTasks
**备选**: Celery + Redis

**理由**:

- 系统已使用 FastAPI，无需引入新依赖
- 报告生成是低频操作（每用户每天几次），不需要分布式任务队列
- BackgroundTasks 与 WebSocket 集成简单

```python
@router.post("/generate")
async def generate_report(background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_report_task, task_id)
    return {"task_id": task_id}
```

### 2. 进度推送机制：函数回调

**选择**: OrchestratorAgent 接受 `progress_callback` 参数
**备选**: 事件发布/订阅

**理由**:

- 简单直接，无需引入事件系统
- 与现有 WebSocket Manager 无缝集成

```python
async def generate_strategic_report(
    self,
    progress_callback: Optional[Callable[[str, int], Awaitable[None]]] = None
):
    if progress_callback:
        await progress_callback("数据治理分析中...", 10)
    # ...
```

### 3. 缓存存储：MongoDB analysis_cache 集合

**选择**: 在 MongoDB 中创建缓存集合，使用 TTL 索引自动过期
**备选**: Redis, 内存缓存

**理由**:

- 系统已有 MongoDB，无新依赖
- TTL 索引自动清理过期数据
- 支持多进程/重启后持久化

```javascript
// 集合设计
{
  "_id": "cross_analysis_2024-03-16-10",
  "type": "cross_analysis",
  "data": { ... },
  "created_at": ISODate(...),
  "expires_at": ISODate(...)  // TTL 索引字段
}

// TTL 索引
db.analysis_cache.createIndex(
  { "expires_at": 1 },
  { expireAfterSeconds: 0 }
)
```

### 4. LLM 调用策略：关键节点 + 最终汇总

**选择**: 在交叉分析完成后调用 LLM 生成洞察，最终报告由 LLM 生成 Markdown
**备选**: 每个子 Agent 都调用 LLM

**理由**:

- 减少 LLM 调用次数，降低成本和延迟
- 让 LLM 看到完整数据后再生成洞察，质量更高
- 控制在 2-3 次 LLM 调用内完成

**LLM 调用点**:

1. `cross_analysis()` 完成后 → 生成交叉归因洞察
2. `generate_strategic_report()` 最后 → 生成 CEO 报告 Markdown

## Risks / Trade-offs

### [风险] LLM 调用可能失败或超时

**缓解**:

- 设置 LLM 调用超时（30秒）
- 失败时回退到规则生成的报告（无 AI 洞察版）
- 错误信息通过 WebSocket 推送给用户

### [风险] 500万数据下交叉归因查询慢

**缓解**:

- 缓存结果，避免重复计算
- 确保 MongoDB 索引覆盖关键字段
- 考虑对大数据集采样分析

### [权衡] 缓存一致性 vs 实时性

**决定**:

- 接受 1 小时的数据延迟
- 提供 `force_refresh=true` 参数强制刷新
- 数据导入后自动清除相关缓存

### [权衡] LLM 成本 vs 洞察质量

**决定**:

- 控制在 2-3 次调用
- 使用结构化 prompt 确保输出质量
- 支持配置使用本地模型（Ollama）降低成本

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│                                                                 │
│   1. POST /reports/generate ──► {"task_id": "abc"}              │
│   2. WS /ws/analysis/abc ──► 实时进度                           │
│   3. 完成后收到完整报告                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                           │
│                                                                 │
│   POST /reports/generate                                        │
│   ├── 创建 task_id                                              │
│   ├── BackgroundTasks.add_task(run_report_task)                 │
│   └── 返回 task_id                                              │
│                                                                 │
│   run_report_task(task_id):                                     │
│   ├── orchestrator = OrchestratorAgent()                        │
│   ├── report = await orchestrator.generate_strategic_report(    │
│   │       progress_callback=lambda s,p: ws_manager.push(...)    │
│   │   )                                                         │
│   └── await ws_manager.complete_task(task_id, report)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   OrchestratorAgent                              │
│                                                                 │
│   generate_strategic_report(progress_callback):                 │
│   ├── callback("数据治理中...", 10)                             │
│   ├── DataGovernanceAgent.run()                                 │
│   ├── callback("招聘分析中...", 25)                             │
│   ├── RecruitmentAgent.run()                                    │
│   ├── callback("风险分析中...", 40)                             │
│   ├── TalentRiskAgent.run()                                     │
│   ├── callback("交叉归因中...", 55)                             │
│   ├── cross_analysis() ──► 检查缓存 / 执行 / 存缓存            │
│   ├── callback("AI分析中...", 75)                               │
│   ├── self.chat("生成交叉分析洞察...")  ◄── LLM 调用           │
│   ├── callback("生成报告中...", 90)                             │
│   ├── self.chat("生成CEO报告...")  ◄── LLM 调用                │
│   └── return report                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MongoDB                                     │
│                                                                 │
│   analysis_cache (TTL索引)                                       │
│   ├── cross_analysis_2024-03-16-10                              │
│   └── ...                                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Open Questions

1. **前端如何处理报告生成超时？**
   - 建议：显示进度条，超过 2 分钟提示用户可能需要稍后查看

2. **是否需要保存历史报告？**
   - 当前设计：不保存，每次生成
   - 可选：保存最近 N 份报告供查看
