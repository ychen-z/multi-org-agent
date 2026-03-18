"""
对话式 AI 洞察 Agent
支持多轮对话、思维链展示、跨 Agent 协作
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum

from Logging import logger
from pydantic import BaseModel

from .base_agent import BaseAgent, AgentMessage, AgentResponse


# ============== 数据模型 ==============

class SSEEventType(str, Enum):
    """SSE 事件类型"""
    THINK = "think"
    PLAN = "plan"
    ACTION = "action"
    OBSERVATION = "observation"
    CONTENT = "content"
    DONE = "done"
    ERROR = "error"


@dataclass
class SSEEvent:
    """SSE 事件"""
    event: SSEEventType
    data: Dict[str, Any]
    
    def to_sse(self) -> str:
        """转换为 SSE 格式字符串"""
        return f"event: {self.event.value}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


class PlanStep(BaseModel):
    """执行计划步骤"""
    step: int
    agent: Optional[str] = None  # talent_risk, recruitment, performance, org_health
    action: str                   # 具体动作描述
    depends_on: List[int] = []   # 依赖的步骤编号


class ExecutionPlan(BaseModel):
    """执行计划"""
    reasoning: str               # 规划理由
    steps: List[PlanStep]


class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # user, assistant
    content: str


# ============== ConversationalAgent ==============

class ConversationalAgent(BaseAgent):
    """对话式 AI 洞察 Agent"""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="conversational",
            name="对话式 AI 助手",
            description="支持多轮对话的智能分析助手，可协调多个专业 Agent 完成复杂分析",
            **kwargs
        )
        
        # 专业 Agent 注册表（延迟初始化避免循环导入）
        self._agents: Dict[str, BaseAgent] = {}
        self._agents_initialized = False
        
        # Agent 能力描述
        self.agent_capabilities = {
            "talent_risk": "离职风险分析、高风险员工识别、团队稳定性评估、人才保留建议",
            "recruitment": "招聘渠道 ROI、漏斗转化分析、招聘周期、瓶颈识别、招聘优化建议",
            "performance": "绩效分布分析、OKR 完成度、管理者评分风格、强制分布合规、绩效通胀检测",
            "org_health": "人效分析、编制利用率、组织结构、人口结构、组织健康度评分"
        }
    
    def _register_tools(self):
        """注册工具（对话 Agent 不需要传统工具）"""
        pass
    
    def _init_agents(self):
        """延迟初始化专业 Agent"""
        if self._agents_initialized:
            return
        
        # 延迟导入避免循环依赖
        from .talent_risk import TalentRiskAgent
        from .recruitment import RecruitmentAgent
        from .performance import PerformanceAgent
        from .org_health import OrgHealthAgent
        
        self._agents = {
            "talent_risk": TalentRiskAgent(llm=self.llm),
            "recruitment": RecruitmentAgent(llm=self.llm),
            "performance": PerformanceAgent(llm=self.llm),
            "org_health": OrgHealthAgent(llm=self.llm),
        }
        self._agents_initialized = True
        logger.info(f"Initialized {len(self._agents)} specialized agents")
    
    async def process(self, message: AgentMessage) -> AgentResponse:
        """处理消息（同步版本，用于简单调用）"""
        task = message.payload.get("task", "")
        history = message.payload.get("history", [])
        
        # 收集所有流式输出
        full_content = ""
        thinking_steps = []
        suggestions = []
        
        async for event in self.process_stream(task, history):
            if event.event == SSEEventType.CONTENT:
                full_content += event.data.get("delta", "")
            elif event.event in [SSEEventType.THINK, SSEEventType.ACTION, SSEEventType.OBSERVATION]:
                thinking_steps.append(event.data)
            elif event.event == SSEEventType.DONE:
                suggestions = event.data.get("suggestions", [])
        
        return AgentResponse(
            success=True,
            data={
                "content": full_content,
                "thinking": thinking_steps,
                "suggestions": suggestions
            }
        )
    
    async def process_stream(
        self, 
        message: str, 
        history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        流式处理对话，返回 SSE 事件流
        
        Args:
            message: 用户消息
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]
        
        Yields:
            SSEEvent: 各类 SSE 事件
        """
        history = history or []
        self._init_agents()
        
        try:
            # Phase 1: 意图理解
            yield SSEEvent(
                event=SSEEventType.THINK,
                data={"type": "thought", "content": "让我分析一下这个问题..."}
            )
            
            # Phase 2: 生成执行计划
            plan = await self._generate_plan(message, history)
            
            yield SSEEvent(
                event=SSEEventType.THINK,
                data={"type": "thought", "content": plan.reasoning}
            )
            
            yield SSEEvent(
                event=SSEEventType.PLAN,
                data={
                    "reasoning": plan.reasoning,
                    "steps": [s.dict() for s in plan.steps]
                }
            )
            
            # Phase 3: 执行计划
            results = {}
            sorted_steps = self._topological_sort(plan.steps)
            
            for step in sorted_steps:
                # 发送 action 事件
                yield SSEEvent(
                    event=SSEEventType.ACTION,
                    data={
                        "step": step.step,
                        "action": step.action,
                        "agent": step.agent
                    }
                )
                
                # 执行步骤
                if step.agent:
                    result = await self._execute_agent_step(step, results)
                else:
                    result = await self._execute_correlation(step, results)
                
                results[step.step] = result
                
                # 发送 observation 事件
                yield SSEEvent(
                    event=SSEEventType.OBSERVATION,
                    data={
                        "step": step.step,
                        "result": self._summarize_result(result)
                    }
                )
                
                # 生成步骤反思
                reflection = await self._generate_step_reflection(step, result)
                yield SSEEvent(
                    event=SSEEventType.THINK,
                    data={"type": "thought", "content": reflection}
                )
            
            # Phase 4: 综合生成回复
            yield SSEEvent(
                event=SSEEventType.THINK,
                data={"type": "thought", "content": "综合以上数据，生成分析结论..."}
            )
            
            async for chunk in self._stream_synthesis(message, results, history):
                yield SSEEvent(
                    event=SSEEventType.CONTENT,
                    data={"delta": chunk}
                )
            
            # Phase 5: 生成建议问题
            suggestions = await self._generate_suggestions(message, results)
            yield SSEEvent(
                event=SSEEventType.DONE,
                data={"suggestions": suggestions}
            )
            
        except Exception as e:
            logger.error(f"ConversationalAgent error: {e}")
            yield SSEEvent(
                event=SSEEventType.ERROR,
                data={"error": str(e)}
            )
    
    async def _generate_plan(
        self, 
        message: str, 
        history: List[Dict[str, str]]
    ) -> ExecutionPlan:
        """LLM 生成执行计划"""
        
        history_text = self._format_history(history) if history else "无历史对话"
        
        prompt = f"""你是一个组织智能分析系统的规划器。根据用户问题，生成执行计划。

## 用户问题
{message}

## 对话历史
{history_text}

## 可用的专业 Agent
{self._format_agent_capabilities()}

## 任务
分析用户问题，确定需要调用哪些 Agent，生成执行计划。

## 输出格式
请返回 JSON 格式：
```json
{{
  "reasoning": "简要解释为什么这样规划（1-2 句话）",
  "steps": [
    {{"step": 1, "agent": "agent_name", "action": "具体动作描述", "depends_on": []}},
    {{"step": 2, "agent": "agent_name", "action": "具体动作描述", "depends_on": []}},
    {{"step": 3, "agent": null, "action": "关联分析描述", "depends_on": [1, 2]}}
  ]
}}
```

## 规则
1. 简单问题只需 1-2 个步骤
2. 跨领域问题需要多个 Agent 协作
3. 需要关联分析时，设置 depends_on 并将 agent 设为 null
4. action 用中文描述，简洁明了
5. 最多 5 个步骤

请直接返回 JSON，不要有其他内容。"""

        try:
            response = await self.chat(prompt)
            
            # 提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                plan_data = json.loads(json_match.group())
                return ExecutionPlan(**plan_data)
            else:
                # 回退：简单单步计划
                return self._create_fallback_plan(message)
                
        except Exception as e:
            logger.warning(f"Failed to generate plan: {e}")
            return self._create_fallback_plan(message)
    
    def _create_fallback_plan(self, message: str) -> ExecutionPlan:
        """创建回退计划"""
        # 根据关键词判断应该调用哪个 Agent
        agent = "talent_risk"  # 默认
        action = "分析相关数据"
        
        if any(kw in message for kw in ["招聘", "渠道", "漏斗", "候选人"]):
            agent = "recruitment"
            action = "分析招聘相关数据"
        elif any(kw in message for kw in ["绩效", "OKR", "评分", "考核"]):
            agent = "performance"
            action = "分析绩效相关数据"
        elif any(kw in message for kw in ["组织", "编制", "结构", "人效", "健康"]):
            agent = "org_health"
            action = "分析组织健康数据"
        elif any(kw in message for kw in ["离职", "风险", "流失", "稳定"]):
            agent = "talent_risk"
            action = "分析人才风险数据"
        
        return ExecutionPlan(
            reasoning=f"这是一个关于{agent.replace('_', ' ')}的问题，直接查询相关数据",
            steps=[
                PlanStep(step=1, agent=agent, action=action, depends_on=[])
            ]
        )
    
    def _topological_sort(self, steps: List[PlanStep]) -> List[PlanStep]:
        """拓扑排序，确保依赖关系正确"""
        # 简单实现：按 step 编号排序，因为 depends_on 只会依赖更小的 step
        return sorted(steps, key=lambda s: s.step)
    
    async def _execute_agent_step(
        self, 
        step: PlanStep, 
        previous_results: Dict[int, Any]
    ) -> Dict[str, Any]:
        """执行专业 Agent 步骤"""
        
        agent = self._agents.get(step.agent)
        if not agent:
            logger.warning(f"Agent not found: {step.agent}")
            return {"error": f"Agent {step.agent} not found"}
        
        # 构建消息
        message = AgentMessage(
            agent_id=step.agent,
            message_type="request",
            task_type="analysis",
            payload={
                "task": step.action,
                "include_insights": True  # 请求 AI 洞察
            }
        )
        
        try:
            response = await agent.process(message)
            if response.success:
                return response.data
            else:
                return {"error": response.error}
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            return {"error": str(e)}
    
    async def _execute_correlation(
        self, 
        step: PlanStep, 
        previous_results: Dict[int, Any]
    ) -> Dict[str, Any]:
        """执行关联分析"""
        
        # 收集依赖步骤的结果
        dep_data = {
            f"step_{dep}": previous_results.get(dep, {})
            for dep in step.depends_on
        }
        
        # 使用 LLM 进行关联分析
        prompt = f"""基于以下多个数据源的结果，进行关联分析：

## 任务
{step.action}

## 数据源
{json.dumps(dep_data, ensure_ascii=False, indent=2, default=str)[:3000]}

## 要求
1. 找出数据之间的关联
2. 识别交叉影响
3. 给出综合结论

请直接给出分析结果。"""

        try:
            analysis = await self.chat(prompt)
            return {
                "type": "correlation",
                "analysis": analysis,
                "source_steps": step.depends_on
            }
        except Exception as e:
            logger.warning(f"Correlation analysis failed: {e}")
            return {
                "type": "correlation",
                "analysis": "关联分析暂时无法完成",
                "source_steps": step.depends_on
            }
    
    async def _generate_step_reflection(
        self, 
        step: PlanStep, 
        result: Dict[str, Any]
    ) -> str:
        """生成步骤反思"""
        
        # 从结果中提取关键信息
        summary = self._summarize_result(result)
        
        # 简单反思，不调用 LLM（节省时间）
        if "error" in result:
            return f"执行 {step.action} 时遇到问题：{result.get('error')}"
        
        if step.agent:
            return f"已获取{step.action}的数据，继续下一步..."
        else:
            return f"完成关联分析，发现了一些有价值的关联..."
    
    async def _stream_synthesis(
        self, 
        message: str, 
        results: Dict[int, Any],
        history: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """流式生成最终回复"""
        
        # 准备数据摘要
        data_summary = self._prepare_data_summary(results)
        
        prompt = f"""基于以下分析数据，回答用户问题。

## 用户问题
{message}

## 分析数据
{data_summary}

## 要求
1. 直接回答用户问题
2. 用数据支撑观点
3. 给出可操作的建议
4. 使用 Markdown 格式
5. 简洁有力，不要太长

请直接回答，不要重复问题。"""

        try:
            # 使用流式 LLM（如果支持）
            if hasattr(self.llm, 'stream_chat'):
                from src.llm.base import Message, MessageRole
                messages = [Message(role=MessageRole.USER, content=prompt)]
                async for chunk in self.llm.stream_chat(messages):
                    yield chunk
            else:
                # 非流式回退
                response = await self.chat(prompt)
                # 模拟流式输出
                for char in response:
                    yield char
                    await asyncio.sleep(0.01)  # 小延迟模拟流式
                    
        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            yield f"抱歉，生成回复时遇到问题：{str(e)}"
    
    async def _generate_suggestions(
        self, 
        message: str, 
        results: Dict[int, Any]
    ) -> List[str]:
        """生成后续问题建议"""
        
        # 基于结果类型生成建议
        suggestions = []
        
        for step_id, result in results.items():
            if isinstance(result, dict):
                # 根据不同的分析类型添加建议
                if "high_risk_employees" in result or "risk" in str(result).lower():
                    suggestions.extend([
                        "哪些员工需要重点关注？",
                        "如何降低离职风险？"
                    ])
                if "channel" in str(result).lower() or "recruitment" in str(result).lower():
                    suggestions.extend([
                        "如何优化招聘渠道？",
                        "招聘漏斗瓶颈在哪里？"
                    ])
                if "performance" in str(result).lower() or "distribution" in str(result).lower():
                    suggestions.extend([
                        "绩效分布是否合理？",
                        "哪些团队需要绩效校准？"
                    ])
                if "health" in str(result).lower() or "org" in str(result).lower():
                    suggestions.extend([
                        "组织结构如何优化？",
                        "哪些部门需要关注？"
                    ])
        
        # 去重并限制数量
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)
                if len(unique_suggestions) >= 3:
                    break
        
        # 如果没有建议，添加通用建议
        if not unique_suggestions:
            unique_suggestions = [
                "查看详细数据分析",
                "生成完整报告",
                "对比其他部门"
            ]
        
        return unique_suggestions
    
    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """格式化对话历史"""
        if not history:
            return "无"
        
        formatted = []
        for msg in history[-6:]:  # 只取最近 6 条
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")[:200]  # 截断
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _format_agent_capabilities(self) -> str:
        """格式化 Agent 能力描述"""
        lines = []
        for agent_id, capabilities in self.agent_capabilities.items():
            lines.append(f"- {agent_id}: {capabilities}")
        return "\n".join(lines)
    
    def _summarize_result(self, result: Dict[str, Any], max_length: int = 500) -> str:
        """摘要结果"""
        if not result:
            return "{}"
        
        # 提取关键字段
        summary = {}
        important_keys = [
            "summary", "overall", "health_score", "total", "count",
            "rate", "score", "level", "status", "assessment",
            "ai_insights", "recommendations", "bottleneck"
        ]
        
        for key, value in result.items():
            if any(ik in key.lower() for ik in important_keys):
                summary[key] = value
        
        # 如果没有找到重要字段，取前几个
        if not summary:
            summary = dict(list(result.items())[:5])
        
        result_str = json.dumps(summary, ensure_ascii=False, default=str)
        if len(result_str) > max_length:
            result_str = result_str[:max_length] + "..."
        
        return result_str
    
    def _prepare_data_summary(self, results: Dict[int, Any]) -> str:
        """准备数据摘要用于最终合成"""
        summaries = []
        
        for step_id, result in results.items():
            summary = self._summarize_result(result, max_length=800)
            summaries.append(f"### Step {step_id}\n{summary}")
        
        return "\n\n".join(summaries)
