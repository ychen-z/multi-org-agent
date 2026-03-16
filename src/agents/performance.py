"""
绩效目标 Agent
负责 OKR 分析、绩效分布、管理者风格识别
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from loguru import logger

from .base_agent import BaseAgent, AgentMessage, AgentResponse, AgentTool
from src.data.mongodb import mongodb


class PerformanceAgent(BaseAgent):
    """绩效目标 Agent"""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="performance",
            name="绩效目标 Agent",
            description="分析 OKR 完成度、绩效分布、管理者风格，提供绩效管理优化建议",
            **kwargs
        )
        
        # 强制分布标准
        self.forced_distribution = {
            "S": 0.05,  # 5%
            "A": 0.20,  # 20%
            "B": 0.50,  # 50%
            "C": 0.20,  # 20%
            "D": 0.05   # 5%
        }
        
        self.rating_order = ["S", "A", "B", "C", "D"]
    
    def _register_tools(self):
        """注册工具"""
        self.register_tool(AgentTool(
            name="analyze_performance_distribution",
            description="分析绩效分布",
            parameters={
                "type": "object",
                "properties": {
                    "period": {"type": "string"},
                    "department_id": {"type": "string"}
                }
            },
            handler=self.analyze_performance_distribution
        ))
        
        self.register_tool(AgentTool(
            name="analyze_okr_completion",
            description="分析 OKR 完成度",
            parameters={
                "type": "object",
                "properties": {"period": {"type": "string"}}
            },
            handler=self.analyze_okr_completion
        ))
        
        self.register_tool(AgentTool(
            name="analyze_manager_style",
            description="分析管理者评分风格",
            parameters={"type": "object", "properties": {}},
            handler=self.analyze_manager_style
        ))
        
        self.register_tool(AgentTool(
            name="check_forced_distribution",
            description="检查强制分布合规性",
            parameters={
                "type": "object",
                "properties": {"period": {"type": "string"}}
            },
            handler=self.check_forced_distribution
        ))
        
        self.register_tool(AgentTool(
            name="detect_performance_inflation",
            description="检测绩效通胀",
            parameters={"type": "object", "properties": {}},
            handler=self.detect_performance_inflation
        ))
    
    async def process(self, message: AgentMessage) -> AgentResponse:
        """处理消息"""
        task = message.payload.get("task", "")
        
        try:
            if "分布" in task:
                result = await self.analyze_performance_distribution()
            elif "OKR" in task.upper() or "完成" in task:
                result = await self.analyze_okr_completion()
            elif "管理者" in task or "风格" in task:
                result = await self.analyze_manager_style()
            elif "强制" in task or "合规" in task:
                result = await self.check_forced_distribution()
            elif "通胀" in task:
                result = await self.detect_performance_inflation()
            else:
                result = await self.run_full_analysis()
            
            return AgentResponse(success=True, data=result)
        except Exception as e:
            logger.error(f"PerformanceAgent error: {e}")
            return AgentResponse(success=False, error=str(e))
    
    async def analyze_performance_distribution(
        self,
        period: Optional[str] = None,
        department_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析绩效分布"""
        
        match_stage = {}
        if period:
            match_stage["period"] = period
        
        # 整体分布
        pipeline = [
            {"$match": match_stage} if match_stage else {"$match": {}},
            {"$group": {
                "_id": "$rating",
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$rating_score"},
                "avg_okr": {"$avg": "$okr_score"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        results = await mongodb.performance_records.aggregate(pipeline).to_list(10)
        
        total = sum(r["count"] for r in results)
        distribution = {}
        
        for r in results:
            rating = r["_id"]
            distribution[rating] = {
                "count": r["count"],
                "percentage": round(r["count"] / total * 100, 2) if total > 0 else 0,
                "avg_score": round(r["avg_score"] or 0, 2),
                "avg_okr": round(r["avg_okr"] or 0, 2),
                "vs_standard": round(r["count"] / total - self.forced_distribution.get(rating, 0), 4) if total > 0 else 0
            }
        
        # 按部门分析
        dept_pipeline = [
            {"$match": match_stage} if match_stage else {"$match": {}},
            {"$lookup": {
                "from": "employees",
                "localField": "employee_id",
                "foreignField": "employee_id",
                "as": "employee"
            }},
            {"$unwind": "$employee"},
            {"$group": {
                "_id": {
                    "department": "$employee.department_id",
                    "rating": "$rating"
                },
                "count": {"$sum": 1}
            }}
        ]
        
        dept_results = await mongodb.performance_records.aggregate(dept_pipeline).to_list(200)
        
        # 整理部门数据
        by_department = {}
        for r in dept_results:
            dept = r["_id"]["department"]
            rating = r["_id"]["rating"]
            if dept not in by_department:
                by_department[dept] = {}
            by_department[dept][rating] = r["count"]
        
        return {
            "period": period or "all",
            "total_records": total,
            "distribution": distribution,
            "by_department": by_department,
            "health_assessment": self._assess_distribution_health(distribution)
        }
    
    async def analyze_okr_completion(self, period: Optional[str] = None) -> Dict[str, Any]:
        """分析 OKR 完成度"""
        
        match_stage = {"okr_score": {"$exists": True}}
        if period:
            match_stage["period"] = period
        
        # 整体 OKR 统计
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": None,
                "avg_completion": {"$avg": "$okr_score"},
                "total": {"$sum": 1},
                "high_completion": {"$sum": {"$cond": [{"$gte": ["$okr_score", 0.8]}, 1, 0]}},
                "low_completion": {"$sum": {"$cond": [{"$lt": ["$okr_score", 0.5]}, 1, 0]}}
            }}
        ]
        
        overall = await mongodb.performance_records.aggregate(pipeline).to_list(1)
        overall_stats = overall[0] if overall else {}
        
        # 按部门
        dept_pipeline = [
            {"$match": match_stage},
            {"$lookup": {
                "from": "employees",
                "localField": "employee_id",
                "foreignField": "employee_id",
                "as": "employee"
            }},
            {"$unwind": "$employee"},
            {"$group": {
                "_id": "$employee.department_id",
                "avg_completion": {"$avg": "$okr_score"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"avg_completion": -1}}
        ]
        
        by_dept = await mongodb.performance_records.aggregate(dept_pipeline).to_list(50)
        
        return {
            "period": period or "all",
            "overall": {
                "avg_completion": round(overall_stats.get("avg_completion", 0) * 100, 2),
                "total_assessed": overall_stats.get("total", 0),
                "high_achievers": overall_stats.get("high_completion", 0),
                "low_achievers": overall_stats.get("low_completion", 0)
            },
            "by_department": [
                {
                    "department_id": d["_id"],
                    "avg_completion": round(d["avg_completion"] * 100, 2),
                    "count": d["count"]
                }
                for d in by_dept
            ],
            "top_departments": [d["_id"] for d in by_dept[:3]],
            "bottom_departments": [d["_id"] for d in by_dept[-3:]] if len(by_dept) > 3 else []
        }
    
    async def analyze_manager_style(self) -> Dict[str, Any]:
        """分析管理者评分风格"""
        
        # 按评审人统计
        pipeline = [
            {"$group": {
                "_id": "$reviewer_id",
                "total_reviews": {"$sum": 1},
                "avg_score": {"$avg": "$rating_score"},
                "ratings": {"$push": "$rating"}
            }},
            {"$match": {"total_reviews": {"$gte": 5}}},
            {"$sort": {"avg_score": -1}}
        ]
        
        results = await mongodb.performance_records.aggregate(pipeline).to_list(100)
        
        # 计算全公司平均
        overall_avg = sum(r["avg_score"] for r in results) / len(results) if results else 70
        
        managers = []
        lenient_managers = []
        strict_managers = []
        
        for r in results:
            avg = r["avg_score"]
            deviation = avg - overall_avg
            
            # 计算评分集中度
            ratings = r["ratings"]
            rating_counts = {rating: ratings.count(rating) for rating in set(ratings)}
            max_concentration = max(rating_counts.values()) / len(ratings) if ratings else 0
            
            # 判断风格
            if deviation > 10:
                style = "lenient"
                lenient_managers.append(r["_id"])
            elif deviation < -10:
                style = "strict"
                strict_managers.append(r["_id"])
            elif max_concentration > 0.7:
                style = "concentrated"
            else:
                style = "balanced"
            
            managers.append({
                "manager_id": r["_id"],
                "total_reviews": r["total_reviews"],
                "avg_score": round(avg, 2),
                "deviation": round(deviation, 2),
                "style": style,
                "concentration": round(max_concentration * 100, 2)
            })
        
        return {
            "overall_avg_score": round(overall_avg, 2),
            "total_managers": len(managers),
            "managers": managers[:20],
            "style_summary": {
                "lenient": len(lenient_managers),
                "strict": len(strict_managers),
                "balanced": len(managers) - len(lenient_managers) - len(strict_managers)
            },
            "attention_needed": lenient_managers[:5] + strict_managers[:5],
            "recommendation": "对评分偏差较大的管理者进行绩效评定培训"
        }
    
    async def check_forced_distribution(self, period: Optional[str] = None) -> Dict[str, Any]:
        """检查强制分布合规性"""
        
        distribution = await self.analyze_performance_distribution(period=period)
        dist = distribution["distribution"]
        
        compliance_issues = []
        
        for rating, standard in self.forced_distribution.items():
            actual = dist.get(rating, {}).get("percentage", 0) / 100
            deviation = actual - standard
            
            if abs(deviation) > 0.05:  # 超过 5% 偏差
                compliance_issues.append({
                    "rating": rating,
                    "standard": f"{standard * 100}%",
                    "actual": f"{actual * 100:.1f}%",
                    "deviation": f"{deviation * 100:+.1f}%",
                    "severity": "high" if abs(deviation) > 0.1 else "medium"
                })
        
        # 按部门检查
        dept_issues = []
        for dept, ratings in distribution.get("by_department", {}).items():
            dept_total = sum(ratings.values())
            for rating, standard in self.forced_distribution.items():
                actual = ratings.get(rating, 0) / dept_total if dept_total > 0 else 0
                if abs(actual - standard) > 0.15:  # 部门允许更大偏差
                    dept_issues.append({
                        "department": dept,
                        "rating": rating,
                        "deviation": f"{(actual - standard) * 100:+.1f}%"
                    })
        
        return {
            "period": period or "all",
            "is_compliant": len(compliance_issues) == 0,
            "overall_issues": compliance_issues,
            "department_issues": dept_issues[:10],
            "recommendations": [
                "召开绩效校准会议" if compliance_issues else "分布符合要求",
                "关注偏差较大的部门" if dept_issues else ""
            ]
        }
    
    async def detect_performance_inflation(self) -> Dict[str, Any]:
        """检测绩效通胀"""
        
        # 按周期统计平均分
        pipeline = [
            {"$group": {
                "_id": "$period",
                "avg_score": {"$avg": "$rating_score"},
                "high_rating_rate": {
                    "$avg": {"$cond": [{"$in": ["$rating", ["S", "A"]]}, 1, 0]}
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        results = await mongodb.performance_records.aggregate(pipeline).to_list(20)
        
        if len(results) < 2:
            return {"message": "历史数据不足，无法检测通胀", "inflation_detected": False}
        
        trends = []
        inflation_detected = False
        
        for i, r in enumerate(results):
            trends.append({
                "period": r["_id"],
                "avg_score": round(r["avg_score"], 2),
                "high_rating_rate": round(r["high_rating_rate"] * 100, 2),
                "count": r["count"]
            })
            
            if i > 0:
                prev = results[i-1]
                if r["avg_score"] > prev["avg_score"] + 2:
                    inflation_detected = True
        
        # 计算整体趋势
        if len(trends) >= 2:
            first_avg = trends[0]["avg_score"]
            last_avg = trends[-1]["avg_score"]
            trend_direction = "上升" if last_avg > first_avg + 3 else "稳定" if abs(last_avg - first_avg) <= 3 else "下降"
        else:
            trend_direction = "数据不足"
        
        return {
            "inflation_detected": inflation_detected,
            "trend_direction": trend_direction,
            "historical_trends": trends,
            "analysis": f"平均绩效分数从 {trends[0]['avg_score']} 变化到 {trends[-1]['avg_score']}" if trends else "",
            "recommendation": "建议重新校准绩效评定标准" if inflation_detected else "绩效评定整体稳定"
        }
    
    async def run_full_analysis(self) -> Dict[str, Any]:
        """运行完整绩效分析"""
        return {
            "distribution": await self.analyze_performance_distribution(),
            "okr_completion": await self.analyze_okr_completion(),
            "manager_style": await self.analyze_manager_style(),
            "forced_distribution_check": await self.check_forced_distribution(),
            "inflation_detection": await self.detect_performance_inflation()
        }
    
    def _assess_distribution_health(self, distribution: Dict) -> Dict[str, Any]:
        """评估分布健康度"""
        total_deviation = 0
        issues = []
        
        for rating, data in distribution.items():
            deviation = abs(data.get("vs_standard", 0))
            total_deviation += deviation
            
            if deviation > 0.1:
                issues.append(f"{rating} 级偏差过大 ({data.get('vs_standard', 0)*100:+.1f}%)")
        
        health_score = max(0, 100 - total_deviation * 200)
        
        return {
            "health_score": round(health_score, 2),
            "status": "健康" if health_score > 80 else "需关注" if health_score > 60 else "需改进",
            "issues": issues
        }
