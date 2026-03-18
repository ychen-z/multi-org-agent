"""
人才风险 Agent
负责离职预测、高潜人才识别、团队稳定性评估
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from Logging import logger

from .base_agent import BaseAgent, AgentMessage, AgentResponse, AgentTool, INSIGHT_TRIGGER_KEYWORDS
from src.data.mongodb import mongodb


class TalentRiskAgent(BaseAgent):
    """人才风险 Agent"""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="talent_risk",
            name="人才风险 Agent",
            description="预测离职风险、识别高潜人才、评估团队稳定性，提供人才保留建议",
            **kwargs
        )
        
        # 风险阈值
        self.risk_thresholds = {
            "critical": 0.85,
            "high": 0.70,
            "medium": 0.40,
            "low": 0.0
        }
        
        # 风险因素权重
        self.risk_factor_weights = {
            "salary_below_market": 0.20,
            "no_promotion_2_years": 0.18,
            "manager_change": 0.12,
            "low_engagement": 0.15,
            "high_workload": 0.10,
            "limited_growth": 0.10,
            "peer_departures": 0.08,
            "performance_decline": 0.07
        }
    
    def _register_tools(self):
        """注册工具"""
        self.register_tool(AgentTool(
            name="get_risk_summary",
            description="获取整体风险摘要",
            parameters={"type": "object", "properties": {}},
            handler=self.get_risk_summary
        ))
        
        self.register_tool(AgentTool(
            name="get_high_risk_employees",
            description="获取高风险员工列表",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 20},
                    "department_id": {"type": "string"}
                }
            },
            handler=self.get_high_risk_employees
        ))
        
        self.register_tool(AgentTool(
            name="identify_high_potentials",
            description="识别高潜人才",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 50}
                }
            },
            handler=self.identify_high_potentials
        ))
        
        self.register_tool(AgentTool(
            name="analyze_team_stability",
            description="分析团队稳定性",
            parameters={
                "type": "object",
                "properties": {
                    "department_id": {"type": "string"}
                }
            },
            handler=self.analyze_team_stability
        ))
        
        self.register_tool(AgentTool(
            name="analyze_risk_factors",
            description="分析风险因素分布",
            parameters={"type": "object", "properties": {}},
            handler=self.analyze_risk_factors
        ))
        
        self.register_tool(AgentTool(
            name="generate_retention_actions",
            description="生成人才保留建议",
            parameters={
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"}
                }
            },
            handler=self.generate_retention_actions
        ))
    
    async def process(self, message: AgentMessage) -> AgentResponse:
        """
        处理消息 - 支持按需 LLM 洞察
        """
        task = message.payload.get("task", "")
        include_insights = message.payload.get("include_insights")
        department_id = message.payload.get("department_id")
        
        try:
            # 1. 根据任务类型查询数据
            if "高风险" in task or "离职" in task:
                result = await self.get_high_risk_employees(department_id=department_id)
            elif "高潜" in task or "潜力" in task:
                result = await self.identify_high_potentials()
            elif "团队" in task or "稳定" in task:
                result = await self.analyze_team_stability(department_id=department_id)
            elif "保留" in task or "挽留" in task or "建议" in task:
                result = await self.generate_retention_actions()
            elif "因素" in task:
                result = await self.analyze_risk_factors()
            else:
                result = await self.run_full_analysis()
            
            # 2. 判断是否需要 AI 洞察
            if self._need_insights(task, include_insights):
                # 生成 AI 洞察
                ai_insights = await self._generate_risk_insights(result, task)
                result["ai_insights"] = ai_insights or self._get_fallback_insight(result)
                result["ai_generated"] = ai_insights is not None
            
            return AgentResponse(success=True, data=result)
            
        except Exception as e:
            logger.error(f"TalentRiskAgent error: {e}")
            return AgentResponse(success=False, error=str(e))
    
    async def _generate_risk_insights(
        self, 
        data: Dict[str, Any], 
        task: str
    ) -> Optional[str]:
        """
        生成风险分析洞察
        """
        # 使用专业的风险分析 prompt
        prompt_template = """你是一位资深的人才风险管理专家。

## 风险数据
{data_summary}

## 用户问题
{user_query}

## 要求
请基于数据提供专业的风险分析洞察：
1. **风险评估**：整体风险水平和主要风险点
2. **原因分析**：风险背后的关键驱动因素
3. **建议措施**：具体可执行的干预建议

