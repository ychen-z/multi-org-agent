"""
组织健康 Agent
负责人效分析、编制分析、人口结构分析、敬业度分析
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date

from Logging import logger

from .base_agent import BaseAgent, AgentMessage, AgentResponse, AgentTool
from src.data.mongodb import mongodb


class OrgHealthAgent(BaseAgent):
    """组织健康 Agent"""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="org_health",
            name="组织健康 Agent",
            description="评估组织人效、编制合理性、人口结构、敬业度，提供组织优化建议",
            **kwargs
        )
        
        # 健康度标准
        self.benchmarks = {
            "optimal_span_of_control": (5, 10),
            "healthy_turnover_rate": 0.15,
            "optimal_tenure_avg": 3.5,
            "management_ratio": 0.12
        }
    
    def _register_tools(self):
        """注册工具"""
        self.register_tool(AgentTool(
            name="analyze_headcount",
            description="分析人效指标",
            parameters={"type": "object", "properties": {}},
            handler=self.analyze_headcount
        ))
        
        self.register_tool(AgentTool(
            name="analyze_headcount_budget",
            description="分析编制使用情况",
            parameters={"type": "object", "properties": {}},
            handler=self.analyze_headcount_budget
        ))
        
        self.register_tool(AgentTool(
            name="analyze_org_structure",
            description="分析组织结构",
            parameters={"type": "object", "properties": {}},
            handler=self.analyze_org_structure
        ))
        
        self.register_tool(AgentTool(
            name="analyze_demographics",
            description="分析人口结构",
            parameters={"type": "object", "properties": {}},
            handler=self.analyze_demographics
        ))
        
        self.register_tool(AgentTool(
            name="calculate_health_score",
            description="计算组织健康度评分",
            parameters={"type": "object", "properties": {}},
            handler=self.calculate_health_score
        ))
    
    async def process(self, message: AgentMessage) -> AgentResponse:
        """处理消息 - 支持按需 LLM 洞察"""
        task = message.payload.get("task", "")
        include_insights = message.payload.get("include_insights")
        
        try:
            if "人效" in task:
                result = await self.analyze_headcount(
                    include_insights=include_insights,
                    task=task
                )
            elif "编制" in task:
                result = await self.analyze_headcount_budget(
                    include_insights=include_insights,
                    task=task
                )
            elif "结构" in task:
                result = await self.analyze_org_structure(
                    include_insights=include_insights,
                    task=task
                )
            elif "人口" in task or "年龄" in task or "司龄" in task:
                result = await self.analyze_demographics(
                    include_insights=include_insights,
                    task=task
                )
            elif "健康" in task or "评分" in task:
                result = await self.calculate_health_score(
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
            logger.error(f"OrgHealthAgent error: {e}")
            return AgentResponse(success=False, error=str(e))
    
    async def _generate_health_insights(
        self,
        data: Dict[str, Any],
        analysis_type: str,
        task: Optional[str] = None
    ) -> str:
        """生成组织健康分析洞察"""
        
        prompts = {
            "headcount": f"""作为组织效能专家，分析以下人效数据：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 人员规模与效能评估
2. 离职率分析及根因
3. 各部门人效差异解读
4. 人力配置优化建议

{f"用户特别关注：{task}" if task else ""}

要求：数据支撑、可量化改进""",

            "budget": f"""作为人力规划专家，分析以下编制数据：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 整体编制利用率评估
2. 超编/空缺部门分析
3. 编制与业务的匹配度
4. 下一年度编制规划建议

{f"用户特别关注：{task}" if task else ""}""",

            "structure": f"""作为组织设计专家，分析以下组织结构数据：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 管理幅度合理性分析
2. 组织层级效率评估
3. 管理者比例是否健康
4. 组织结构优化建议

{f"用户特别关注：{task}" if task else ""}""",

            "demographics": f"""作为人力资源专家，分析以下人口结构数据：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 年龄结构是否合理
2. 司龄分布健康度
3. 多样性与包容性分析
4. 人才梯队建设建议

{f"用户特别关注：{task}" if task else ""}""",

            "health_score": f"""作为组织诊断专家，分析以下组织健康度评分：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 综合健康度解读
2. 各维度强弱项分析
3. 与行业标杆的差距
4. 优先改进领域和路径

