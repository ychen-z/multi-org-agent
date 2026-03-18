"""
Agent 基类定义
提供所有 Agent 的通用接口和功能
"""

import uuid
import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from Logging import logger

from src.llm.base import LLMProvider, Message, MessageRole, Tool
from src.llm.factory import get_llm


# 触发 LLM 洞察的关键词
INSIGHT_TRIGGER_KEYWORDS = [
    "分析", "为什么", "原因", "建议", "怎么办", "如何",
    "洞察", "趋势", "预测", "解读", "评估", "诊断"
]

# 不触发 LLM 的关键词
NO_INSIGHT_KEYWORDS = [
    "多少", "几个", "列出", "显示", "查询", "获取"
]

# 默认洞察 Prompt 模板
DEFAULT_INSIGHT_PROMPT = """你是一位资深的 HR 数据分析专家。

## 数据摘要
{data_summary}

## 用户问题
{user_query}

## 要求
请基于数据回答用户问题，提供：
1. 关键发现（2-3 条）
2. 原因分析（如适用）
3. 建议行动（如适用）

保持简洁，每条不超过 50 字。直接返回分析内容，不要说"根据数据"等开场白。
"""

# LLM 调用超时（秒）
LLM_TIMEOUT = 10


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentMessage:
    """Agent 间通信消息"""
    agent_id: str
    message_type: str  # request / response / error
    task_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "message_type": self.message_type,
            "task_type": self.task_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
        }


@dataclass
class AgentResponse:
    """Agent 响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metrics": self.metrics,
        }


@dataclass
class AgentTool:
    """Agent 工具"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    
    def to_llm_tool(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )


