# API 参考文档

## 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **API 文档**: `http://localhost:8000/docs` (Swagger UI)
- **Content-Type**: `application/json`

---

## 数据管理 API

### 生成测试数据

```http
POST /data/generate
```

**请求体**:

```json
{
  "employee_count": 10000,
  "include_historical_records": true
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "employees_created": 10000,
    "departments_created": 15,
    "performance_records": 30000,
    "recruitment_records": 25000,
    "duration_seconds": 45.2
  }
}
```

### 导入数据

```http
POST /data/import
Content-Type: multipart/form-data
```

**支持格式**: Excel (.xlsx, .xls), CSV

**字段映射**: 系统自动识别中英文表头

| 中文     | 英文        | 字段        |
| -------- | ----------- | ----------- |
| 员工编号 | employee_id | employee_id |
| 姓名     | name        | name        |
| 邮箱     | email       | email       |
| 部门     | department  | department  |
| 职位     | position    | position    |
| 入职日期 | hire_date   | hire_date   |

### 获取数据统计

```http
GET /data/stats
```

**响应**:

```json
{
  "success": true,
  "data": {
    "total_employees": 10000,
    "total_departments": 15,
    "total_performance_records": 30000,
    "total_recruitment_records": 25000,
    "data_quality_score": 95.2
  }
}
```

---

## 分析 API

### 执行综合分析

```http
POST /analysis/comprehensive
```

**请求体**:

```json
{
  "modules": ["recruitment", "performance", "talent_risk", "org_health"],
  "department": null,
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  }
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "task_id": "task_abc123",
    "status": "processing"
  }
}
```

### 查询分析状态

```http
GET /analysis/status/{task_id}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "task_id": "task_abc123",
    "status": "completed",
    "progress": 100,
    "result": { ... }
  }
}
```

### 招聘效能分析

```http
POST /analysis/recruitment
```

**响应**:

```json
{
  "success": true,
  "data": {
    "summary": {
      "total_positions": 150,
      "filled_positions": 120,
      "fill_rate": 80.0,
      "avg_time_to_hire": 32.5
    },
    "channel_effectiveness": [
      {
        "channel": "猎头",
        "applications": 500,
        "hires": 45,
        "conversion_rate": 9.0,
        "avg_cost": 25000,
        "roi_score": 85
      }
    ],
    "funnel": {
      "resume_screening": 2000,
      "phone_interview": 800,
      "onsite_interview": 300,
      "offer": 150,
      "hired": 120
    }
  }
}
```

### 绩效分析

```http
POST /analysis/performance
```

**响应**:

```json
{
  "success": true,
  "data": {
    "distribution": {
      "A": 15.2,
      "B+": 25.8,
      "B": 35.0,
      "C": 18.5,
      "D": 5.5
    },
    "okr_completion": {
      "average": 78.5,
      "by_department": [{ "department": "技术部", "completion": 82.3 }]
    },
    "manager_styles": [
      {
        "manager_id": "M001",
        "name": "张经理",
        "style": "严格型",
        "avg_team_rating": 3.2,
        "distribution_skew": -0.5
      }
    ]
  }
}
```

### 人才风险分析

```http
POST /analysis/talent-risk
```

**响应**:

```json
{
  "success": true,
  "data": {
    "overall_risk_score": 6.2,
    "risk_distribution": {
      "low": 65.0,
      "medium": 25.0,
      "high": 8.0,
      "critical": 2.0
    },
    "high_risk_employees": [
      {
        "employee_id": "E001",
        "name": "李明",
        "department": "技术部",
        "risk_score": 8.5,
        "risk_factors": ["薪资低于市场", "晋升停滞", "工作年限长"]
      }
    ],
    "high_potential_list": [
      {
        "employee_id": "E002",
        "name": "王芳",
        "potential_score": 92,
        "strengths": ["学习能力强", "绩效优秀", "领导力"]
      }
    ]
  }
}
```

### 组织健康分析

```http
POST /analysis/org-health
```

**响应**:

```json
{
  "success": true,
  "data": {
    "health_score": 78.5,
    "span_of_control": {
      "average": 6.2,
      "optimal_range": [5, 8],
      "outliers": [{ "manager": "张三", "direct_reports": 15 }]
    },
    "management_ratio": {
      "current": 12.5,
      "benchmark": 10.0,
      "assessment": "偏高"
    },
    "demographics": {
      "age_distribution": [{ "range": "25-30", "percentage": 35.2 }],
      "tenure_distribution": [{ "range": "0-1年", "percentage": 22.5 }]
    }
  }
}
```

---

## 报告 API

### 生成 CEO 报告

```http
POST /reports/ceo-report
```

**请求体**:

```json
{
  "analysis_task_id": "task_abc123",
  "format": "markdown"
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "report_id": "rpt_xyz789",
    "title": "组织智能分析报告 - 2024年12月",
    "content": "## 执行摘要\n\n...",
    "key_insights": [
      "技术部离职风险较高，需关注薪资竞争力",
      "招聘漏斗转化率偏低，建议优化面试流程"
    ],
    "action_items": [
      {
        "priority": "高",
        "action": "启动技术部薪资调研",
        "owner": "HR总监",
        "deadline": "2024-12-31"
      }
    ]
  }
}
```

### 导出报告

```http
GET /reports/{report_id}/export?format=pdf
```

**支持格式**: `pdf`, `docx`, `html`

---

## 智能对话 API

### 发送消息

```http
POST /chat/message
```

**请求体**:

```json
{
  "message": "技术部的离职风险有多高？",
  "context": {
    "current_page": "talent_risk"
  }
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "response": "根据分析结果，技术部的整体离职风险评分为 7.2（满分10），属于中高风险级别...",
    "suggestions": [
      "查看高风险员工详情",
      "对比其他部门风险"
    ],
    "data_references": [
      {
        "type": "chart",
        "chart_type": "bar",
        "data": { ... }
      }
    ]
  }
}
```

---

## WebSocket API

### 连接进度推送

```javascript
// 连接地址
ws://localhost:8000/ws/analysis/{task_id}

// 接收消息格式
{
  "type": "progress",
  "data": {
    "current_step": "分析招聘数据",
    "progress": 45,
    "estimated_remaining": 30
  }
}

// 完成消息
{
  "type": "completed",
  "data": {
    "result": { ... }
  }
}

// 错误消息
{
  "type": "error",
  "data": {
    "error": "分析失败: 数据不足"
  }
}
```

---

## 错误码

| 状态码 | 含义           |
| ------ | -------------- |
| 200    | 成功           |
| 400    | 请求参数错误   |
| 401    | 未授权         |
| 404    | 资源不存在     |
| 422    | 数据验证失败   |
| 500    | 服务器内部错误 |

**错误响应格式**:

```json
{
  "success": false,
  "error": "错误描述",
  "meta": {
    "request_id": "req_xxx"
  }
}
```

---

## 速率限制

- 默认: 100 请求/分钟
- 大数据分析: 10 请求/分钟
- 报告生成: 20 请求/分钟

超出限制返回 `429 Too Many Requests`