{f"用户特别关注：{task}" if task else ""}"""
        }
        
        prompt = prompts.get(analysis_type, prompts["health_score"])
        return await self.generate_insights(prompt, data, analysis_type)
    
    def _get_health_fallback_insight(
        self, 
        data: Dict[str, Any], 
        analysis_type: str
    ) -> str:
        """组织健康分析回退洞察"""
        
        if analysis_type == "headcount":
            summary = data.get("summary", {})
            return (
                f"在职员工 {summary.get('total_active', 0)} 人，"
                f"离职率 {summary.get('turnover_rate', 0)}%，"
                f"{'高于' if summary.get('vs_benchmark', 0) > 0 else '低于'}基准 "
                f"{abs(summary.get('vs_benchmark', 0))}%。"
            )
        
        elif analysis_type == "budget":
            summary = data.get("summary", {})
            return (
                f"编制利用率 {summary.get('overall_utilization', 0)}%，"
                f"超编部门 {summary.get('over_budget_depts', 0)} 个，"
                f"空缺部门 {summary.get('under_budget_depts', 0)} 个。"
            )
        
        elif analysis_type == "structure":
            span = data.get("span_of_control", {})
            return (
                f"平均管理幅度 {span.get('average', 0)}，"
                f"状态：{span.get('assessment', '未知')}。"
            )
        
        elif analysis_type == "demographics":
            insights = data.get("insights", [])
            return insights[0] if insights else "人口结构分析完成，整体分布正常。"
        
        elif analysis_type == "health_score":
            return (
                f"组织健康度评分 {data.get('overall_score', 0)}，"
                f"等级：{data.get('health_level', '未知')}。"
            )
        
        return "组织健康分析完成，建议结合具体场景解读。"
    
    async def analyze_headcount(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析人效"""
        
        # 员工总数
        total_active = await mongodb.employees.count_documents({"status": "active"})
        total_resigned = await mongodb.employees.count_documents({"status": "resigned"})
        
        # 按部门统计
        dept_pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {
                "_id": "$department_id",
                "count": {"$sum": 1},
                "avg_salary": {"$avg": "$salary.total"}
            }},
            {"$sort": {"count": -1}}
        ]
        
        dept_stats = await mongodb.employees.aggregate(dept_pipeline).to_list(50)
        
        # 计算离职率
        turnover_rate = total_resigned / (total_active + total_resigned) if (total_active + total_resigned) > 0 else 0
        
        # 按职级统计
        level_pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {
                "_id": "$level",
                "count": {"$sum": 1},
                "avg_salary": {"$avg": "$salary.total"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        level_stats = await mongodb.employees.aggregate(level_pipeline).to_list(20)
        
        result = {
            "summary": {
                "total_active": total_active,
                "total_resigned": total_resigned,
                "turnover_rate": round(turnover_rate * 100, 2),
                "vs_benchmark": round((turnover_rate - self.benchmarks["healthy_turnover_rate"]) * 100, 2)
            },
            "by_department": [
                {
                    "department_id": d["_id"],
                    "headcount": d["count"],
                    "avg_salary": round(d["avg_salary"] or 0, 2)
                }
                for d in dept_stats
            ],
            "by_level": [
                {
                    "level": l["_id"],
                    "count": l["count"],
                    "avg_salary": round(l["avg_salary"] or 0, 2)
                }
                for l in level_stats
            ],
            "assessment": "健康" if turnover_rate <= self.benchmarks["healthy_turnover_rate"] else "需关注"
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_health_insights(
                    result, "headcount", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate headcount insights: {e}")
                result["ai_insights"] = self._get_health_fallback_insight(
                    result, "headcount"
                )
        
        return result
    
    async def analyze_headcount_budget(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析编制使用情况"""
        
        # 获取部门编制数据
        departments = await mongodb.departments.find({}).to_list(100)
        
        # 统计各部门实际人数
        actual_pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {
                "_id": "$department_id",
                "actual": {"$sum": 1}
            }}
        ]
        
        actual_counts = await mongodb.employees.aggregate(actual_pipeline).to_list(100)
        actual_map = {a["_id"]: a["actual"] for a in actual_counts}
        
        budget_analysis = []
        total_budget = 0
        total_actual = 0
        over_budget = []
        under_budget = []
        
        for dept in departments:
            budget = dept.get("headcount_budget", 0)
            actual = actual_map.get(dept["department_id"], 0)
            utilization = actual / budget if budget > 0 else 0
            
            total_budget += budget
            total_actual += actual
            
            status = "正常"
            if utilization > 1.1:
                status = "超编"
                over_budget.append(dept["name"])
            elif utilization < 0.7:
                status = "空缺"
                under_budget.append(dept["name"])
            
            budget_analysis.append({
                "department_id": dept["department_id"],
                "department_name": dept.get("name", "Unknown"),
                "budget": budget,
                "actual": actual,
                "utilization": round(utilization * 100, 2),
                "variance": actual - budget,
                "status": status
            })
        
        overall_utilization = total_actual / total_budget if total_budget > 0 else 0
        
        result = {
            "summary": {
                "total_budget": total_budget,
                "total_actual": total_actual,
                "overall_utilization": round(overall_utilization * 100, 2),
                "over_budget_depts": len(over_budget),
                "under_budget_depts": len(under_budget)
            },
            "by_department": budget_analysis,
            "alerts": {
                "over_budget": over_budget[:5],
                "under_budget": under_budget[:5]
            },
            "recommendations": [
                f"关注超编部门: {', '.join(over_budget[:3])}" if over_budget else "无超编部门",
                f"评估空缺岗位: {', '.join(under_budget[:3])}" if under_budget else "编制利用充分"
            ]
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_health_insights(
                    result, "budget", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate budget insights: {e}")
                result["ai_insights"] = self._get_health_fallback_insight(
                    result, "budget"
                )
        
        return result
    
    async def analyze_org_structure(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析组织结构"""
        
        # 计算管理幅度
        span_pipeline = [
            {"$match": {"status": "active", "manager_id": {"$ne": None}}},
            {"$group": {
                "_id": "$manager_id",
                "direct_reports": {"$sum": 1}
            }},
            {"$group": {
                "_id": None,
                "avg_span": {"$avg": "$direct_reports"},
                "max_span": {"$max": "$direct_reports"},
                "min_span": {"$min": "$direct_reports"},
                "total_managers": {"$sum": 1}
            }}
        ]
        
        span_result = await mongodb.employees.aggregate(span_pipeline).to_list(1)
        span_stats = span_result[0] if span_result else {}
        
        # 管理者比例
        total_active = await mongodb.employees.count_documents({"status": "active"})
        managers_count = await mongodb.employees.count_documents({
            "status": "active",
            "level": {"$regex": "^M"}
        })
        
        management_ratio = managers_count / total_active if total_active > 0 else 0
        
        # 组织层级深度
        depth_pipeline = [
            {"$graphLookup": {
                "from": "departments",
                "startWith": "$parent_id",
                "connectFromField": "parent_id",
                "connectToField": "department_id",
                "as": "ancestors"
            }},
            {"$project": {
                "depth": {"$add": [{"$size": "$ancestors"}, 1]}
            }},
            {"$group": {
                "_id": None,
                "max_depth": {"$max": "$depth"}
            }}
        ]
        
        depth_result = await mongodb.departments.aggregate(depth_pipeline).to_list(1)
        max_depth = depth_result[0]["max_depth"] if depth_result else 1
        
        avg_span = span_stats.get("avg_span", 0)
        optimal_min, optimal_max = self.benchmarks["optimal_span_of_control"]
        
        result = {
            "span_of_control": {
                "average": round(avg_span, 2),
                "max": span_stats.get("max_span", 0),
                "min": span_stats.get("min_span", 0),
                "optimal_range": f"{optimal_min}-{optimal_max}",
                "assessment": "正常" if optimal_min <= avg_span <= optimal_max else "需优化"
            },
            "management": {
                "total_managers": managers_count,
                "management_ratio": round(management_ratio * 100, 2),
                "benchmark": f"{self.benchmarks['management_ratio'] * 100}%",
                "assessment": "正常" if management_ratio <= self.benchmarks["management_ratio"] * 1.2 else "管理者占比偏高"
            },
            "org_depth": {
                "max_levels": max_depth,
                "assessment": "正常" if max_depth <= 6 else "层级过深"
            },
            "recommendations": self._get_structure_recommendations(avg_span, management_ratio, max_depth)
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_health_insights(
                    result, "structure", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate structure insights: {e}")
                result["ai_insights"] = self._get_health_fallback_insight(
                    result, "structure"
                )
        
        return result
    
    async def analyze_demographics(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析人口结构"""
        
        today = date.today()
        
        # 年龄分布
        age_pipeline = [
            {"$match": {"status": "active", "birth_date": {"$exists": True}}},
            {"$project": {
                "age": {
                    "$subtract": [
                        {"$year": "$$NOW"},
                        {"$year": "$birth_date"}
                    ]
                }
            }},
            {"$bucket": {
                "groupBy": "$age",
                "boundaries": [0, 25, 30, 35, 40, 45, 50, 100],
                "default": "Other",
                "output": {"count": {"$sum": 1}}
            }}
        ]
        
        age_dist = await mongodb.employees.aggregate(age_pipeline).to_list(10)
        
        # 司龄分布
        tenure_pipeline = [
            {"$match": {"status": "active", "hire_date": {"$exists": True}}},
            {"$project": {
                "tenure_years": {
                    "$divide": [
                        {"$subtract": ["$$NOW", "$hire_date"]},
                        31536000000  # 毫秒转年
                    ]
                }
            }},
            {"$bucket": {
                "groupBy": "$tenure_years",
                "boundaries": [0, 1, 3, 5, 10, 100],
                "default": "Other",
                "output": {"count": {"$sum": 1}}
            }}
        ]
        
        tenure_dist = await mongodb.employees.aggregate(tenure_pipeline).to_list(10)
        
        # 性别分布
        gender_pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {
                "_id": "$gender",
                "count": {"$sum": 1}
            }}
        ]
        
        gender_dist = await mongodb.employees.aggregate(gender_pipeline).to_list(5)
        
        # 学历分布
        edu_pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {
                "_id": "$education",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        
        edu_dist = await mongodb.employees.aggregate(edu_pipeline).to_list(10)
        
        result = {
            "age_distribution": [
                {"range": self._get_age_range(a["_id"]), "count": a["count"]}
                for a in age_dist if a["_id"] != "Other"
            ],
            "tenure_distribution": [
                {"range": self._get_tenure_range(t["_id"]), "count": t["count"]}
                for t in tenure_dist if t["_id"] != "Other"
            ],
            "gender_distribution": {
                g["_id"]: g["count"] for g in gender_dist
            },
            "education_distribution": [
                {"level": e["_id"], "count": e["count"]}
                for e in edu_dist
            ],
            "insights": self._get_demographic_insights(age_dist, tenure_dist, gender_dist)
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_health_insights(
                    result, "demographics", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate demographics insights: {e}")
                result["ai_insights"] = self._get_health_fallback_insight(
                    result, "demographics"
                )
        
        return result
    
    async def calculate_health_score(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """计算组织健康度评分"""
        
        headcount = await self.analyze_headcount()
        budget = await self.analyze_headcount_budget()
        structure = await self.analyze_org_structure()
        demographics = await self.analyze_demographics()
        
        scores = {}
        
        # 人员稳定性评分
        turnover_rate = headcount["summary"]["turnover_rate"] / 100
        stability_score = max(0, 100 - (turnover_rate - self.benchmarks["healthy_turnover_rate"]) * 200)
        scores["stability"] = round(min(100, stability_score), 2)
        
        # 编制利用率评分
        utilization = budget["summary"]["overall_utilization"]
        budget_score = 100 - abs(utilization - 90) * 2
        scores["budget_utilization"] = round(max(0, min(100, budget_score)), 2)
        
        # 组织结构评分
        span = structure["span_of_control"]["average"]
        optimal_min, optimal_max = self.benchmarks["optimal_span_of_control"]
        if optimal_min <= span <= optimal_max:
            structure_score = 100
        else:
            deviation = min(abs(span - optimal_min), abs(span - optimal_max))
            structure_score = max(0, 100 - deviation * 10)
        scores["structure"] = round(structure_score, 2)
        
        # 多样性评分
        gender_dist = demographics.get("gender_distribution", {})
        total = sum(gender_dist.values())
        if total > 0:
            male_ratio = gender_dist.get("M", 0) / total
            diversity_score = 100 - abs(male_ratio - 0.5) * 100
        else:
            diversity_score = 50
        scores["diversity"] = round(diversity_score, 2)
        
        # 综合评分
        weights = {"stability": 0.3, "budget_utilization": 0.25, "structure": 0.25, "diversity": 0.2}
        overall = sum(scores[k] * weights[k] for k in weights)
        
        result = {
            "overall_score": round(overall, 2),
            "dimension_scores": scores,
            "health_level": self._get_health_level(overall),
            "summary": {
                "strengths": [k for k, v in scores.items() if v >= 80],
                "areas_to_improve": [k for k, v in scores.items() if v < 70]
            },
            "recommendations": self._get_health_recommendations(scores)
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_health_insights(
                    result, "health_score", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate health score insights: {e}")
                result["ai_insights"] = self._get_health_fallback_insight(
                    result, "health_score"
                )
        
        return result
    
    async def run_full_analysis(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行完整组织健康分析"""
        result = {
            "headcount": await self.analyze_headcount(),
            "budget": await self.analyze_headcount_budget(),
            "structure": await self.analyze_org_structure(),
            "demographics": await self.analyze_demographics(),
            "health_score": await self.calculate_health_score()
        }
        
        # 按需生成综合洞察
        if self._need_insights(task or "", include_insights):
            try:
                summary_data = {
                    "人效概况": result["headcount"]["summary"],
                    "编制利用": result["budget"]["summary"],
                    "组织结构": result["structure"]["span_of_control"],
                    "健康评分": result["health_score"]["overall_score"],
                    "健康等级": result["health_score"]["health_level"]
                }
                result["ai_insights"] = await self._generate_health_insights(
                    summary_data, "health_score", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate full analysis insights: {e}")
                result["ai_insights"] = "完整组织健康分析已完成，请查看各模块详细数据。"
        
        return result
    
    def _get_age_range(self, boundary: int) -> str:
        """获取年龄范围标签"""
        ranges = {0: "<25", 25: "25-29", 30: "30-34", 35: "35-39", 40: "40-44", 45: "45-49", 50: "50+"}
        return ranges.get(boundary, str(boundary))
    
    def _get_tenure_range(self, boundary: float) -> str:
        """获取司龄范围标签"""
        ranges = {0: "<1年", 1: "1-3年", 3: "3-5年", 5: "5-10年", 10: "10年+"}
        return ranges.get(int(boundary), str(boundary))
    
    def _get_structure_recommendations(self, span: float, mgmt_ratio: float, depth: int) -> List[str]:
        """获取组织结构优化建议"""
        recs = []
        optimal_min, optimal_max = self.benchmarks["optimal_span_of_control"]
        
        if span < optimal_min:
            recs.append("管理幅度过小，考虑合并管理层级")
        elif span > optimal_max:
            recs.append("管理幅度过大，考虑增设管理岗位")
        
        if mgmt_ratio > self.benchmarks["management_ratio"] * 1.2:
            recs.append("管理者比例偏高，评估管理效率")
        
        if depth > 6:
            recs.append("组织层级过深，考虑扁平化改造")
        
        return recs if recs else ["组织结构健康，无需调整"]
    
    def _get_demographic_insights(self, age_dist, tenure_dist, gender_dist) -> List[str]:
        """获取人口结构洞察"""
        insights = []
        
        # 检查新员工占比
        new_employees = next((t["count"] for t in tenure_dist if t.get("_id") == 0), 0)
        total = sum(t["count"] for t in tenure_dist if t.get("_id") != "Other")
        if total > 0 and new_employees / total > 0.3:
            insights.append("新员工占比较高，关注培训和融入")
        
        return insights if insights else ["人口结构分布正常"]
    
    def _get_health_level(self, score: float) -> str:
        """获取健康等级"""
        if score >= 85:
            return "优秀"
        elif score >= 70:
            return "良好"
        elif score >= 55:
            return "一般"
        else:
            return "需改进"
    
    def _get_health_recommendations(self, scores: Dict) -> List[str]:
        """获取健康度优化建议"""
        recs = []
        
        if scores.get("stability", 100) < 70:
            recs.append("加强人才保留，降低离职率")
        if scores.get("budget_utilization", 100) < 70:
            recs.append("优化编制配置，提高利用率")
        if scores.get("structure", 100) < 70:
            recs.append("优化组织结构，调整管理幅度")
        if scores.get("diversity", 100) < 70:
            recs.append("关注多样性建设")
        
        return recs if recs else ["组织健康度良好"]