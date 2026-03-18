"""
招聘效能 Agent
负责招聘渠道分析、漏斗分析、人岗匹配
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from Logging import logger

from .base_agent import BaseAgent, AgentMessage, AgentResponse, AgentTool
from src.data.mongodb import mongodb


class RecruitmentAgent(BaseAgent):
    """招聘效能 Agent"""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="recruitment",
            name="招聘效能 Agent",
            description="分析招聘渠道 ROI、漏斗转化、人岗匹配度，提供招聘优化建议",
            **kwargs
        )
        
        # 漏斗阶段定义
        self.funnel_stages = [
            "resume", "screening", "first_interview", 
            "second_interview", "final_interview",
            "offer", "offer_accepted", "hired"
        ]
        
        # 行业基准
        self.benchmarks = {
            "screening_pass_rate": 0.30,
            "interview_pass_rate": 0.40,
            "offer_accept_rate": 0.70,
            "avg_time_to_hire": 45,  # 天
            "cost_per_hire_target": 8000  # 元
        }
    
    def _register_tools(self):
        """注册工具"""
        self.register_tool(AgentTool(
            name="analyze_channel_roi",
            description="分析各招聘渠道的投入产出比",
            parameters={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "开始日期"},
                    "end_date": {"type": "string", "description": "结束日期"}
                }
            },
            handler=self.analyze_channel_roi
        ))
        
        self.register_tool(AgentTool(
            name="analyze_funnel",
            description="分析招聘漏斗转化率",
            parameters={
                "type": "object",
                "properties": {
                    "department_id": {"type": "string"},
                    "position_id": {"type": "string"}
                }
            },
            handler=self.analyze_funnel
        ))
        
        self.register_tool(AgentTool(
            name="calculate_time_to_hire",
            description="计算各维度的招聘周期",
            parameters={
                "type": "object",
                "properties": {
                    "group_by": {"type": "string", "enum": ["channel", "department", "position"]}
                }
            },
            handler=self.calculate_time_to_hire
        ))
        
        self.register_tool(AgentTool(
            name="identify_bottlenecks",
            description="识别招聘漏斗瓶颈",
            parameters={"type": "object", "properties": {}},
            handler=self.identify_bottlenecks
        ))
        
        self.register_tool(AgentTool(
            name="generate_recommendations",
            description="生成招聘优化建议",
            parameters={"type": "object", "properties": {}},
            handler=self.generate_recommendations
        ))
    
    async def process(self, message: AgentMessage) -> AgentResponse:
        """处理消息 - 支持按需 LLM 洞察"""
        task = message.payload.get("task", "")
        include_insights = message.payload.get("include_insights")
        
        try:
            if "ROI" in task.upper() or "渠道" in task:
                result = await self.analyze_channel_roi(
                    include_insights=include_insights,
                    task=task
                )
            elif "漏斗" in task or "转化" in task:
                result = await self.analyze_funnel(
                    include_insights=include_insights,
                    task=task
                )
            elif "建议" in task or "优化" in task:
                result = await self.generate_recommendations(
                    include_insights=include_insights,
                    task=task
                )
            elif "瓶颈" in task:
                result = await self.identify_bottlenecks(
                    include_insights=include_insights,
                    task=task
                )
            else:
                # 运行完整分析
                result = await self.run_full_analysis(
                    include_insights=include_insights,
                    task=task
                )
            
            return AgentResponse(success=True, data=result)
            
        except Exception as e:
            logger.error(f"RecruitmentAgent error: {e}")
            return AgentResponse(success=False, error=str(e))
    
    async def _generate_recruitment_insights(
        self,
        data: Dict[str, Any],
        analysis_type: str,
        task: Optional[str] = None
    ) -> str:
        """生成招聘分析洞察"""
        
        prompts = {
            "channel_roi": f"""作为招聘效能专家，分析以下招聘渠道 ROI 数据：

数据摘要：
{self._summarize_data(data)}

请从以下角度提供深度洞察：
1. 哪些渠道性价比最高？为什么？
2. 低效渠道的问题根因是什么？
3. 渠道组合优化建议
4. 预计优化后的成本节省

{f"用户特别关注：{task}" if task else ""}

要求：简洁、数据支撑、可执行""",

            "funnel": f"""作为招聘流程专家，分析以下招聘漏斗数据：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 瓶颈环节的根本原因分析
