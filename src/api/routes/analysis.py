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
    # 获取招聘数据统计
    pipeline = [
        {"$group": {
            "_id": "$channel",
            "total": {"$sum": 1},
            "hired": {"$sum": {"$cond": [{"$eq": ["$stage", "hired"]}, 1, 0]}},
            "total_cost": {"$sum": "$channel_cost"}
        }},
        {"$sort": {"total": -1}}
    ]
    
    results = await mongodb.recruitment_records.aggregate(pipeline).to_list(100)
    
    return {
        "success": True,
        "data": {
            "channel_stats": results,
            "summary": {
                "total_channels": len(results),
                "total_records": sum(r["total"] for r in results),
                "total_hired": sum(r["hired"] for r in results)
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
    """人才风险分析"""
    pipeline = [
        {"$group": {
            "_id": "$risk_level",
            "count": {"$sum": 1},
            "avg_score": {"$avg": "$turnover_risk_score"}
        }},
        {"$sort": {"avg_score": -1}}
    ]
    
    results = await mongodb.risk_assessments.aggregate(pipeline).to_list(10)
    
    return {
        "success": True,
        "data": {
            "risk_distribution": results,
            "high_risk_count": sum(r["count"] for r in results if r["_id"] in ["high", "critical"])
        }
    }


@router.post("/org-health")
async def org_health_analysis(request: AnalysisRequest = AnalysisRequest()):
    """组织健康分析"""
    # 员工统计
    total_employees = await mongodb.employees.count_documents({"status": "active"})
    
    # 部门统计
    dept_stats = await mongodb.departments.aggregate([
        {"$project": {
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
    
    return {
        "success": True,
        "data": {
            "total_employees": total_employees,
            "department_stats": dept_stats,
            "avg_utilization": sum(d.get("utilization", 0) for d in dept_stats) / len(dept_stats) if dept_stats else 0
        }
    }
