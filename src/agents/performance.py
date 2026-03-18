"""
绩效目标 Agent
负责 OKR 分析、绩效分布、管理者风格识别
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from Logging import logger

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
        """处理消息 - 支持按需 LLM 洞察"""
        task = message.payload.get("task", "")
        include_insights = message.payload.get("include_insights")
        
        try:
            if "分布" in task:
                result = await self.analyze_performance_distribution(
                    include_insights=include_insights,
                    task=task
                )
            elif "OKR" in task.upper() or "完成" in task:
                result = await self.analyze_okr_completion(
                    include_insights=include_insights,
                    task=task
                )
            elif "管理者" in task or "风格" in task:
                result = await self.analyze_manager_style(
                    include_insights=include_insights,
                    task=task
                )
            elif "强制" in task or "合规" in task:
                result = await self.check_forced_distribution(
                    include_insights=include_insights,
                    task=task
                )
            elif "通胀" in task:
                result = await self.detect_performance_inflation(
                    include_insights=include_insights,
                    task=task
                )
            else:
                result = await self.run_full_analysis(
                    include_insights=include_insights,
                    task=task
                )
            
            return AgentResponse(success=True, data=result)
        except Exception as e:
            logger.error(f"PerformanceAgent error: {e}")
            return AgentResponse(success=False, error=str(e))
    
    async def _generate_performance_insights(
        self,
        data: Dict[str, Any],
        analysis_type: str,
        task: Optional[str] = None
    ) -> str:
        """生成绩效分析洞察"""
        
        prompts = {
            "distribution": f"""作为绩效管理专家，分析以下绩效分布数据：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 分布是否符合强制分布要求？偏差原因？
2. 各等级分布的合理性分析
3. 需要关注的部门或团队
4. 优化建议和校准方案

{f"用户特别关注：{task}" if task else ""}

要求：数据支撑、可操作""",

            "okr": f"""作为 OKR 教练，分析以下 OKR 完成度数据：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 整体完成度评价
2. 高绩效部门的成功经验
3. 低绩效部门的问题诊断
4. 下一周期 OKR 设定建议

{f"用户特别关注：{task}" if task else ""}""",

            "manager_style": f"""作为领导力顾问，分析以下管理者评分风格数据：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 评分风格分布解读
2. 宽松/严格管理者的影响
3. 评分一致性问题分析
4. 校准培训建议

{f"用户特别关注：{task}" if task else ""}""",

            "compliance": f"""作为 HR 合规专家，分析以下强制分布合规数据：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 合规性整体评估
2. 主要违规问题分析
3. 部门层面的风险点
4. 合规改进路径

{f"用户特别关注：{task}" if task else ""}""",

            "inflation": f"""作为组织诊断专家，分析以下绩效通胀数据：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 通胀趋势判断
2. 通胀对组织的影响
3. 根本原因分析
4. 纠偏措施建议

