## Why

当前各 Agent（TalentRisk、Recruitment、Performance 等）实际上是"伪 AI Agent"：

- 只做 MongoDB 数据查询
- "洞察" 是字符串拼接，不是 AI 生成
- "建议" 是硬编码的规则字典，不是个性化生成
- 只有在生成战略报告时才调用 LLM

用户在各分析页面感知不到 AI 的价值。

## What Changes

实现"按需调用 LLM"策略：

- 简单查询（数量、列表）→ 直接返回数据，不调用 LLM
- 需要洞察（分析、原因、建议）→ 数据 + LLM 生成洞察

## Capabilities

### New Capabilities

- `agent-llm-insights`: 各 Agent 按需调用 LLM 生成智能洞察

### Modified Capabilities

无

## Impact

- **TalentRiskAgent**: 添加 LLM 洞察生成能力
- **RecruitmentAgent**: 添加 LLM 洞察生成能力
- **PerformanceAgent**: 添加 LLM 洞察生成能力
- **OrgHealthAgent**: 添加 LLM 洞察生成能力
- **API 路由**: 返回结果中包含 ai_insights 字段
