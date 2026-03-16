"""
Agent 基类定义
提供所有 Agent 的通用接口和功能
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from loguru import logger

from src.llm.base import LLMProvider, Message, MessageRole, Tool
from src.llm.factory import get_llm


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


# 需要导入 asyncio
import asyncio
