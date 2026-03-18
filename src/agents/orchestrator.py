"""
主控 Agent (Orchestrator)
负责调度所有 Agent、交叉归因分析、生成战略报告
"""

from typing import Dict, List, Any, Optional, TypedDict, Callable, Awaitable
from datetime import datetime
from enum import Enum

from Logging import logger

from .base_agent import BaseAgent, AgentMessage, AgentResponse, AgentTool
from .data_governance import DataGovernanceAgent
from .recruitment import RecruitmentAgent
from .performance import PerformanceAgent
from .talent_risk import TalentRiskAgent
from .org_health import OrgHealthAgent
from src.data.mongodb import mongodb


class AnalysisType(str, Enum):
    FULL = "full"
    RECRUITMENT = "recruitment"
    PERFORMANCE = "performance"
    TALENT_RISK = "talent_risk"
    ORG_HEALTH = "org_health"


class OrchestratorAgent(BaseAgent):
    """主控 Agent"""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="orchestrator",
            name="主控 Agent",
            description="调度所有专业 Agent，进行交叉归因分析，生成战略报告和可执行 Action List",
            **kwargs
        )
        
        # 初始化子 Agent
        self.agents: Dict[str, BaseAgent] = {}
        self._init_agents()
    
    def _init_agents(self):
        """初始化所有子 Agent"""
        try:
            self.agents["data_governance"] = DataGovernanceAgent()
            self.agents["recruitment"] = RecruitmentAgent()
            self.agents["performance"] = PerformanceAgent()
            self.agents["talent_risk"] = TalentRiskAgent()
            self.agents["org_health"] = OrgHealthAgent()
            logger.info("Sub-agents initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize sub-agents: {e}")
    
    def _register_tools(self):
        """注册工具"""
        self.register_tool(AgentTool(
            name="run_full_analysis",
            description="运行全面组织分析",
            parameters={"type": "object", "properties": {}},
            handler=self.run_full_analysis
        ))
        
        self.register_tool(AgentTool(
            name="cross_analysis",
            description="进行交叉归因分析",
            parameters={"type": "object", "properties": {}},
            handler=self.cross_analysis
        ))
        
        self.register_tool(AgentTool(
            name="generate_strategic_report",
            description="生成 CEO 战略报告",
            parameters={"type": "object", "properties": {}},
            handler=self.generate_strategic_report
        ))
        
        self.register_tool(AgentTool(
            name="generate_action_list",
            description="生成可执行行动清单",
            parameters={"type": "object", "properties": {}},
            handler=self.generate_action_list
        ))
    
    async def process(self, message: AgentMessage) -> AgentResponse:
        """处理消息"""
        task = message.payload.get("task", "")
        
        try:
            if "全面分析" in task or "complete" in task.lower():
                result = await self.run_full_analysis()
            elif "报告" in task or "report" in task.lower():
                result = await self.generate_strategic_report()
            elif "行动" in task or "action" in task.lower():
                result = await self.generate_action_list()
            elif "交叉" in task or "归因" in task:
                result = await self.cross_analysis()
            else:
                # 使用 LLM 理解复杂查询
                result = await self.handle_natural_query(task)
            
            return AgentResponse(success=True, data=result)
            
        except Exception as e:
            logger.error(f"OrchestratorAgent error: {e}")
            return AgentResponse(success=False, error=str(e))
    
    async def run_full_analysis(self) -> Dict[str, Any]:
        """运行全面分析"""
        logger.info("Starting full organization analysis...")
        
        results = {
            "analysis_time": datetime.utcnow().isoformat(),
            "agents_results": {}
        }
        
        # 1. 数据治理分析
        logger.info("Running data governance analysis...")
        dg_agent = self.agents.get("data_governance")
        if dg_agent:
            dg_result = await dg_agent.run("运行数据质量评估")
            results["agents_results"]["data_governance"] = dg_result.data
        
        # 2. 招聘分析
        logger.info("Running recruitment analysis...")
        rec_agent = self.agents.get("recruitment")
        if rec_agent:
            rec_result = await rec_agent.run("运行完整招聘分析")
            results["agents_results"]["recruitment"] = rec_result.data
        
        # 3. 人才风险分析
        logger.info("Running talent risk analysis...")
        risk_agent = self.agents.get("talent_risk")
        if risk_agent:
            risk_result = await risk_agent.run("运行完整风险分析")
            results["agents_results"]["talent_risk"] = risk_result.data
        
        # 4. 交叉归因
        logger.info("Running cross analysis...")
        results["cross_analysis"] = await self.cross_analysis()
        
        # 5. 生成摘要
        results["summary"] = await self._generate_summary(results)
        
        logger.info("Full analysis completed")
        return results
    
    async def cross_analysis(
        self,
        force_refresh: bool = False,
        department_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        交叉归因分析（带缓存）
        
        Args:
            force_refresh: 是否强制刷新缓存
            department_id: 部门 ID（可选筛选）
        
        Returns:
            交叉分析结果
        """
        from src.data.cache import cache_manager, CacheManager
        
        # 生成缓存键
        cache_key = CacheManager.generate_cache_key(
            analysis_type="cross_analysis",
            department_id=department_id,
            granularity="hour"
        )
        
        # 检查缓存（除非强制刷新）
        if not force_refresh:
            cached_data = await cache_manager.get_cache(cache_key)
            if cached_data:
                logger.info(f"Cross analysis cache hit: {cache_key}")
                return cached_data
        
        logger.info(f"Cross analysis cache miss, executing queries: {cache_key}")
        
        # 执行分析
        cross_insights = {
            "recruitment_performance": await self._analyze_recruitment_performance(),
            "performance_turnover": await self._analyze_performance_turnover(),
            "manager_team_impact": await self._analyze_manager_team_impact(),
            "cached_at": datetime.utcnow().isoformat(),
            "cache_key": cache_key
        }
        
        # 存入缓存
        await cache_manager.set_cache(
            cache_key=cache_key,
            data=cross_insights,
            analysis_type="cross_analysis"
        )
        
        return cross_insights
    
    async def _analyze_recruitment_performance(self) -> Dict[str, Any]:
        """招聘-绩效关联分析"""
        
        # 按渠道分析入职员工的绩效
        pipeline = [
            {"$match": {"stage": "hired", "hired_employee_id": {"$exists": True}}},
            {"$lookup": {
                "from": "performance_records",
                "localField": "hired_employee_id",
                "foreignField": "employee_id",
                "as": "performance"
            }},
            {"$unwind": {"path": "$performance", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": "$channel",
                "hired_count": {"$sum": 1},
                "avg_rating_score": {"$avg": "$performance.rating_score"},
                "high_performers": {
                    "$sum": {"$cond": [{"$in": ["$performance.rating", ["S", "A"]]}, 1, 0]}
                }
            }},
            {"$sort": {"avg_rating_score": -1}}
        ]
        
        results = await mongodb.recruitment_records.aggregate(pipeline).to_list(20)
        
        channel_quality = []
        for r in results:
            high_perf_rate = r["high_performers"] / r["hired_count"] * 100 if r["hired_count"] > 0 else 0
            channel_quality.append({
                "channel": r["_id"],
                "hired_count": r["hired_count"],
                "avg_rating_score": round(r["avg_rating_score"] or 0, 2),
                "high_performer_rate": round(high_perf_rate, 2),
                "quality_rank": len(channel_quality) + 1
            })
        
        return {
            "analysis": "招聘渠道与员工绩效关联",
            "channel_quality": channel_quality,
            "insight": f"最优质渠道是 {channel_quality[0]['channel']}，高绩效员工占比 {channel_quality[0]['high_performer_rate']}%" if channel_quality else "暂无数据",
            "recommendation": "增加优质渠道投入，优化低质量渠道筛选标准"
        }
    
    async def _analyze_performance_turnover(self) -> Dict[str, Any]:
        """绩效-离职关联分析"""
        
        # 分析高风险员工的绩效分布
        pipeline = [
            {"$match": {"risk_level": {"$in": ["high", "critical"]}}},
            {"$lookup": {
                "from": "performance_records",
                "localField": "employee_id",
                "foreignField": "employee_id",
                "as": "performance"
            }},
            {"$unwind": {"path": "$performance", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": "$performance.rating",
                "count": {"$sum": 1},
                "avg_risk_score": {"$avg": "$turnover_risk_score"}
            }},
            {"$sort": {"avg_risk_score": -1}}
        ]
        
        results = await mongodb.risk_assessments.aggregate(pipeline).to_list(10)
        
        perf_risk_map = []
        for r in results:
            perf_risk_map.append({
                "rating": r["_id"] or "Unknown",
                "high_risk_count": r["count"],
                "avg_risk_score": round(r["avg_risk_score"], 3)
            })
        
        # 找出高绩效高风险的情况
        high_perf_high_risk = next(
            (p for p in perf_risk_map if p["rating"] in ["S", "A"] and p["avg_risk_score"] > 0.7),
            None
        )
        
        return {
            "analysis": "绩效评级与离职风险关联",
            "performance_risk_map": perf_risk_map,
            "insight": f"警告：存在高绩效高风险员工（{high_perf_high_risk['rating']} 级）" if high_perf_high_risk else "高绩效员工整体稳定",
            "recommendation": "重点关注高绩效员工的满意度和发展需求"
        }
    
    async def _analyze_manager_team_impact(self) -> Dict[str, Any]:
        """管理者-团队影响分析"""
        
        # 按经理分析下属的风险情况
        pipeline = [
            {"$lookup": {
                "from": "employees",
                "localField": "employee_id",
                "foreignField": "employee_id",
                "as": "employee"
            }},
            {"$unwind": "$employee"},
            {"$group": {
                "_id": "$employee.manager_id",
                "team_size": {"$sum": 1},
                "avg_risk_score": {"$avg": "$turnover_risk_score"},
                "high_risk_count": {
                    "$sum": {"$cond": [{"$in": ["$risk_level", ["high", "critical"]]}, 1, 0]}
                }
            }},
            {"$match": {"team_size": {"$gte": 3}}},
            {"$sort": {"avg_risk_score": -1}},
            {"$limit": 10}
        ]
        
        results = await mongodb.risk_assessments.aggregate(pipeline).to_list(10)
        
        problem_managers = []
        for r in results:
            if r["avg_risk_score"] and r["avg_risk_score"] > 0.5:
                high_risk_rate = r["high_risk_count"] / r["team_size"] * 100
                problem_managers.append({
                    "manager_id": r["_id"],
                    "team_size": r["team_size"],
                    "avg_team_risk": round(r["avg_risk_score"], 3),
                    "high_risk_rate": round(high_risk_rate, 2)
                })
        
        return {
            "analysis": "管理者与团队稳定性关联",
            "problem_managers": problem_managers,
            "insight": f"发现 {len(problem_managers)} 位管理者的团队存在异常高的离职风险" if problem_managers else "管理者团队整体稳定",
            "recommendation": "对问题管理者进行一对一沟通，了解团队情况；安排管理培训"
        }
    
    async def generate_strategic_report(
        self,
        progress_callback: Optional[Callable[[str, int], Awaitable[None]]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        生成 CEO 战略报告
        
        Args:
            progress_callback: 进度回调函数 (step_name, progress_percent)
            force_refresh: 是否强制刷新缓存
        
        Returns:
            完整的战略报告
        """
        async def report_progress(step: str, progress: int):
            if progress_callback:
                try:
                    await progress_callback(step, progress)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
        
        await report_progress("初始化分析...", 5)
        
        # 收集关键数据
        employee_count = await mongodb.employees.count_documents({"status": "active"})
        
        await report_progress("数据治理分析中...", 10)
        
        # 数据治理
        dg_agent = self.agents.get("data_governance")
        dg_data = None
        if dg_agent:
            result = await dg_agent.run("运行数据质量评估")
            dg_data = result.data
        
        await report_progress("招聘效能分析中...", 25)
        
        # 招聘数据
        recruitment_agent = self.agents.get("recruitment")
        recruitment_data = None
        if recruitment_agent:
            result = await recruitment_agent.run("分析招聘渠道 ROI")
            recruitment_data = result.data
        
        await report_progress("绩效分析中...", 35)
        
        # 绩效数据
        perf_agent = self.agents.get("performance")
        perf_data = None
        if perf_agent:
            result = await perf_agent.run("分析绩效分布")
            perf_data = result.data
        
        await report_progress("人才风险分析中...", 45)
        
        # 风险数据
        risk_agent = self.agents.get("talent_risk")
        risk_data = None
        if risk_agent:
            result = await risk_agent.run("获取风险摘要")
            risk_data = result.data
        
        await report_progress("组织健康分析中...", 55)
        
        # 组织健康
        org_agent = self.agents.get("org_health")
        org_data = None
        if org_agent:
            result = await org_agent.run("分析组织健康")
            org_data = result.data
        
        await report_progress("交叉归因分析中...", 65)
        
        # 交叉分析（带缓存）
        cross_data = await self.cross_analysis(force_refresh=force_refresh)
        
        await report_progress("AI 生成洞察中...", 75)
        
        # 使用 LLM 生成智能洞察
        ai_insights = await self._generate_ai_insights(
            employee_count=employee_count,
            recruitment_data=recruitment_data,
            risk_data=risk_data,
            cross_data=cross_data
        )
        
        await report_progress("生成报告中...", 85)
        
        # 使用 LLM 生成报告 Markdown（如果可用）
        report_markdown = await self._generate_report_markdown(
            employee_count=employee_count,
            dg_data=dg_data,
            recruitment_data=recruitment_data,
            perf_data=perf_data,
            risk_data=risk_data,
            org_data=org_data,
            cross_data=cross_data,
            ai_insights=ai_insights
        )
        
        await report_progress("完成报告...", 95)
        
        # 构建结构化报告
        report = {
            "title": "组织智能分析战略报告",
            "subtitle": "Multi-Agent 系统自动生成",
            "generated_at": datetime.utcnow().isoformat(),
            "executive_summary": {
                "key_metrics": {
                    "total_employees": employee_count,
                    "high_risk_count": risk_data.get("risk_summary", {}).get("risk_distribution", {}).get("high", 0) if risk_data else 0,
                    "critical_risk_count": risk_data.get("risk_summary", {}).get("risk_distribution", {}).get("critical", 0) if risk_data else 0,
                    "data_quality_score": dg_data.get("quality_score", 0) if dg_data else 0
                },
                "key_findings": ai_insights.get("key_findings", [
                    f"当前在职员工 {employee_count:,} 人",
                ]),
                "ai_summary": ai_insights.get("executive_summary", "")
            },
            "sections": {
                "data_quality": {
                    "title": "数据质量",
                    "summary": dg_data if dg_data else {}
                },
                "recruitment": {
                    "title": "招聘效能",
                    "summary": recruitment_data.get("channel_roi", {}).get("summary") if recruitment_data else {},
                    "top_channels": recruitment_data.get("channel_roi", {}).get("recommendations", {}).get("top_channels", []) if recruitment_data else []
                },
                "performance": {
                    "title": "绩效分析",
                    "summary": perf_data if perf_data else {}
                },
                "talent_risk": {
                    "title": "人才风险",
                    "summary": risk_data.get("risk_summary") if risk_data else {}
                },
                "org_health": {
                    "title": "组织健康",
                    "summary": org_data if org_data else {}
                },
                "cross_insights": {
                    "title": "交叉分析洞察",
                    "insights": ai_insights.get("cross_insights", [
                        cross_data.get("recruitment_performance", {}).get("insight", ""),
                        cross_data.get("performance_turnover", {}).get("insight", ""),
                        cross_data.get("manager_team_impact", {}).get("insight", "")
                    ])
                }
            },
            "recommendations": ai_insights.get("recommendations", {
                "short_term": ["立即约谈极高风险员工（1-2周）"],
                "medium_term": ["优化绩效管理流程"],
                "long_term": ["建立人才梯队"]
            }),
            "action_items": ai_insights.get("action_items", []),
            "report_markdown": report_markdown
        }
        
        await report_progress("完成", 100)
        
        return report
    
    async def _generate_ai_insights(
        self,
        employee_count: int,
        recruitment_data: Optional[Dict],
        risk_data: Optional[Dict],
        cross_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """使用 LLM 生成智能洞察"""
        
        # 构建分析数据摘要
        data_summary = f"""
## 组织数据摘要

### 基础数据
- 在职员工总数: {employee_count}

### 风险分析
- 高风险员工数: {risk_data.get('risk_summary', {}).get('risk_distribution', {}).get('high', 0) if risk_data else 'N/A'}
- 极高风险员工数: {risk_data.get('risk_summary', {}).get('risk_distribution', {}).get('critical', 0) if risk_data else 'N/A'}

### 交叉分析结果
- 招聘-绩效关联: {cross_data.get('recruitment_performance', {}).get('insight', 'N/A') if cross_data else 'N/A'}
- 绩效-离职关联: {cross_data.get('performance_turnover', {}).get('insight', 'N/A') if cross_data else 'N/A'}
- 管理者-团队影响: {cross_data.get('manager_team_impact', {}).get('insight', 'N/A') if cross_data else 'N/A'}
"""
        
        system_prompt = """你是一位资深的 HR 数据分析专家，擅长从组织数据中提取战略洞察。

请基于提供的数据，生成以下内容（JSON 格式）：
1. executive_summary: 一段 2-3 句话的执行摘要
2. key_findings: 3-5 个关键发现（数组）
3. cross_insights: 3 个交叉分析洞察（数组）
4. recommendations: 包含 short_term, medium_term, long_term 三个数组
5. action_items: 3-5 个具体行动项，每个包含 priority, action, owner, deadline

返回纯 JSON，不要包含 markdown 代码块。"""

        try:
            import asyncio
            
            # 设置 30 秒超时
            response = await asyncio.wait_for(
                self.chat(data_summary, system_prompt=system_prompt),
                timeout=30.0
            )
            
            # 解析 JSON 响应
            import json
            # 清理可能的 markdown 代码块
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            response = response.strip()
            
            insights = json.loads(response)
            logger.info("AI insights generated successfully")
            return insights
            
        except asyncio.TimeoutError:
            logger.warning("LLM timeout, using fallback insights")
            return self._get_fallback_insights(employee_count, risk_data, cross_data)
        except Exception as e:
            logger.warning(f"LLM insights failed: {e}, using fallback")
            return self._get_fallback_insights(employee_count, risk_data, cross_data)
    
    def _get_fallback_insights(
        self,
        employee_count: int,
        risk_data: Optional[Dict],
        cross_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """LLM 失败时的回退洞察"""
        high_risk = risk_data.get('risk_summary', {}).get('risk_distribution', {}).get('high', 0) if risk_data else 0
        critical_risk = risk_data.get('risk_summary', {}).get('risk_distribution', {}).get('critical', 0) if risk_data else 0
        
        return {
            "executive_summary": f"组织当前在职员工 {employee_count:,} 人，其中 {high_risk + critical_risk} 人存在较高离职风险需要关注。",
            "key_findings": [
                f"当前在职员工 {employee_count:,} 人",
                f"高风险员工 {high_risk + critical_risk} 人，需重点关注",
                "建议加强对核心人才的保留措施"
            ],
            "cross_insights": [
                cross_data.get("recruitment_performance", {}).get("insight", "") if cross_data else "",
                cross_data.get("performance_turnover", {}).get("insight", "") if cross_data else "",
                cross_data.get("manager_team_impact", {}).get("insight", "") if cross_data else ""
            ],
            "recommendations": {
                "short_term": ["立即约谈极高风险员工（1-2周）", "暂停低效招聘渠道投入"],
                "medium_term": ["优化绩效管理流程", "加强管理者培训"],
                "long_term": ["建立人才梯队", "完善员工体验"]
            },
            "action_items": [
                {"priority": "critical", "action": "约谈高风险核心员工", "owner": "HRBP", "deadline": "2周内"},
                {"priority": "high", "action": "优化招聘渠道预算", "owner": "招聘负责人", "deadline": "1个月内"}
            ],
            "_fallback": True,
            "_fallback_reason": "AI 洞察生成失败，使用规则报告"
        }
    
    async def _generate_report_markdown(
        self,
        employee_count: int,
        dg_data: Optional[Dict],
        recruitment_data: Optional[Dict],
        perf_data: Optional[Dict],
        risk_data: Optional[Dict],
        org_data: Optional[Dict],
        cross_data: Optional[Dict],
        ai_insights: Optional[Dict]
    ) -> str:
        """使用 LLM 生成报告 Markdown"""
        
        # 如果已经是回退模式，直接使用模板
        if ai_insights and ai_insights.get("_fallback"):
            return self._get_fallback_markdown(employee_count, risk_data, ai_insights)
        
        data_context = f"""
# 分析数据上下文

## 基础指标
- 在职员工: {employee_count}
- 数据质量分数: {dg_data.get('quality_score', 'N/A') if dg_data else 'N/A'}

## AI 生成的洞察
{ai_insights if ai_insights else 'N/A'}

## 交叉分析
{cross_data if cross_data else 'N/A'}
"""
        
        system_prompt = """你是一位 CEO 级别的战略报告撰写专家。

请基于提供的数据，生成一份专业的战略报告（Markdown 格式）。

报告结构：
1. # 执行摘要 - 2-3 句话概述
2. ## 关键指标 - 用表格展示核心数据
3. ## 风险与机遇 - 列出主要风险和机遇
4. ## 战略建议 - 分短期/中期/长期
5. ## 行动计划 - 具体可执行的行动项

要求：
- 语言简洁有力，适合高管阅读
- 数据驱动，有具体数字支撑
- 建议要具体可执行
- 控制在 1000 字以内"""

        try:
            import asyncio
            
            response = await asyncio.wait_for(
                self.chat(data_context, system_prompt=system_prompt),
                timeout=30.0
            )
            
            logger.info("Report markdown generated successfully")
            return response
            
        except Exception as e:
            logger.warning(f"Report markdown generation failed: {e}")
            return self._get_fallback_markdown(employee_count, risk_data, ai_insights)
    
    def _get_fallback_markdown(
        self,
        employee_count: int,
        risk_data: Optional[Dict],
        ai_insights: Optional[Dict]
    ) -> str:
        """生成回退 Markdown 报告"""
        high_risk = risk_data.get('risk_summary', {}).get('risk_distribution', {}).get('high', 0) if risk_data else 0
        critical_risk = risk_data.get('risk_summary', {}).get('risk_distribution', {}).get('critical', 0) if risk_data else 0
        
        return f"""# 组织智能分析战略报告

> ⚠️ 注意：AI 洞察生成失败，使用规则模板生成

## 执行摘要

组织当前在职员工 **{employee_count:,}** 人，其中 **{high_risk + critical_risk}** 人存在较高离职风险需要关注。

## 关键指标

| 指标 | 数值 |
|------|------|
| 在职员工 | {employee_count:,} |
| 高风险员工 | {high_risk} |
| 极高风险员工 | {critical_risk} |

## 风险与机遇

### 风险
- 存在 {high_risk + critical_risk} 名高风险员工，需及时干预
- 部分招聘渠道效率偏低

### 机遇
- 通过优化招聘渠道可节省成本
- 针对性的人才保留可降低流失

## 战略建议

### 短期（1-2周）
- 立即约谈极高风险员工
- 暂停低效招聘渠道投入

### 中期（1-3个月）
- 优化绩效管理流程
- 加强管理者培训

### 长期（3-6个月）
- 建立人才梯队
- 完善员工体验

## 行动计划

| 优先级 | 行动 | 责任人 | 截止日期 |
|--------|------|--------|----------|
| 紧急 | 约谈高风险核心员工 | HRBP | 2周内 |
| 高 | 优化招聘渠道预算 | 招聘负责人 | 1个月内 |
| 中 | 启动管理者培训 | HR总监 | 季度末 |

---
*报告生成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*
"""
    
    async def generate_action_list(self) -> Dict[str, Any]:
        """生成可执行行动清单"""
        
        # 获取各维度分析结果
        risk_agent = self.agents.get("talent_risk")
        recruitment_agent = self.agents.get("recruitment")
        
        actions = []
        
        # 人才风险行动
        if risk_agent:
            risk_result = await risk_agent.run("获取高风险员工")
            high_risk_employees = risk_result.data.get("high_risk_employees", [])[:5]
            
            if high_risk_employees:
                actions.append({
                    "id": "ACT001",
                    "priority": "critical",
                    "category": "人才挽留",
                    "action": "约谈高风险核心员工",
                    "target": f"{len(high_risk_employees)} 人",
                    "details": [e.get("name", e.get("employee_id")) for e in high_risk_employees],
                    "owner": "HRBP",
                    "deadline": "2周内",
                    "expected_outcome": "降低核心人才流失风险"
                })
        
        # 招聘优化行动
        if recruitment_agent:
            rec_result = await recruitment_agent.run("分析招聘渠道 ROI")
            low_channels = rec_result.data.get("channel_roi", {}).get("recommendations", {}).get("channels_to_review", [])
            
            if low_channels:
                actions.append({
                    "id": "ACT002",
                    "priority": "high",
                    "category": "招聘优化",
                    "action": "关闭或优化低效招聘渠道",
                    "target": ", ".join(low_channels[:3]),
                    "owner": "招聘负责人",
                    "deadline": "1个月内",
                    "expected_outcome": "预计节省招聘成本 20-30%"
                })
        
        # 管理者辅导行动
        cross_data = await self.cross_analysis()
        problem_managers = cross_data.get("manager_team_impact", {}).get("problem_managers", [])
        
        if problem_managers:
            actions.append({
                "id": "ACT003",
                "priority": "high",
                "category": "管理提升",
                "action": "约谈问题管理者，了解团队情况",
                "target": f"{len(problem_managers)} 位管理者",
                "owner": "HRBP / 上级领导",
                "deadline": "2周内",
                "expected_outcome": "改善团队稳定性"
            })
        
        # 添加常规行动
        actions.extend([
            {
                "id": "ACT004",
                "priority": "medium",
                "category": "绩效管理",
                "action": "启动绩效校准会议",
                "target": "全公司",
                "owner": "HR 负责人",
                "deadline": "季度末",
                "expected_outcome": "确保绩效评定公平性"
            },
            {
                "id": "ACT005",
                "priority": "medium",
                "category": "组织健康",
                "action": "开展员工敬业度调研",
                "target": "全公司",
                "owner": "HR 负责人",
                "deadline": "下季度初",
                "expected_outcome": "了解员工诉求，提前干预"
            }
        ])
        
        # 按优先级排序
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        actions.sort(key=lambda x: priority_order.get(x["priority"], 99))
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "action_list": actions,
            "summary": {
                "total_actions": len(actions),
                "critical": len([a for a in actions if a["priority"] == "critical"]),
                "high": len([a for a in actions if a["priority"] == "high"]),
                "medium": len([a for a in actions if a["priority"] == "medium"])
            }
        }
    
    async def handle_natural_query(self, query: str) -> Dict[str, Any]:
        """处理自然语言查询"""
        
        # 简单的意图识别
        if any(kw in query for kw in ["招聘", "渠道", "候选人"]):
            agent = self.agents.get("recruitment")
            if agent:
                result = await agent.run(query)
                return {"source": "recruitment_agent", "result": result.data}
        
        elif any(kw in query for kw in ["离职", "风险", "高风险", "保留"]):
            agent = self.agents.get("talent_risk")
            if agent:
                result = await agent.run(query)
                return {"source": "talent_risk_agent", "result": result.data}
        
        elif any(kw in query for kw in ["数据", "质量", "清洗"]):
            agent = self.agents.get("data_governance")
            if agent:
                result = await agent.run(query)
                return {"source": "data_governance_agent", "result": result.data}
        
        # 默认运行全面分析
        return await self.run_full_analysis()
    
    async def _generate_summary(self, results: Dict) -> Dict[str, Any]:
        """生成分析摘要"""
        summary = {
            "key_findings": [],
            "alerts": [],
            "recommendations": []
        }
        
        # 从各 Agent 结果提取关键发现
        talent_risk = results.get("agents_results", {}).get("talent_risk", {})
        if talent_risk:
            risk_summary = talent_risk.get("risk_summary", {})
            high_risk = risk_summary.get("risk_distribution", {}).get("high", 0)
            critical = risk_summary.get("risk_distribution", {}).get("critical", 0)
            
            if critical > 0:
                summary["alerts"].append(f"紧急：{critical} 名员工存在极高离职风险")
            if high_risk > 10:
                summary["alerts"].append(f"警告：{high_risk} 名员工存在高离职风险")
        
        recruitment = results.get("agents_results", {}).get("recruitment", {})
        if recruitment:
            channel_roi = recruitment.get("channel_roi", {})
            inefficient = channel_roi.get("recommendations", {}).get("channels_to_review", [])
            if inefficient:
                summary["recommendations"].append(f"建议优化招聘渠道：{', '.join(inefficient[:3])}")
        
        cross = results.get("cross_analysis", {})
        if cross:
            for key, analysis in cross.items():
                if analysis.get("insight"):
                    summary["key_findings"].append(analysis["insight"])
        
        return summary
