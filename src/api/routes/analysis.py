"""
分析接口路由
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.data.mongodb import mongodb


router = APIRouter()


class AnalysisRequest(BaseModel):
    """分析请求"""
    period: Optional[str] = None
    department_id: Optional[str] = None
    filters: Optional[dict] = None
    include_insights: Optional[bool] = None  # 是否需要 AI 洞察
    task: Optional[str] = None  # 自然语言任务描述


class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool = True
    data: dict = {}
    meta: dict = {}


@router.post("/full")
async def full_analysis(request: AnalysisRequest):
    """全面分析"""
    # TODO: 调用主控 Agent 进行全面分析
    return {
        "success": True,
        "data": {
            "message": "Full analysis started",
            "status": "pending"
        },
        "meta": {
            "request_time": datetime.utcnow().isoformat()
        }
    }


@router.post("/recruitment")
async def recruitment_analysis(request: AnalysisRequest = AnalysisRequest()):
    """招聘分析"""
    # 1. 获取渠道统计
    channel_pipeline = [
        {"$group": {
            "_id": "$channel",
            "total": {"$sum": 1},
            "hired": {"$sum": {"$cond": [{"$eq": ["$stage", "hired"]}, 1, 0]}},
            "total_cost": {"$sum": "$channel_cost"}
        }},
        {"$sort": {"total": -1}}
    ]
    
    channel_results = await mongodb.recruitment_records.aggregate(channel_pipeline).to_list(100)
    
    # 2. 获取漏斗数据（各阶段人数）
    funnel_pipeline = [
        {"$group": {
            "_id": "$stage",
            "count": {"$sum": 1}
        }}
    ]
    
    funnel_results = await mongodb.recruitment_records.aggregate(funnel_pipeline).to_list(20)
    
    # 转换为对象格式，确保所有阶段都有值
    stage_mapping = {
        "applied": "简历",
        "screening": "筛选",
        "interview": "面试",
        "offer": "Offer",
        "hired": "入职",
        "rejected": "拒绝",
        "withdrawn": "撤回"
    }
    
    funnel_data = {}
    for r in funnel_results:
        stage = r["_id"]
        funnel_data[stage] = r["count"]
    
    # 构建有序的漏斗数据
    funnel_ordered = [
        {"name": "简历", "value": funnel_data.get("applied", 0)},
        {"name": "筛选", "value": funnel_data.get("screening", 0)},
        {"name": "面试", "value": funnel_data.get("interview", 0)},
        {"name": "Offer", "value": funnel_data.get("offer", 0)},
        {"name": "入职", "value": funnel_data.get("hired", 0)},
    ]
    
    total_records = sum(r["total"] for r in channel_results)
    total_hired = sum(r["hired"] for r in channel_results)
    
    return {
        "success": True,
        "data": {
            "channel_stats": channel_results,
            "funnel_data": funnel_ordered,
            "funnel_raw": funnel_data,
            "summary": {
                "total_channels": len(channel_results),
                "total_records": total_records,
                "total_hired": total_hired,
                "conversion_rate": round(total_hired / total_records * 100, 1) if total_records > 0 else 0
            }
        }
    }


@router.post("/performance")
async def performance_analysis(request: AnalysisRequest = AnalysisRequest()):
    """绩效分析"""
    try:
        # 检查数据库连接
        if mongodb._db is None:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        # 检查是否有数据
        total_count = await mongodb.performance_records.count_documents({})
        if total_count == 0:
            return {
                "success": True,
                "data": {
                    "distribution": [],
                    "period": request.period or "all",
                    "total_records": 0,
                    "message": "No performance records found. Please generate data first."
                }
            }
        
        pipeline = [
            {"$group": {
                "_id": "$rating",
                "count": {"$sum": 1},
                "avg_okr_score": {"$avg": "$okr_score"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        if request.period:
            pipeline.insert(0, {"$match": {"period": request.period}})
        
        results = await mongodb.performance_records.aggregate(pipeline).to_list(10)
        
        # 计算总数
        total = sum(r["count"] for r in results)
        
        # 添加百分比
        for r in results:
            r["percentage"] = round(r["count"] / total * 100, 1) if total > 0 else 0
        
        return {
            "success": True,
            "data": {
                "distribution": results,
                "period": request.period or "all",
                "total_records": total
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance analysis failed: {str(e)}")


@router.post("/talent-risk")
async def talent_risk_analysis(request: AnalysisRequest = AnalysisRequest()):
    """
    人才风险分析
    
    - 默认返回风险统计数据
    - 设置 include_insights=true 或 task 包含"分析"等关键词时，生成 AI 洞察
    """
    from src.agents.talent_risk import TalentRiskAgent
    
    # 判断是否使用 Agent（需要 AI 洞察时）
    use_agent = request.include_insights or (
        request.task and any(kw in request.task for kw in ["分析", "为什么", "建议", "原因"])
    )
    
    if use_agent:
        # 使用 Agent 分析（含 AI 洞察）
        agent = TalentRiskAgent()
        result = await agent.run(
            task=request.task or "分析人才风险",
            include_insights=request.include_insights,
            department_id=request.department_id
        )
        
        if result.success:
            return {
                "success": True,
                "data": result.data
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)
    
    # 简单查询模式（不调用 LLM）
    pipeline = [
        {"$group": {
            "_id": "$risk_level",
            "count": {"$sum": 1},
            "avg_score": {"$avg": "$turnover_risk_score"}
        }},
        {"$sort": {"avg_score": -1}}
    ]
    
    results = await mongodb.risk_assessments.aggregate(pipeline).to_list(10)
    
    # 转换为对象格式 {low: N, medium: N, high: N, critical: N}
    risk_distribution = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0
    }
    for r in results:
        if r["_id"] in risk_distribution:
            risk_distribution[r["_id"]] = r["count"]
    
    total_risk = sum(risk_distribution.values())
    high_risk_count = risk_distribution["high"] + risk_distribution["critical"]
    
    return {
        "success": True,
        "data": {
            "risk_distribution": risk_distribution,
            "high_risk_count": high_risk_count,
            "total_assessed": total_risk,
            "high_risk_ratio": round(high_risk_count / total_risk * 100, 1) if total_risk > 0 else 0
        }
    }


@router.post("/org-health")
async def org_health_analysis(request: AnalysisRequest = AnalysisRequest()):
    """组织健康分析"""
    # 1. 员工统计
    total_employees = await mongodb.employees.count_documents({"status": "active"})
    
    # 2. 部门统计（编制利用率）
    dept_stats = await mongodb.departments.aggregate([
        {"$project": {
            "_id": 0,  # 排除 MongoDB ObjectId，避免 JSON 序列化问题
            "department_id": 1,
            "name": 1,
            "headcount_budget": 1,
            "headcount_actual": 1,
            "utilization": {
                "$cond": [
                    {"$eq": ["$headcount_budget", 0]},
                    0,
                    {"$divide": ["$headcount_actual", "$headcount_budget"]}
                ]
            }
        }}
    ]).to_list(100)
    
    # 计算编制利用率
    total_budget = sum(d.get("headcount_budget", 0) for d in dept_stats)
    total_actual = sum(d.get("headcount_actual", 0) for d in dept_stats)
    utilization_rate = round((total_actual / total_budget * 100) if total_budget > 0 else 0, 1)
    
    # 3. 稳定性评分（基于风险分布）
    risk_pipeline = [
        {"$group": {
            "_id": "$risk_level",
            "count": {"$sum": 1}
        }}
    ]
    risk_results = await mongodb.risk_assessments.aggregate(risk_pipeline).to_list(10)
    risk_dist = {r["_id"]: r["count"] for r in risk_results}
    
    total_assessed = sum(risk_dist.values()) or 1
    high_risk = risk_dist.get("high", 0) + risk_dist.get("critical", 0)
    stability_score = round(100 - (high_risk / total_assessed * 100), 1)
    
    # 4. 绩效评分（基于绩效分布）
    perf_pipeline = [
        {"$group": {
            "_id": "$rating",
            "count": {"$sum": 1}
        }}
    ]
    perf_results = await mongodb.performance_records.aggregate(perf_pipeline).to_list(10)
    perf_dist = {r["_id"]: r["count"] for r in perf_results}
    
    total_perf = sum(perf_dist.values()) or 1
    # 绩效评分: A=100, B=80, C=60, D=40
    perf_weights = {"A": 100, "B+": 90, "B": 80, "B-": 70, "C": 60, "D": 40}
    weighted_score = sum(perf_dist.get(k, 0) * v for k, v in perf_weights.items())
    performance_score = round(weighted_score / total_perf, 1) if total_perf > 0 else 70
    
    # 5. 组织结构评分（基于管理幅度）
    # 假设理想管理幅度是 5-8，超出范围扣分
    manager_count = await mongodb.employees.count_documents({
        "status": "active",
        "level": {"$regex": "^M|manager|经理", "$options": "i"}
    })
    avg_span = total_employees / manager_count if manager_count > 0 else 6
    # 理想幅度 5-8，偏离越多分数越低
    if 5 <= avg_span <= 8:
        structure_score = 90
    elif 3 <= avg_span <= 10:
        structure_score = 75
    else:
        structure_score = 60
    
    # 6. 综合健康度评分
    # health_score = 0.3 * utilization + 0.3 * stability + 0.2 * performance + 0.2 * structure
    health_score = round(
        0.3 * min(utilization_rate, 100) +
        0.3 * stability_score +
        0.2 * performance_score +
        0.2 * structure_score,
        1
    )
    
    return {
        "success": True,
        "data": {
            "total_employees": total_employees,
            "department_stats": dept_stats,
            
            # 核心健康度指标
            "health_score": health_score,
            "stability_score": stability_score,
            "utilization_rate": utilization_rate,
            "performance_score": performance_score,
            "structure_score": structure_score,
            
            # 详细数据
            "headcount": {
                "budget": total_budget,
                "actual": total_actual
            },
            "risk_summary": {
                "high_risk_count": high_risk,
                "total_assessed": total_assessed
            },
            "avg_management_span": round(avg_span, 1)
        }
    }
