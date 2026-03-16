## 新增需求

### 需求: 组织健康度评分计算

系统必须基于真实数据计算组织健康度评分。

#### 场景: 计算综合健康度评分

- **当** 调用 /analysis/org-health API
- **则** 系统计算综合健康度评分 (0-100)
- **且** 评分公式为: health*score = 0.3 * utilization + 0.3 _ stability + 0.2 _ performance + 0.2 \_ structure

#### 场景: 计算稳定性评分

- **当** 计算稳定性评分
- **则** stability_score = 100 - (high_risk_ratio \* 100)
- **且** high_risk_ratio = (高风险员工 + 极高风险员工) / 总员工数

#### 场景: 计算编制利用率

- **当** 计算编制利用率
- **则** utilization_rate = 实际人数 / 预算人数 \* 100
- **且** 跨所有部门汇总计算

### 需求: TalentRisk API 格式修正

系统必须以对象格式返回风险分布。

#### 场景: 风险分布对象格式

- **当** 调用 /analysis/talent-risk API
- **则** 返回 risk_distribution 为对象格式
- **且** 格式为 {"low": N, "medium": N, "high": N, "critical": N}

### 需求: 招聘漏斗真实数据

系统必须基于数据库统计返回招聘漏斗数据。

#### 场景: 漏斗数据统计

- **当** 调用 /analysis/recruitment API
- **则** 返回 funnel_data 包含各阶段真实人数
- **且** 阶段包括: applied, screening, interview, offer, hired

### 需求: 前端使用真实数据

前端组件必须使用从 API 获取的真实数据。

#### 场景: Dashboard 健康度仪表盘

- **当** 渲染 Dashboard 页面的健康度仪表盘
- **则** 从 /analysis/org-health API 获取评分数据
- **且** GaugeChart 显示真实的 health_score

#### 场景: OrgHealth 页面指标

- **当** 渲染 OrgHealth 页面
- **则** 所有指标从 API 获取
- **且** 无硬编码数值

#### 场景: Recruitment 漏斗图

- **当** 渲染 Recruitment 页面的漏斗图
- **则** 使用 API 返回的 funnel_data
- **且** 无假计算 (如 x0.3, x0.15)
