## Context

当前系统前端使用 React + TanStack Query 从后端 API 获取数据，但存在以下问题：

1. 部分页面使用硬编码假数据
2. 后端 API 返回格式与前端期望不一致

## Goals / Non-Goals

**Goals:**

- 所有前端显示的数据都来自后端 API
- 后端 API 返回格式与前端期望一致
- 健康度评分基于真实数据计算

**Non-Goals:**

- 不修改数据模型
- 不修改前端 UI 样式
- 不引入新的前端依赖

## Decisions

### 1. 健康度评分计算公式

**综合健康度评分 (0-100):**

```
health_score = 0.3 * utilization_score + 0.3 * stability_score + 0.2 * performance_score + 0.2 * structure_score
```

**稳定性评分:**

```
stability_score = 100 - (high_risk_ratio * 100)
其中 high_risk_ratio = (high_risk + critical_risk) / total_employees
```

**编制利用率:**

```
utilization_rate = actual_headcount / budget_headcount * 100
```

**绩效评分:**

```
performance_score = (A_ratio * 100 + B_ratio * 80 + C_ratio * 60 + D_ratio * 40) / total
```

**组织结构评分:**

```
structure_score = 基于管理幅度、层级比例计算
```

### 2. TalentRisk API 返回格式

从数组格式改为对象格式：

```json
// Before
{"risk_distribution": [{"_id": "low", "count": 100}, ...]}

// After
{"risk_distribution": {"low": 100, "medium": 50, "high": 30, "critical": 10}}
```

### 3. Recruitment 漏斗数据

从数据库统计各阶段真实人数：

```python
pipeline = [
    {"$group": {"_id": "$stage", "count": {"$sum": 1}}}
]
# 返回: {applied: N, screening: N, interview: N, offer: N, hired: N}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端组件                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Dashboard.tsx                                                  │
│  ├── useQuery("org-health") ──► health_score, stability_score  │
│  └── GaugeChart value={health_score}  ✅ 真实数据              │
│                                                                 │
│  OrgHealth.tsx                                                  │
│  └── useQuery("org-health") ──► 所有健康度指标                  │
│                                                                 │
│  Recruitment.tsx                                                │
│  └── useQuery("recruitment") ──► funnel_data                   │
│                                                                 │
│  TalentRisk.tsx                                                 │
│  └── useQuery("talent-risk") ──► risk_distribution (对象格式)  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         后端 API                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  POST /analysis/org-health                                      │
│  └── 返回: health_score, stability_score, utilization_rate,    │
│            performance_score, structure_score                   │
│                                                                 │
│  POST /analysis/recruitment                                     │
│  └── 返回: channel_stats, summary, funnel_data                 │
│                                                                 │
│  POST /analysis/talent-risk                                     │
│  └── 返回: risk_distribution: {low, medium, high, critical}    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Open Questions

无
