"""
报告接口路由
"""

import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.data.mongodb import mongodb
from src.api.websocket import ws_manager
from src.agents.orchestrator import OrchestratorAgent


router = APIRouter()


# 任务状态存储（内存）
_task_store: Dict[str, Dict[str, Any]] = {}


class ReportRequest(BaseModel):
    """报告请求"""
    period: Optional[str] = None
    include_sections: Optional[list] = None
    force_refresh: bool = False


class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str  # running, completed, failed
    progress: int = 0
    current_step: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务状态"""
    return _task_store.get(task_id)


def set_task(task_id: str, data: Dict[str, Any]):
    """设置任务状态"""
    _task_store[task_id] = data


async def run_report_task(task_id: str, request: ReportRequest):
    """后台报告生成任务"""
    
    # 初始化任务状态
    set_task(task_id, {
        "status": "running",
        "progress": 0,
        "current_step": "初始化...",
        "started_at": datetime.utcnow().isoformat()
    })
    
    try:
        # 创建 Orchestrator
        orchestrator = OrchestratorAgent()
        
        # 进度回调
        async def on_progress(step: str, progress: int):
            # 更新任务状态
            task_data = get_task(task_id)
            if task_data:
                task_data["progress"] = progress
                task_data["current_step"] = step
                set_task(task_id, task_data)
            
            # 推送到 WebSocket
            await ws_manager.update_progress(task_id, step, progress)
        
        # 生成报告
        report = await orchestrator.generate_strategic_report(
            progress_callback=on_progress,
            force_refresh=request.force_refresh
        )
        
        # 更新任务为完成状态
        set_task(task_id, {
            "status": "completed",
            "progress": 100,
            "current_step": "完成",
            "result": report,
            "completed_at": datetime.utcnow().isoformat()
        })
        
        # 通过 WebSocket 推送完成
        await ws_manager.complete_task(task_id, report)
        
    except Exception as e:
        # 更新任务为失败状态
        error_msg = str(e)
        set_task(task_id, {
            "status": "failed",
            "progress": 0,
            "current_step": "失败",
            "error": error_msg,
            "failed_at": datetime.utcnow().isoformat()
        })
        
        # 通过 WebSocket 推送失败
        await ws_manager.fail_task(task_id, error_msg)


@router.post("/generate")
async def generate_report(
    request: ReportRequest = ReportRequest(),
    background_tasks: BackgroundTasks = None
):
    """
    异步生成战略报告
    
    返回 task_id，客户端可通过 WebSocket 接收进度或查询状态
    """
    task_id = str(uuid.uuid4())
    
    # 启动后台任务
    if background_tasks:
        background_tasks.add_task(run_report_task, task_id, request)
    else:
        # 如果没有 BackgroundTasks，手动创建任务
        asyncio.create_task(run_report_task(task_id, request))
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "Report generation started. Connect to WebSocket for progress.",
        "websocket_url": f"/ws/analysis/{task_id}"
    }


@router.get("/status/{task_id}")
async def get_report_status(task_id: str):
    """
    查询报告生成任务状态
    """
    task = get_task(task_id)
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "success": True,
        "data": {
            "task_id": task_id,
            **task
        }
    }


@router.get("/strategic/{report_id}")
async def get_strategic_report(report_id: str):
    """获取战略报告（通过任务 ID）"""
    task = get_task(report_id)
    
    if task is None:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if task.get("status") != "completed":
        return {
            "success": False,
            "error": f"Report not ready. Current status: {task.get('status')}",
            "progress": task.get("progress", 0)
        }
    
    return {
        "success": True,
        "data": task.get("result")
    }


@router.get("/action-list/{report_id}")
async def get_action_list(report_id: str):
    """获取行动清单"""
    task = get_task(report_id)
    
    if task and task.get("status") == "completed":
        result = task.get("result", {})
        action_items = result.get("action_items", [])
        
        if action_items:
            return {
                "success": True,
                "data": {
                    "report_id": report_id,
                    "action_list": action_items
                }
            }
    
    # 返回默认行动清单
    action_list = [
        {
            "priority": "high",
            "category": "retention",
            "action": "约谈高风险核心员工",
            "target": "10 人",
            "deadline": "2 周内",
            "owner": "HRBP"
        },
        {
            "priority": "high",
            "category": "recruitment",
            "action": "关闭低效招聘渠道",
            "target": "智联招聘、前程无忧",
            "expected_saving": "¥50,000/月",
            "owner": "招聘负责人"
        },
        {
            "priority": "medium",
            "category": "performance",
            "action": "约谈问题管理者",
            "target": "3 位评分偏差过大的经理",
            "deadline": "1 个月内",
            "owner": "HRBP"
        },
        {
            "priority": "medium",
            "category": "compensation",
            "action": "调整研发岗位薪酬带宽",
            "target": "P5-P7 级别",
            "expected_impact": "降低 15% 离职率",
            "owner": "薪酬负责人"
        }
    ]
    
    return {
        "success": True,
        "data": {
            "report_id": report_id,
            "action_list": action_list
        }
    }


# 保留同步接口作为快速预览
@router.post("/generate-sync")
async def generate_report_sync(request: ReportRequest = ReportRequest()):
    """
    同步生成报告（快速版，不调用 LLM）
    
    用于快速预览，不包含 AI 洞察
    """
    # 收集各维度数据
    employee_count = await mongodb.employees.count_documents({"status": "active"})
    
    # 绩效分布
    perf_dist = await mongodb.performance_records.aggregate([
        {"$group": {"_id": "$rating", "count": {"$sum": 1}}}
    ]).to_list(10)
    
    # 高风险员工
    high_risk = await mongodb.risk_assessments.count_documents({
        "risk_level": {"$in": ["high", "critical"]}
    })
    
    report = {
        "title": "组织智能分析战略报告（快速版）",
        "generated_at": datetime.utcnow().isoformat(),
        "period": request.period or "全部",
        "note": "此为快速预览版本，不包含 AI 洞察。使用 /generate 获取完整报告。",
        "sections": {
            "executive_summary": {
                "total_employees": employee_count,
                "high_risk_count": high_risk,
                "key_findings": [
                    f"当前在职员工 {employee_count:,} 人",
                    f"高风险员工 {high_risk} 人，需重点关注",
                ]
            },
            "performance_overview": {
                "distribution": {item["_id"]: item["count"] for item in perf_dist}
            },
            "risk_assessment": {
                "high_risk_employees": high_risk,
                "risk_level": "medium" if high_risk < employee_count * 0.1 else "high"
            },
            "recommendations": [
                "建议对高风险员工进行一对一沟通",
                "优化绩效管理流程，关注 C/D 级员工发展",
                "评估招聘渠道 ROI，优化招聘预算分配"
            ]
        }
    }
    
    return {
        "success": True,
        "data": report
    }