class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        llm_provider: Optional[str] = None,
        **kwargs
    ):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE
        self.llm = get_llm(provider=llm_provider)
        self.tools: Dict[str, AgentTool] = {}
        self.config = kwargs
        
        # 注册工具
        self._register_tools()
        
        logger.info(f"Agent initialized: {self.agent_id} ({self.name})")
    
    @abstractmethod
    def _register_tools(self):
        """注册 Agent 的工具（子类实现）"""
        pass
    
    @abstractmethod
    async def process(self, message: AgentMessage) -> AgentResponse:
        """处理消息（子类实现）"""
        pass
    
    def register_tool(self, tool: AgentTool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.debug(f"Agent {self.agent_id}: Registered tool {tool.name}")
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """执行工具"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool = self.tools[tool_name]
        start_time = datetime.utcnow()
        
        try:
            result = await tool.handler(**kwargs) if asyncio.iscoroutinefunction(tool.handler) else tool.handler(**kwargs)
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.debug(f"Agent {self.agent_id}: Tool {tool_name} completed in {duration:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Agent {self.agent_id}: Tool {tool_name} failed: {e}")
            raise
    
    async def chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """与 LLM 对话"""
        messages = []
        
        if system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=system_prompt))
        
        messages.append(Message(role=MessageRole.USER, content=prompt))
        
        return await self.llm.chat(messages)
    
    async def chat_with_tools(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_iterations: int = 5
    ) -> str:
        """带工具调用的对话"""
        messages = []
        
        if system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=system_prompt))
        
        messages.append(Message(role=MessageRole.USER, content=prompt))
        
        llm_tools = [tool.to_llm_tool() for tool in self.tools.values()]
        
        for _ in range(max_iterations):
            result = await self.llm.chat_with_tools(messages, llm_tools)
            
            if not result.tool_calls:
                return result.content
            
            # 执行工具调用
            messages.append(Message(
                role=MessageRole.ASSISTANT,
                content=result.content,
                tool_calls=[{
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": str(tc.arguments)}
                } for tc in result.tool_calls]
            ))
            
            for tool_call in result.tool_calls:
                try:
                    tool_result = await self.execute_tool(tool_call.name, **tool_call.arguments)
                    messages.append(Message(
                        role=MessageRole.TOOL,
                        content=str(tool_result),
                        tool_call_id=tool_call.id
                    ))
                except Exception as e:
                    messages.append(Message(
                        role=MessageRole.TOOL,
                        content=f"Error: {str(e)}",
                        tool_call_id=tool_call.id
                    ))
        
        return "Max iterations reached"
    
    def get_system_prompt(self) -> str:
        """获取 Agent 的系统提示词（子类可覆盖）"""
        return f"""你是 {self.name}。

{self.description}

请根据用户的请求完成任务。如果需要使用工具，请调用相应的工具。
确保你的回答准确、专业、有条理。
"""
    
    async def run(self, task: str, **kwargs) -> AgentResponse:
        """运行 Agent"""
        self.status = AgentStatus.RUNNING
        start_time = datetime.utcnow()
        
        try:
            message = AgentMessage(
                agent_id=self.agent_id,
                message_type="request",
                task_type="run",
                payload={"task": task, **kwargs}
            )
            
            response = await self.process(message)
            self.status = AgentStatus.COMPLETED
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            response.metrics["duration_seconds"] = duration
            
            return response
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            logger.error(f"Agent {self.agent_id} failed: {e}")
            return AgentResponse(
                success=False,
                error=str(e),
                metrics={"duration_seconds": (datetime.utcnow() - start_time).total_seconds()}
            )


    # ==================== 按需 LLM 洞察方法 ====================
    
    def _need_insights(self, task: str, include_insights: Optional[bool] = None) -> bool:
        """
        判断是否需要生成 AI 洞察
        
        Args:
            task: 用户任务描述
            include_insights: 显式指定是否需要洞察
        
        Returns:
            是否需要调用 LLM 生成洞察
        """
        # 显式指定优先
        if include_insights is not None:
            return include_insights
        
        task_lower = task.lower()
        
        # 检查是否包含不触发关键词
        for keyword in NO_INSIGHT_KEYWORDS:
            if keyword in task_lower:
                return False
        
        # 检查是否包含触发关键词
        for keyword in INSIGHT_TRIGGER_KEYWORDS:
            if keyword in task_lower:
                return True
        
        # 默认不触发（节省成本）
        return False
    
    async def generate_insights(
        self,
        data: Dict[str, Any],
        task: str,
        prompt_template: Optional[str] = None,
        timeout: int = LLM_TIMEOUT
    ) -> Optional[str]:
        """
        生成 AI 洞察
        
        Args:
            data: 分析数据
            task: 用户任务
            prompt_template: 自定义 prompt 模板（可选）
            timeout: 超时时间（秒）
        
        Returns:
            AI 生成的洞察文本，超时或失败返回 None
        """
        try:
            # 准备数据摘要（限制长度）
            data_summary = self._summarize_data(data)
            
            # 构建 prompt
            template = prompt_template or DEFAULT_INSIGHT_PROMPT
            prompt = template.format(
                data_summary=data_summary,
                user_query=task
            )
            
            # 带超时的 LLM 调用
            response = await asyncio.wait_for(
                self.chat(prompt),
                timeout=timeout
            )
            
            logger.info(f"Agent {self.agent_id}: AI insights generated")
            return response
            
        except asyncio.TimeoutError:
            logger.warning(f"Agent {self.agent_id}: LLM timeout after {timeout}s")
            return None
        except Exception as e:
            logger.warning(f"Agent {self.agent_id}: LLM insights failed: {e}")
            return None
    
    def _summarize_data(self, data: Dict[str, Any], max_length: int = 2000) -> str:
        """
        将数据转换为摘要字符串（限制长度）
        
        Args:
            data: 数据字典
            max_length: 最大字符数
        
        Returns:
            JSON 格式的数据摘要
        """
        try:
            # 简化数据：只保留关键字段，限制列表长度
            simplified = self._simplify_data(data)
            
            json_str = json.dumps(simplified, ensure_ascii=False, indent=2)
            
            if len(json_str) > max_length:
                json_str = json_str[:max_length] + "\n... (数据已截断)"
            
            return json_str
        except Exception:
            return str(data)[:max_length]
    
    def _simplify_data(self, data: Any, max_list_items: int = 5) -> Any:
        """简化数据结构"""
        if isinstance(data, dict):
            return {k: self._simplify_data(v, max_list_items) for k, v in data.items()}
        elif isinstance(data, list):
            if len(data) > max_list_items:
                return [self._simplify_data(item, max_list_items) for item in data[:max_list_items]] + [f"... 还有 {len(data) - max_list_items} 条"]
            return [self._simplify_data(item, max_list_items) for item in data]
        else:
            return data
    
    def _get_fallback_insight(self, data: Dict[str, Any]) -> str:
        """
        LLM 失败时的回退洞察（子类可覆盖）
        
        Args:
            data: 分析数据
        
        Returns:
            规则生成的简单洞察
        """
        return "暂无 AI 洞察，请查看详细数据。"
