"""
数据接口路由
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from src.data.mongodb import mongodb
from src.data.generator import generate_and_insert_data
from src.data.cache import cache_manager


router = APIRouter()


class GenerateRequest(BaseModel):
    """数据生成请求"""
    employee_count: int = 10000
    recruitment_count: Optional[int] = None


@router.post("/generate")
async def generate_data(request: GenerateRequest):
    """生成模拟数据"""
    recruitment_count = request.recruitment_count or request.employee_count // 10
    
    stats = await generate_and_insert_data(
        employee_count=request.employee_count,
        recruitment_count=recruitment_count
    )
    
    # 清除分析缓存（数据已变更）
    cleared = await cache_manager.clear_cache()
    
    return {
        "success": True,
        "data": {**stats, "cache_cleared": cleared},
        "message": f"Generated {request.employee_count:,} employees"
    }


@router.post("/import")
async def import_data(file: UploadFile = File(...)):
    """导入数据文件"""
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    # TODO: 实现数据导入逻辑
    
    # 清除分析缓存（数据已变更）
    cleared = await cache_manager.clear_cache()
    
    return {
        "success": True,
        "message": f"File {file.filename} uploaded successfully",
        "data": {"filename": file.filename, "cache_cleared": cleared}
    }


@router.get("/stats")
async def get_data_stats():
    """获取数据统计"""
    stats = {
        "employees": await mongodb.employees.count_documents({}),
        "departments": await mongodb.departments.count_documents({}),
        "performance_records": await mongodb.performance_records.count_documents({}),
        "recruitment_records": await mongodb.recruitment_records.count_documents({}),
        "risk_assessments": await mongodb.risk_assessments.count_documents({}),
    }
    
    return {
        "success": True,
        "data": stats
    }


@router.get("/employees")
async def list_employees(
    page: int = 1,
    page_size: int = 20,
    department_id: Optional[str] = None,
    status: Optional[str] = None
):
    """获取员工列表"""
    query = {}
    if department_id:
        query["department_id"] = department_id
    if status:
        query["status"] = status
    
    skip = (page - 1) * page_size
    
    employees = await mongodb.employees.find(query).skip(skip).limit(page_size).to_list(page_size)
    total = await mongodb.employees.count_documents(query)
    
    # 转换 ObjectId 和日期
    for emp in employees:
        emp["_id"] = str(emp["_id"])
        if emp.get("birth_date"):
            emp["birth_date"] = emp["birth_date"].isoformat() if hasattr(emp["birth_date"], 'isoformat') else str(emp["birth_date"])
        if emp.get("hire_date"):
            emp["hire_date"] = emp["hire_date"].isoformat() if hasattr(emp["hire_date"], 'isoformat') else str(emp["hire_date"])
    
    return {
        "success": True,
        "data": {
            "items": employees,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/departments")
async def list_departments():
    """获取部门列表"""
    departments = await mongodb.departments.find({}).to_list(100)
    
    for dept in departments:
        dept["_id"] = str(dept["_id"])
    
    return {
        "success": True,
        "data": departments
    }