2. 与行业基准的对比解读
3. 每个环节的具体优化措施
4. 优化优先级排序

{f"用户特别关注：{task}" if task else ""}

要求：具体、可落地、有预期效果""",

            "bottleneck": f"""作为招聘诊断专家，分析以下招聘瓶颈：

数据摘要：
{self._summarize_data(data)}

请提供：
1. 瓶颈的系统性原因
2. 相互关联的问题
3. 解决优先级和依赖关系
4. 立即可行的改进措施

{f"用户特别关注：{task}" if task else ""}""",

            "recommendations": f"""作为招聘策略专家，基于以下分析结果：

数据摘要：
{self._summarize_data(data)}

请生成：
1. 战略级优化建议（长期）
2. 战术级优化建议（短期）
3. 快速见效的改进（Quick Wins）
4. 每项建议的预期 ROI

{f"用户特别关注：{task}" if task else ""}"""
        }
        
        prompt = prompts.get(analysis_type, prompts["channel_roi"])
        return await self.generate_insights(prompt, data, analysis_type)
    
    def _get_recruitment_fallback_insight(
        self, 
        data: Dict[str, Any], 
        analysis_type: str
    ) -> str:
        """招聘分析回退洞察"""
        
        if analysis_type == "channel_roi":
            metrics = data.get("channel_metrics", [])
            if metrics:
                top = metrics[0] if metrics else {}
                return (
                    f"渠道分析显示：{top.get('channel', '未知')} 渠道 ROI 最高，"
                    f"转化率 {top.get('conversion_rate', 0)}%。"
                    f"建议优化低效渠道以降低招聘成本。"
                )
        
        elif analysis_type == "funnel":
            bottleneck = data.get("bottleneck", {})
            return (
                f"漏斗分析显示：{bottleneck.get('stage_name', '未知')} 环节流失率最高，"
                f"达 {bottleneck.get('drop_rate', 0)}%。建议重点优化该环节。"
            )
        
        elif analysis_type == "bottleneck":
            issues = data.get("bottlenecks", [])
            high_severity = len([b for b in issues if b.get("severity") == "high"])
            return f"发现 {len(issues)} 个瓶颈问题，其中 {high_severity} 个需紧急处理。"
        
        return "数据分析完成，建议结合业务场景深入解读。"
    
    async def analyze_channel_roi(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析各招聘渠道 ROI"""
        
        match_stage = {}
        if start_date:
            match_stage["created_at"] = {"$gte": datetime.fromisoformat(start_date)}
        if end_date:
            if "created_at" in match_stage:
                match_stage["created_at"]["$lte"] = datetime.fromisoformat(end_date)
            else:
                match_stage["created_at"] = {"$lte": datetime.fromisoformat(end_date)}
        
        pipeline = [
            {"$match": match_stage} if match_stage else {"$match": {}},
            {"$group": {
                "_id": "$channel",
                "total_candidates": {"$sum": 1},
                "total_cost": {"$sum": "$channel_cost"},
                "hired_count": {
                    "$sum": {"$cond": [{"$eq": ["$stage", "hired"]}, 1, 0]}
                },
                "offer_count": {
                    "$sum": {"$cond": [{"$in": ["$stage", ["offer", "offer_accepted", "offer_rejected", "hired"]]}, 1, 0]}
                },
                "interview_count": {
                    "$sum": {"$cond": [{"$in": ["$stage", ["first_interview", "second_interview", "final_interview", "offer", "offer_accepted", "offer_rejected", "hired"]]}, 1, 0]}
                }
            }},
            {"$sort": {"hired_count": -1}}
        ]
        
        results = await mongodb.recruitment_records.aggregate(pipeline).to_list(100)
        
        channel_metrics = []
        for r in results:
            hired = r["hired_count"] or 0
            cost = r["total_cost"] or 0
            
            cost_per_hire = cost / hired if hired > 0 else float('inf')
            conversion_rate = hired / r["total_candidates"] if r["total_candidates"] > 0 else 0
            
            # 计算 ROI 分数
            roi_score = 0
            if hired > 0 and cost > 0:
                # 基于成本效益和转化率
                roi_score = (conversion_rate * 100) / (cost_per_hire / 10000 + 1)
            
            channel_metrics.append({
                "channel": r["_id"],
                "total_candidates": r["total_candidates"],
                "interview_count": r["interview_count"],
                "offer_count": r["offer_count"],
                "hired_count": hired,
                "total_cost": round(cost, 2),
                "cost_per_hire": round(cost_per_hire, 2) if cost_per_hire != float('inf') else None,
                "conversion_rate": round(conversion_rate * 100, 2),
                "roi_score": round(roi_score, 2),
                "is_efficient": cost_per_hire < self.benchmarks["cost_per_hire_target"]
            })
        
        # 排序：按 ROI 分数
        channel_metrics.sort(key=lambda x: x["roi_score"], reverse=True)
        
        # 分类渠道
        efficient_channels = [c for c in channel_metrics if c["is_efficient"]]
        inefficient_channels = [c for c in channel_metrics if not c["is_efficient"]]
        
        result = {
            "analysis_period": {
                "start": start_date,
                "end": end_date
            },
            "channel_metrics": channel_metrics,
            "summary": {
                "total_channels": len(channel_metrics),
                "total_candidates": sum(c["total_candidates"] for c in channel_metrics),
                "total_hired": sum(c["hired_count"] for c in channel_metrics),
                "total_cost": sum(c["total_cost"] for c in channel_metrics),
                "efficient_channels": len(efficient_channels),
                "inefficient_channels": len(inefficient_channels)
            },
            "recommendations": {
                "top_channels": [c["channel"] for c in channel_metrics[:3]],
                "channels_to_review": [c["channel"] for c in inefficient_channels]
            }
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_recruitment_insights(
                    result, "channel_roi", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate channel ROI insights: {e}")
                result["ai_insights"] = self._get_recruitment_fallback_insight(
                    result, "channel_roi"
                )
        
        return result
    
    async def analyze_funnel(
        self,
        department_id: Optional[str] = None,
        position_id: Optional[str] = None,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析招聘漏斗"""
        
        match_stage = {}
        if department_id:
            match_stage["department_id"] = department_id
        if position_id:
            match_stage["position_id"] = position_id
        
        pipeline = [
            {"$match": match_stage} if match_stage else {"$match": {}},
            {"$group": {
                "_id": "$stage",
                "count": {"$sum": 1}
            }}
        ]
        
        results = await mongodb.recruitment_records.aggregate(pipeline).to_list(20)
        stage_counts = {r["_id"]: r["count"] for r in results}
        
        # 构建漏斗
        funnel = []
        previous_count = None
        
        for stage in self.funnel_stages:
            count = stage_counts.get(stage, 0)
            
            # 累计计算：当前阶段 = 当前阶段 + 后续所有阶段
            cumulative = sum(
                stage_counts.get(s, 0) 
                for s in self.funnel_stages[self.funnel_stages.index(stage):]
            )
            
            conversion_rate = cumulative / previous_count if previous_count else 1.0
            
            funnel.append({
                "stage": stage,
                "stage_name": self._get_stage_name(stage),
                "count": count,
                "cumulative": cumulative,
                "conversion_rate": round(conversion_rate * 100, 2),
                "drop_rate": round((1 - conversion_rate) * 100, 2) if previous_count else 0
            })
            
            previous_count = cumulative if cumulative > 0 else previous_count
        
        # 识别最大流失环节
        max_drop = max(funnel, key=lambda x: x["drop_rate"])
        
        result = {
            "filters": {
                "department_id": department_id,
                "position_id": position_id
            },
            "funnel": funnel,
            "summary": {
                "total_candidates": funnel[0]["cumulative"] if funnel else 0,
                "total_hired": stage_counts.get("hired", 0),
                "overall_conversion": round(
                    stage_counts.get("hired", 0) / funnel[0]["cumulative"] * 100, 2
                ) if funnel and funnel[0]["cumulative"] > 0 else 0
            },
            "bottleneck": {
                "stage": max_drop["stage"],
                "stage_name": max_drop["stage_name"],
                "drop_rate": max_drop["drop_rate"]
            }
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_recruitment_insights(
                    result, "funnel", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate funnel insights: {e}")
                result["ai_insights"] = self._get_recruitment_fallback_insight(
                    result, "funnel"
                )
        
        return result
    
    async def calculate_time_to_hire(
        self,
        group_by: str = "channel"
    ) -> Dict[str, Any]:
        """计算招聘周期"""
        
        group_field = f"${group_by}" if group_by != "channel" else "$channel"
        
        pipeline = [
            {"$match": {"stage": "hired"}},
            {"$addFields": {
                "days_to_hire": {
                    "$divide": [
                        {"$subtract": ["$updated_at", "$created_at"]},
                        86400000  # 毫秒转天
                    ]
                }
            }},
            {"$group": {
                "_id": group_field,
                "avg_days": {"$avg": "$days_to_hire"},
                "min_days": {"$min": "$days_to_hire"},
                "max_days": {"$max": "$days_to_hire"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"avg_days": 1}}
        ]
        
        results = await mongodb.recruitment_records.aggregate(pipeline).to_list(100)
        
        metrics = []
        for r in results:
            avg_days = r["avg_days"] or 0
            metrics.append({
                group_by: r["_id"],
                "avg_days": round(avg_days, 1),
                "min_days": round(r["min_days"] or 0, 1),
                "max_days": round(r["max_days"] or 0, 1),
                "hired_count": r["count"],
                "vs_benchmark": round(avg_days - self.benchmarks["avg_time_to_hire"], 1)
            })
        
        overall_avg = sum(m["avg_days"] * m["hired_count"] for m in metrics) / sum(m["hired_count"] for m in metrics) if metrics else 0
        
        return {
            "group_by": group_by,
            "metrics": metrics,
            "summary": {
                "overall_avg_days": round(overall_avg, 1),
                "benchmark": self.benchmarks["avg_time_to_hire"],
                "vs_benchmark": round(overall_avg - self.benchmarks["avg_time_to_hire"], 1)
            },
            "slowest": metrics[-1] if metrics else None,
            "fastest": metrics[0] if metrics else None
        }
    
    async def identify_bottlenecks(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """识别招聘瓶颈"""
        
        funnel = await self.analyze_funnel()
        time_metrics = await self.calculate_time_to_hire()
        channel_analysis = await self.analyze_channel_roi()
        
        bottlenecks = []
        
        # 漏斗瓶颈
        if funnel["bottleneck"]["drop_rate"] > 50:
            bottlenecks.append({
                "type": "funnel",
                "location": funnel["bottleneck"]["stage_name"],
                "severity": "high" if funnel["bottleneck"]["drop_rate"] > 70 else "medium",
                "metric": f"{funnel['bottleneck']['drop_rate']}% 流失率",
                "suggestion": self._get_stage_suggestion(funnel["bottleneck"]["stage"])
            })
        
        # 时间瓶颈
        if time_metrics["summary"]["vs_benchmark"] > 15:
            bottlenecks.append({
                "type": "time",
                "location": "整体招聘周期",
                "severity": "high" if time_metrics["summary"]["vs_benchmark"] > 30 else "medium",
                "metric": f"平均 {time_metrics['summary']['overall_avg_days']} 天，超出基准 {time_metrics['summary']['vs_benchmark']} 天",
                "suggestion": "优化面试安排流程，减少等待时间"
            })
        
        # 渠道瓶颈
        inefficient = channel_analysis["recommendations"]["channels_to_review"]
        if len(inefficient) > len(channel_analysis["channel_metrics"]) / 2:
            bottlenecks.append({
                "type": "channel",
                "location": "招聘渠道",
                "severity": "medium",
                "metric": f"{len(inefficient)} 个渠道效率低下",
                "suggestion": f"考虑关闭或优化: {', '.join(inefficient[:3])}"
            })
        
        result = {
            "bottlenecks": bottlenecks,
            "total_issues": len(bottlenecks),
            "high_severity_count": len([b for b in bottlenecks if b["severity"] == "high"]),
            "details": {
                "funnel_summary": funnel["summary"],
                "time_summary": time_metrics["summary"],
                "channel_summary": channel_analysis["summary"]
            }
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_recruitment_insights(
                    result, "bottleneck", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate bottleneck insights: {e}")
                result["ai_insights"] = self._get_recruitment_fallback_insight(
                    result, "bottleneck"
                )
        
        return result
    
    async def generate_recommendations(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成招聘优化建议"""
        
        channel_analysis = await self.analyze_channel_roi()
        funnel = await self.analyze_funnel()
        bottlenecks = await self.identify_bottlenecks()
        
        recommendations = []
        
        # 渠道优化建议
        top_channels = channel_analysis["recommendations"]["top_channels"]
        low_channels = channel_analysis["recommendations"]["channels_to_review"]
        
        if low_channels:
            recommendations.append({
                "category": "渠道优化",
                "priority": "high",
                "action": f"关闭或减少以下渠道投入: {', '.join(low_channels[:2])}",
                "expected_impact": "预计节省招聘成本 20-30%",
                "effort": "low"
            })
        
        if top_channels:
            recommendations.append({
                "category": "渠道优化",
                "priority": "medium",
                "action": f"增加优质渠道投入: {', '.join(top_channels[:2])}",
                "expected_impact": "提高招聘效率 15-25%",
                "effort": "medium"
            })
        
        # 漏斗优化建议
        if funnel["bottleneck"]["drop_rate"] > 40:
            recommendations.append({
                "category": "流程优化",
                "priority": "high",
                "action": f"优化 {funnel['bottleneck']['stage_name']} 环节",
                "expected_impact": "提高整体转化率",
                "effort": "medium",
                "details": self._get_stage_suggestion(funnel["bottleneck"]["stage"])
            })
        
        # 基于瓶颈的建议
        for bottleneck in bottlenecks["bottlenecks"]:
            if bottleneck["severity"] == "high":
                recommendations.append({
                    "category": "紧急改进",
                    "priority": "high",
                    "action": bottleneck["suggestion"],
                    "expected_impact": "解决关键瓶颈",
                    "effort": "medium"
                })
        
        result = {
            "recommendations": recommendations,
            "summary": {
                "total_recommendations": len(recommendations),
                "high_priority": len([r for r in recommendations if r["priority"] == "high"]),
                "quick_wins": len([r for r in recommendations if r.get("effort") == "low"])
            }
        }
        
        # 按需生成 AI 洞察
        if self._need_insights(task or "", include_insights):
            try:
                result["ai_insights"] = await self._generate_recruitment_insights(
                    result, "recommendations", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate recommendation insights: {e}")
                result["ai_insights"] = "建议基于数据分析生成，请结合业务实际情况执行。"
        
        return result
    
    async def run_full_analysis(
        self,
        include_insights: Optional[bool] = None,
        task: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行完整招聘分析"""
        result = {
            "channel_roi": await self.analyze_channel_roi(),
            "funnel": await self.analyze_funnel(),
            "time_to_hire": await self.calculate_time_to_hire(),
            "bottlenecks": await self.identify_bottlenecks(),
            "recommendations": await self.generate_recommendations()
        }
        
        # 按需生成综合洞察
        if self._need_insights(task or "", include_insights):
            try:
                summary_data = {
                    "渠道效率": result["channel_roi"]["summary"],
                    "漏斗瓶颈": result["funnel"]["bottleneck"],
                    "招聘周期": result["time_to_hire"]["summary"],
                    "问题数量": result["bottlenecks"]["total_issues"]
                }
                result["ai_insights"] = await self._generate_recruitment_insights(
                    summary_data, "recommendations", task
                )
            except Exception as e:
                logger.warning(f"Failed to generate full analysis insights: {e}")
                result["ai_insights"] = "完整分析已完成，请查看各模块详细数据。"
        
        return result
    
    def _get_stage_name(self, stage: str) -> str:
        """获取阶段中文名"""
        names = {
            "resume": "简历投递",
            "screening": "简历筛选",
            "first_interview": "初面",
            "second_interview": "复面",
            "final_interview": "终面",
            "offer": "发放 Offer",
            "offer_accepted": "接受 Offer",
            "offer_rejected": "拒绝 Offer",
            "hired": "入职"
        }
        return names.get(stage, stage)
    
    def _get_stage_suggestion(self, stage: str) -> str:
        """获取阶段优化建议"""
        suggestions = {
            "screening": "优化 JD 描述，提高简历匹配度；调整筛选标准",
            "first_interview": "提升面试官培训；优化面试流程",
            "second_interview": "确保候选人体验；及时反馈",
            "final_interview": "加快决策流程；高层参与",
            "offer": "确保薪酬竞争力；快速响应",
            "offer_accepted": "分析拒绝原因；改善 EVP"
        }
        return suggestions.get(stage, "分析具体原因，针对性优化")