{f"用户特别关注：{task}" if task else ""}"""
        }
        
        prompt = prompts.get(analysis_type, prompts["distribution"])
        return await self.generate_insights(prompt, data, analysis_type)
    
    def _get_performance_fallback_insight(
        self, 
        data: Dict[str, Any], 
        analysis_type: str
    ) -> str:
        """绩效分析回退洞察"""
        
        if analysis_type == "distribution":
            health = data.get("health_assessment", {})
            return (
                f"绩效分布健康度 {health.get('health_score', 0)}，"
                f"状态：{health.get('status', '未知')}。"
                f"{'存在问题：' + '、'.join(health.get('issues', [])) if health.get('issues') else '分布整体正常。'}"
            )
        
        elif analysis_type == "okr":
            overall = data.get("overall", {})
            return (
                f"OKR 平均完成度 {overall.get('avg_completion', 0)}%，"
                f"高绩效者 {overall.get('high_achievers', 0)} 人，"
                f"需关注 {overall.get('low_achievers', 0)} 人。"
            )
        
        elif analysis_type == "manager_style":
            summary = data.get("style_summary", {})
            return (
                f"管理者评分风格：宽松型 {summary.get('lenient', 0)} 人，"
                f"严格型 {summary.get('strict', 0)} 人，"
                f"均衡型 {summary.get('balanced', 0)} 人。"
            )
        
        elif analysis_type == "compliance":
            is_compliant = data.get("is_compliant", False)
            return (
                "强制分布合规。" if is_compliant 
                else f"存在 {len(data.get('overall_issues', []))} 项合规问题，建议召开校准会议。"
            )
        
        elif analysis_type == "inflation":
            detected = data.get("inflation_detected", False)
            trend = data.get("trend_direction", "未知")
            return (
                f"绩效趋势{trend}，"
                f"{'检测到通胀风险，建议重新校准评定标准。' if detected else '未检测到明显通胀。'}"
            )
        
        return "绩效分析完成，建议结合具体场景解读。"
    
    async def analyze_performance_distribution(
        self,
        period: Optional[str] = None,
        department_id: Optional[str] = None,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
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
        
        result = {
            "period": period or "all",
            "total_records": total,
            "distribution": distribution,
            "by_department": by_department,
            "health_assessment": self._assess_distribution_health(distribution)
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_performance_insights(
                    result, "distribution", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate distribution insights: {e}")
                result["ai_insights"] = self._get_performance_fallback_insight(
                    result, "distribution"
                )
        
        return result
    
    async def analyze_okr_completion(
        self, 
        period: Optional[str] = None,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
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
        
        result = {
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
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_performance_insights(
                    result, "okr", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate OKR insights: {e}")
                result["ai_insights"] = self._get_performance_fallback_insight(
                    result, "okr"
                )
        
        return result
    
    async def analyze_manager_style(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
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
        
        result = {
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
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_performance_insights(
                    result, "manager_style", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate manager style insights: {e}")
                result["ai_insights"] = self._get_performance_fallback_insight(
                    result, "manager_style"
                )
        
        return result
    
    async def check_forced_distribution(
        self, 
        period: Optional[str] = None,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
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
        
        result = {
            "period": period or "all",
            "is_compliant": len(compliance_issues) == 0,
            "overall_issues": compliance_issues,
            "department_issues": dept_issues[:10],
            "recommendations": [
                "召开绩效校准会议" if compliance_issues else "分布符合要求",
                "关注偏差较大的部门" if dept_issues else ""
            ]
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_performance_insights(
                    result, "compliance", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate compliance insights: {e}")
                result["ai_insights"] = self._get_performance_fallback_insight(
                    result, "compliance"
                )
        
        return result
    
    async def detect_performance_inflation(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
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
        
        result = {
            "inflation_detected": inflation_detected,
            "trend_direction": trend_direction,
            "historical_trends": trends,
            "analysis": f"平均绩效分数从 {trends[0]['avg_score']} 变化到 {trends[-1]['avg_score']}" if trends else "",
            "recommendation": "建议重新校准绩效评定标准" if inflation_detected else "绩效评定整体稳定"
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_performance_insights(
                    result, "inflation", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate inflation insights: {e}")
                result["ai_insights"] = self._get_performance_fallback_insight(
                    result, "inflation"
                )
        
        return result
    
    async def run_full_analysis(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行完整绩效分析"""
        result = {
            "distribution": await self.analyze_performance_distribution(),
            "okr_completion": await self.analyze_okr_completion(),
            "manager_style": await self.analyze_manager_style(),
            "forced_distribution_check": await self.check_forced_distribution(),
            "inflation_detection": await self.detect_performance_inflation()
        }
        
        # 按需生成综合洞察
        if self._need_insights(task or "", include_insights):
            try:
                summary_data = {
                    "分布健康度": result["distribution"]["health_assessment"],
                    "OKR完成度": result["okr_completion"]["overall"],
                    "管理者风格": result["manager_style"]["style_summary"],
                    "合规状态": result["forced_distribution_check"]["is_compliant"],
                    "通胀风险": result["inflation_detection"]["inflation_detected"]
                }
                result["ai_insights"] = await self._generate_performance_insights(
                    summary_data, "distribution", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate full analysis insights: {e}")
                result["ai_insights"] = "完整绩效分析已完成，请查看各模块详细数据。"
        
        return result
    
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