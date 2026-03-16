## Why

当前前端页面存在多处硬编码的假数据，以及后端 API 返回的数据结构与前端期望不匹配的问题：

1. **Dashboard 健康度仪表盘** - 综合评分(78)、稳定性(85)、利用率(92) 都是硬编码
2. **OrgHealth 页面** - 所有健康度指标都是硬编码
3. **Recruitment 漏斗数据** - 面试数、Offer 数是假计算 (x0.3, x0.15)
4. **TalentRisk API 格式** - 返回数组格式，前端期望对象格式

需要将所有假数据替换为从后端 API 获取的真实数据。

## What Changes

### 后端 API 修改

- 修复 `/talent-risk` 返回格式：数组 → 对象
- 增强 `/org-health` 返回：添加 health_score, stability_score, utilization_rate
- 增强 `/recruitment` 返回：添加 funnel_data（各阶段真实统计）

### 前端组件修改

- Dashboard.tsx：健康度仪表盘使用真实数据
- OrgHealth.tsx：所有指标使用真实数据
- Recruitment.tsx：漏斗图使用真实数据

## Capabilities

### New Capabilities

- `org-health-metrics`: 组织健康度计算和返回，包含综合评分、稳定性、利用率

### Modified Capabilities

- 无

## Impact

- **后端**: `src/api/routes/analysis.py` - 修改 3 个 API 端点
- **前端**: `frontend/src/pages/Dashboard.tsx`, `OrgHealth.tsx`, `Recruitment.tsx` - 替换硬编码数据