每条建议要具体、可操作。保持简洁专业。
"""
        return await self.generate_insights(data, task, prompt_template)
    
    def _get_fallback_insight(self, data: Dict[str, Any]) -> str:
        """风险分析的回退洞察"""
        risk_summary = data.get("risk_summary", {})
        high_risk = risk_summary.get("risk_distribution", {}).get("high", 0)
        critical = risk_summary.get("risk_distribution", {}).get("critical", 0)
        total_high_risk = high_risk + critical
        
        if total_high_risk > 0:
            return f"发现 {total_high_risk} 名高风险员工，建议优先约谈了解情况。主要关注薪资竞争力和职业发展两个维度。"
        else:
            return "整体人才风险可控，建议持续关注绩效波动和市场薪资变化。"
    
    async def get_risk_summary(self) -> Dict[str, Any]:
        """获取整体风险摘要"""
        
        # 按风险等级统计
        pipeline = [
            {"$group": {
                "_id": "$risk_level",
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$turnover_risk_score"}
            }}
        ]
        
        results = await mongodb.risk_assessments.aggregate(pipeline).to_list(10)
        
        level_stats = {r["_id"]: {"count": r["count"], "avg_score": r["avg_score"]} for r in results}
        
        total = sum(r["count"] for r in results)
        critical_count = level_stats.get("critical", {}).get("count", 0)
        high_count = level_stats.get("high", {}).get("count", 0)
        
        # 计算整体风险分数
        overall_avg_score = await mongodb.risk_assessments.aggregate([
            {"$group": {"_id": None, "avg": {"$avg": "$turnover_risk_score"}}}
        ]).to_list(1)
        
        avg_score = overall_avg_score[0]["avg"] if overall_avg_score else 0
        
        return {
            "total_assessed": total,
            "risk_distribution": {
                "critical": critical_count,
                "high": high_count,
                "medium": level_stats.get("medium", {}).get("count", 0),
                "low": level_stats.get("low", {}).get("count", 0)
            },
            "high_risk_rate": round((critical_count + high_count) / total * 100, 2) if total > 0 else 0,
            "avg_risk_score": round(avg_score, 3),
            "risk_level": self._get_overall_risk_level(avg_score),
            "immediate_attention_needed": critical_count
        }
    
    async def get_high_risk_employees(
        self,
        limit: int = 20,
        department_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取高风险员工列表"""
        
        match_stage = {"risk_level": {"$in": ["high", "critical"]}}
        
        pipeline = [
            {"$match": match_stage},
            {"$sort": {"turnover_risk_score": -1}},
            {"$limit": limit},
            {"$lookup": {
                "from": "employees",
                "localField": "employee_id",
                "foreignField": "employee_id",
                "as": "employee"
            }},
            {"$unwind": {"path": "$employee", "preserveNullAndEmptyArrays": True}}
        ]
        
        results = await mongodb.risk_assessments.aggregate(pipeline).to_list(limit)
        
        employees = []
        for r in results:
            emp = r.get("employee", {})
            
            # 过滤部门
            if department_id and emp.get("department_id") != department_id:
                continue
            
            employees.append({
                "employee_id": r["employee_id"],
                "name": emp.get("name", "Unknown"),
                "department_id": emp.get("department_id"),
                "level": emp.get("level"),
                "position_name": emp.get("position_name"),
                "risk_score": round(r["turnover_risk_score"], 3),
                "risk_level": r["risk_level"],
                "risk_factors": r.get("risk_factors", []),
                "recommended_actions": r.get("recommended_actions", []),
                "assessment_date": r.get("assessment_date")
            })
        
        return {
            "high_risk_employees": employees[:limit],
            "total_count": len(employees),
            "filters": {"department_id": department_id}
        }
    
    async def identify_high_potentials(self, limit: int = 50) -> Dict[str, Any]:
        """识别高潜人才"""
        
        pipeline = [
            {"$match": {
                "high_potential_score": {"$exists": True, "$gte": 0.6}
            }},
            {"$sort": {"high_potential_score": -1}},
            {"$limit": limit},
            {"$lookup": {
                "from": "employees",
                "localField": "employee_id",
                "foreignField": "employee_id",
                "as": "employee"
            }},
            {"$unwind": {"path": "$employee", "preserveNullAndEmptyArrays": True}}
        ]
        
        results = await mongodb.risk_assessments.aggregate(pipeline).to_list(limit)
        
        high_potentials = []
        at_risk_high_potentials = []
        
        for r in results:
            emp = r.get("employee", {})
            hp_data = {
                "employee_id": r["employee_id"],
                "name": emp.get("name", "Unknown"),
                "department_id": emp.get("department_id"),
                "level": emp.get("level"),
                "position_name": emp.get("position_name"),
                "high_potential_score": round(r.get("high_potential_score", 0), 3),
                "high_potential_factors": r.get("high_potential_factors", []),
                "turnover_risk_score": round(r.get("turnover_risk_score", 0), 3),
                "risk_level": r.get("risk_level")
            }
            
            high_potentials.append(hp_data)
            
            # 高潜高风险人才
            if r.get("risk_level") in ["high", "critical"]:
                at_risk_high_potentials.append(hp_data)
        
        return {
            "high_potentials": high_potentials,
            "total_count": len(high_potentials),
            "at_risk_high_potentials": at_risk_high_potentials,
            "at_risk_count": len(at_risk_high_potentials),
            "alert": f"警告: {len(at_risk_high_potentials)} 名高潜人才存在离职风险!" if at_risk_high_potentials else None
        }
    
    async def analyze_team_stability(
        self,
        department_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析团队稳定性"""
        
        # 按部门统计风险分布
        pipeline = [
            {"$lookup": {
                "from": "employees",
                "localField": "employee_id",
                "foreignField": "employee_id",
                "as": "employee"
            }},
            {"$unwind": "$employee"},
            {"$group": {
                "_id": "$employee.department_id",
                "total": {"$sum": 1},
                "avg_risk_score": {"$avg": "$turnover_risk_score"},
                "high_risk_count": {
                    "$sum": {"$cond": [{"$in": ["$risk_level", ["high", "critical"]]}, 1, 0]}
                },
                "critical_count": {
                    "$sum": {"$cond": [{"$eq": ["$risk_level", "critical"]}, 1, 0]}
                }
            }},
            {"$lookup": {
                "from": "departments",
                "localField": "_id",
                "foreignField": "department_id",
                "as": "department"
            }},
            {"$unwind": {"path": "$department", "preserveNullAndEmptyArrays": True}},
            {"$sort": {"avg_risk_score": -1}}
        ]
        
        if department_id:
            pipeline.insert(0, {"$match": {"employee.department_id": department_id}})
        
        results = await mongodb.risk_assessments.aggregate(pipeline).to_list(100)
        
        team_stability = []
        for r in results:
            high_risk_rate = r["high_risk_count"] / r["total"] * 100 if r["total"] > 0 else 0
            
            # 计算稳定性分数 (100 - 风险分数 * 100)
            stability_score = max(0, 100 - r["avg_risk_score"] * 100)
            
            team_stability.append({
                "department_id": r["_id"],
                "department_name": r.get("department", {}).get("name", "Unknown"),
                "total_employees": r["total"],
                "high_risk_count": r["high_risk_count"],
                "critical_count": r["critical_count"],
                "high_risk_rate": round(high_risk_rate, 2),
                "avg_risk_score": round(r["avg_risk_score"], 3),
                "stability_score": round(stability_score, 2),
                "stability_level": self._get_stability_level(stability_score)
            })
        
        # 识别最不稳定的团队
        unstable_teams = [t for t in team_stability if t["stability_level"] in ["critical", "unstable"]]
        
        return {
            "team_stability": team_stability,
            "summary": {
                "total_teams": len(team_stability),
                "unstable_teams": len(unstable_teams),
                "most_at_risk": team_stability[0] if team_stability else None
            },
            "alerts": [
                f"团队 {t['department_name']} 不稳定，{t['high_risk_count']} 人高风险"
                for t in unstable_teams[:3]
            ]
        }
    
    async def analyze_risk_factors(self) -> Dict[str, Any]:
        """分析风险因素分布"""
        
        pipeline = [
            {"$unwind": "$risk_factors"},
            {"$group": {
                "_id": "$risk_factors",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        
        results = await mongodb.risk_assessments.aggregate(pipeline).to_list(20)
        
        total = sum(r["count"] for r in results)
        
        factors = []
        for r in results:
            factor = r["_id"]
            factors.append({
                "factor": factor,
                "factor_name": self._get_factor_name(factor),
                "count": r["count"],
                "percentage": round(r["count"] / total * 100, 2) if total > 0 else 0,
                "weight": self.risk_factor_weights.get(factor, 0.05),
                "suggested_action": self._get_factor_action(factor)
            })
        
        return {
            "risk_factors": factors,
            "top_factors": factors[:5],
            "insights": [
                f"最主要的风险因素是 {factors[0]['factor_name']}，影响 {factors[0]['percentage']}% 的高风险员工"
                if factors else "暂无风险因素数据"
            ]
        }
    
    async def generate_retention_actions(
        self,
        employee_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成人才保留建议"""
        
        if employee_id:
            # 针对特定员工
            assessment = await mongodb.risk_assessments.find_one({"employee_id": employee_id})
            
            if not assessment:
                return {"error": f"Employee {employee_id} not found"}
            
            employee = await mongodb.employees.find_one({"employee_id": employee_id})
            
            actions = []
            for factor in assessment.get("risk_factors", []):
                action = self._get_factor_action(factor)
                actions.append({
                    "factor": factor,
                    "factor_name": self._get_factor_name(factor),
                    "action": action,
                    "priority": "high" if self.risk_factor_weights.get(factor, 0) > 0.15 else "medium"
                })
            
            return {
                "employee_id": employee_id,
                "employee_name": employee.get("name") if employee else "Unknown",
                "risk_level": assessment.get("risk_level"),
                "risk_score": assessment.get("turnover_risk_score"),
                "retention_actions": actions,
                "immediate_actions": [a for a in actions if a["priority"] == "high"]
            }
        
        else:
            # 整体保留策略
            risk_summary = await self.get_risk_summary()
            factor_analysis = await self.analyze_risk_factors()
            
            strategic_actions = []
            
            # 基于主要风险因素的策略
            for factor in factor_analysis["top_factors"][:3]:
                strategic_actions.append({
                    "category": self._get_factor_category(factor["factor"]),
                    "action": factor["suggested_action"],
                    "target_impact": f"预计降低 {factor['percentage'] * 0.3:.1f}% 的离职风险",
                    "priority": "high" if factor["percentage"] > 20 else "medium"
                })
            
            # 高风险人群专项行动
            if risk_summary["risk_distribution"]["critical"] > 0:
                strategic_actions.append({
                    "category": "紧急干预",
                    "action": f"立即约谈 {risk_summary['risk_distribution']['critical']} 名极高风险员工",
                    "target_impact": "防止关键人才流失",
                    "priority": "critical"
                })
            
            return {
                "strategic_actions": strategic_actions,
                "summary": {
                    "total_actions": len(strategic_actions),
                    "critical_actions": len([a for a in strategic_actions if a["priority"] == "critical"]),
                    "high_priority_actions": len([a for a in strategic_actions if a["priority"] == "high"])
                }
            }
    
    async def run_full_analysis(self) -> Dict[str, Any]:
        """运行完整风险分析"""
        return {
            "risk_summary": await self.get_risk_summary(),
            "high_risk_employees": await self.get_high_risk_employees(limit=10),
            "high_potentials": await self.identify_high_potentials(limit=10),
            "team_stability": await self.analyze_team_stability(),
            "risk_factors": await self.analyze_risk_factors(),
            "retention_actions": await self.generate_retention_actions()
        }
    
    def _get_overall_risk_level(self, score: float) -> str:
        """获取整体风险等级"""
        if score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _get_stability_level(self, score: float) -> str:
        """获取稳定性等级"""
        if score >= 80:
            return "stable"
        elif score >= 60:
            return "moderate"
        elif score >= 40:
            return "unstable"
        else:
            return "critical"
    
    def _get_factor_name(self, factor: str) -> str:
        """获取风险因素中文名"""
        names = {
            "salary_below_market": "薪资低于市场",
            "no_promotion_2_years": "两年未晋升",
            "manager_change": "直属领导变更",
            "low_engagement": "敬业度低",
            "high_workload": "工作负荷过重",
            "limited_growth": "发展空间受限",
            "peer_departures": "同事离职影响",
            "performance_decline": "绩效下滑",
            "attendance_issues": "考勤异常",
            "training_decrease": "培训参与度下降"
        }
        return names.get(factor, factor)
    
    def _get_factor_action(self, factor: str) -> str:
        """获取因素对应的行动建议"""
        actions = {
            "salary_below_market": "进行薪酬竞争力评估，考虑调薪或发放留任奖金",
            "no_promotion_2_years": "制定职业发展计划，安排晋升评审或横向发展机会",
            "manager_change": "安排与新领导的深度沟通，关注适应期支持",
            "low_engagement": "开展一对一沟通，了解根本原因，提供针对性支持",
            "high_workload": "评估工作量分配，考虑人员补充或项目优先级调整",
            "limited_growth": "提供培训机会、轮岗或挑战性项目",
            "peer_departures": "加强团队建设，提升归属感，关注情绪变化",
            "performance_decline": "分析下降原因，提供绩效辅导和资源支持",
            "attendance_issues": "关怀沟通，了解是否有个人困难",
            "training_decrease": "重新激发学习兴趣，提供感兴趣的培训课程"
        }
        return actions.get(factor, "进一步了解情况，制定针对性方案")
    
    def _get_factor_category(self, factor: str) -> str:
        """获取因素分类"""
        categories = {
            "salary_below_market": "薪酬福利",
            "no_promotion_2_years": "职业发展",
            "manager_change": "管理关系",
            "low_engagement": "员工体验",
            "high_workload": "工作负荷",
            "limited_growth": "职业发展",
            "peer_departures": "团队氛围",
            "performance_decline": "绩效管理",
            "attendance_issues": "员工关怀",
            "training_decrease": "学习发展"
        }
        return categories.get(factor, "其他")
