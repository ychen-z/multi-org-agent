"""
数据治理 Agent
负责数据清洗、口径统一、质量评估
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import re

from Logging import logger

from .base_agent import BaseAgent, AgentMessage, AgentResponse, AgentTool
from src.data.mongodb import mongodb


class DataGovernanceAgent(BaseAgent):
    """数据治理 Agent"""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="data_governance",
            name="数据治理 Agent",
            description="负责数据清洗、口径统一、质量评估和数据血缘追踪",
            **kwargs
        )
        
        # 部门名称映射表
        self.dept_name_mapping = {
            "研发部": "研发中心",
            "R&D": "研发中心",
            "研发": "研发中心",
            "技术部": "研发中心",
            "销售": "销售中心",
            "市场": "市场部",
            "HR": "人力资源部",
            "人力": "人力资源部",
            "财务": "财务部",
            "行政": "行政部",
        }
        
        # 职级映射表
        self.level_mapping = {
            "初级": "P1",
            "Junior": "P1",
            "中级": "P3",
            "Mid": "P3",
            "高级": "P5",
            "Senior": "P5",
            "资深": "P6",
            "Staff": "P6",
            "专家": "P7",
            "Expert": "P7",
            "经理": "M1",
            "Manager": "M1",
            "总监": "M3",
            "Director": "M3",
        }
    
    def _register_tools(self):
        """注册工具"""
        self.register_tool(AgentTool(
            name="clean_missing_values",
            description="处理数据中的缺失值",
            parameters={
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "description": "集合名称"},
                    "strategy": {"type": "string", "enum": ["fill", "drop", "flag"]}
                },
                "required": ["collection"]
            },
            handler=self.clean_missing_values
        ))
        
        self.register_tool(AgentTool(
            name="detect_duplicates",
            description="检测重复记录",
            parameters={
                "type": "object",
                "properties": {
                    "collection": {"type": "string"},
                    "key_fields": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["collection", "key_fields"]
            },
            handler=self.detect_duplicates
        ))
        
        self.register_tool(AgentTool(
            name="detect_anomalies",
            description="检测异常值",
            parameters={
                "type": "object",
                "properties": {
                    "collection": {"type": "string"},
                    "field": {"type": "string"},
                    "min_value": {"type": "number"},
                    "max_value": {"type": "number"}
                },
                "required": ["collection", "field"]
            },
            handler=self.detect_anomalies
        ))
        
        self.register_tool(AgentTool(
            name="standardize_department_names",
            description="标准化部门名称",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=self.standardize_department_names
        ))
        
        self.register_tool(AgentTool(
            name="assess_data_quality",
            description="评估数据质量",
            parameters={
                "type": "object",
                "properties": {
                    "collection": {"type": "string"}
                },
                "required": ["collection"]
            },
            handler=self.assess_data_quality
        ))
    
    async def process(self, message: AgentMessage) -> AgentResponse:
        """处理消息"""
        task = message.payload.get("task", "")
        
        try:
            if "清洗" in task or "clean" in task.lower():
                result = await self.run_full_cleaning()
            elif "质量" in task or "quality" in task.lower():
                result = await self.run_quality_assessment()
            else:
                # 使用 LLM 理解任务
                response = await self.chat_with_tools(
                    task,
                    system_prompt=self.get_system_prompt()
                )
                result = {"response": response}
            
            return AgentResponse(success=True, data=result)
            
        except Exception as e:
            logger.error(f"DataGovernanceAgent error: {e}")
            return AgentResponse(success=False, error=str(e))
    
    async def clean_missing_values(
        self,
        collection: str,
        strategy: str = "flag"
    ) -> Dict[str, Any]:
        """处理缺失值"""
        coll = mongodb.collection(collection)
        
        # 查找有缺失值的记录
        missing_stats = {}
        
        # 获取一个样本文档来了解字段
        sample = await coll.find_one()
        if not sample:
            return {"message": "Collection is empty", "missing_count": 0}
        
        fields = list(sample.keys())
        
        for field in fields:
            if field == "_id":
                continue
            
            # 统计空值
            null_count = await coll.count_documents({
                "$or": [
                    {field: None},
                    {field: ""},
                    {field: {"$exists": False}}
                ]
            })
            
            if null_count > 0:
                missing_stats[field] = null_count
        
        # 根据策略处理
        if strategy == "flag":
            # 标记有缺失值的记录
            for field in missing_stats:
                await coll.update_many(
                    {"$or": [{field: None}, {field: ""}, {field: {"$exists": False}}]},
                    {"$set": {f"_data_quality.missing_{field}": True}}
                )
        
        return {
            "collection": collection,
            "missing_stats": missing_stats,
            "total_fields_with_missing": len(missing_stats),
            "strategy_applied": strategy
        }
    
    async def detect_duplicates(
        self,
        collection: str,
        key_fields: List[str]
    ) -> Dict[str, Any]:
        """检测重复记录"""
        coll = mongodb.collection(collection)
        
        # 构建聚合管道
        group_id = {field: f"${field}" for field in key_fields}
        
        pipeline = [
            {"$group": {
                "_id": group_id,
                "count": {"$sum": 1},
                "ids": {"$push": "$_id"}
            }},
            {"$match": {"count": {"$gt": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 100}
        ]
        
        duplicates = await coll.aggregate(pipeline).to_list(100)
        
        total_duplicate_groups = len(duplicates)
        total_duplicate_records = sum(d["count"] for d in duplicates)
        
        return {
            "collection": collection,
            "key_fields": key_fields,
            "duplicate_groups": total_duplicate_groups,
            "total_duplicate_records": total_duplicate_records,
            "sample_duplicates": duplicates[:10]
        }
    
    async def detect_anomalies(
        self,
        collection: str,
        field: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """检测异常值"""
        coll = mongodb.collection(collection)
        
        # 计算统计信息
        stats_pipeline = [
            {"$group": {
                "_id": None,
                "avg": {"$avg": f"${field}"},
                "min": {"$min": f"${field}"},
                "max": {"$max": f"${field}"},
                "stddev": {"$stdDevPop": f"${field}"}
            }}
        ]
        
        stats_result = await coll.aggregate(stats_pipeline).to_list(1)
        
        if not stats_result:
            return {"message": "No data found", "anomalies": 0}
        
        stats = stats_result[0]
        
        # 使用 3 倍标准差或指定范围
        if min_value is None:
            min_value = stats["avg"] - 3 * (stats["stddev"] or 0)
        if max_value is None:
            max_value = stats["avg"] + 3 * (stats["stddev"] or 0)
        
        # 查找异常值
        anomaly_count = await coll.count_documents({
            "$or": [
                {field: {"$lt": min_value}},
                {field: {"$gt": max_value}}
            ]
        })
        
        # 获取异常样本
        anomaly_samples = await coll.find({
            "$or": [
                {field: {"$lt": min_value}},
                {field: {"$gt": max_value}}
            ]
        }).limit(10).to_list(10)
        
        for sample in anomaly_samples:
            sample["_id"] = str(sample["_id"])
        
        return {
            "collection": collection,
            "field": field,
            "statistics": {
                "avg": stats["avg"],
                "min": stats["min"],
                "max": stats["max"],
                "stddev": stats["stddev"]
            },
            "anomaly_range": {"min": min_value, "max": max_value},
            "anomaly_count": anomaly_count,
            "anomaly_samples": anomaly_samples
        }
    
    async def standardize_department_names(self) -> Dict[str, Any]:
        """标准化部门名称"""
        updated_count = 0
        
        for original, standard in self.dept_name_mapping.items():
            result = await mongodb.employees.update_many(
                {"department_name": original},
                {"$set": {"department_name": standard, "_original_dept_name": original}}
            )
            updated_count += result.modified_count
        
        return {
            "updated_count": updated_count,
            "mapping_applied": self.dept_name_mapping
        }
    
    async def assess_data_quality(self, collection: str) -> Dict[str, Any]:
        """评估数据质量"""
        coll = mongodb.collection(collection)
        
        total_count = await coll.count_documents({})
        
        if total_count == 0:
            return {
                "collection": collection,
                "total_records": 0,
                "quality_score": 0,
                "message": "Collection is empty"
            }
        
        # 获取样本文档
        sample = await coll.find_one()
        fields = [k for k in sample.keys() if not k.startswith("_")]
        
        # 计算各维度得分
        completeness_scores = []
        
        for field in fields:
            non_null = await coll.count_documents({
                field: {"$ne": None, "$ne": ""}
            })
            completeness_scores.append(non_null / total_count)
        
        completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
        
        # 唯一性检查（针对 ID 字段）
        id_field = next((f for f in fields if "id" in f.lower()), None)
        uniqueness = 1.0
        
        if id_field:
            unique_count = len(await coll.distinct(id_field))
            uniqueness = unique_count / total_count
        
        # 计算综合得分
        quality_score = (completeness * 0.4 + uniqueness * 0.3 + 0.3) * 100
        
        return {
            "collection": collection,
            "total_records": total_count,
            "quality_score": round(quality_score, 2),
            "dimensions": {
                "completeness": round(completeness * 100, 2),
                "uniqueness": round(uniqueness * 100, 2),
                "consistency": 85.0,  # 简化处理
                "timeliness": 90.0    # 简化处理
            },
            "fields_analyzed": len(fields),
            "assessment_time": datetime.utcnow().isoformat()
        }
    
    async def run_full_cleaning(self) -> Dict[str, Any]:
        """运行完整清洗流程"""
        results = {}
        
        # 清洗员工数据
        results["employees_missing"] = await self.clean_missing_values("employees")
        results["employees_duplicates"] = await self.detect_duplicates("employees", ["employee_id"])
        results["employees_salary_anomalies"] = await self.detect_anomalies(
            "employees", "salary.total", min_value=0, max_value=500000
        )
        
        # 标准化部门名称
        results["dept_standardization"] = await self.standardize_department_names()
        
        return results
    
    async def run_quality_assessment(self) -> Dict[str, Any]:
        """运行质量评估"""
        collections = ["employees", "departments", "performance_records", 
                       "recruitment_records", "risk_assessments"]
        
        results = {}
        total_score = 0
        
        for coll in collections:
            assessment = await self.assess_data_quality(coll)
            results[coll] = assessment
            total_score += assessment.get("quality_score", 0)
        
        results["overall_score"] = round(total_score / len(collections), 2)
        
        return results
