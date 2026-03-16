## 1. 后端 API 修改

- [x] 1.1 修改 /talent-risk 返回格式为对象 {low, medium, high, critical}
- [x] 1.2 增强 /org-health 计算稳定性评分 stability_score
- [x] 1.3 增强 /org-health 计算编制利用率 utilization_rate
- [x] 1.4 增强 /org-health 计算综合健康度 health_score
- [x] 1.5 增强 /recruitment 添加 funnel_data 统计各阶段人数

## 2. 前端组件修改

- [x] 2.1 Dashboard.tsx 健康度仪表盘使用 API 数据
- [x] 2.2 Dashboard.tsx 稳定性仪表盘使用 API 数据
- [x] 2.3 Dashboard.tsx 利用率仪表盘使用 API 数据
- [x] 2.4 OrgHealth.tsx 所有指标使用 API 数据
- [x] 2.5 Recruitment.tsx 漏斗图使用 funnel_data

## 3. 测试验证

- [x] 3.1 验证后端 API 返回格式正确
- [x] 3.2 验证前端页面无硬编码数据
- [x] 3.3 验证健康度评分计算逻辑正确
