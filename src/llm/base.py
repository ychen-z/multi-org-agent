"""
LLM Provider 抽象层
支持多种 LLM 提供商的统一接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncGenerator
from enum import Enum

from pydantic import BaseModel


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """消息"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolCallResult:
    """工具调用结果"""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"


class Tool(BaseModel):
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]


class LLMProvider(ABC):
    """LLM Provider 基类"""
    
    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_config = kwargs
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> str:
        """普通对话"""
        pass
    
    @abstractmethod
    async def chat_with_tools(
        self,
        messages: List[Message],
        tools: List[Tool],
        **kwargs
    ) -> ToolCallResult:
        """带工具的对话"""
        pass
    
    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        pass
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict]:
        """转换消息格式（子类可覆盖）"""
        result = []
        for msg in messages:
            item = {
                "role": msg.role.value,
                "content": msg.content
            }
            if msg.name:
                item["name"] = msg.name
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                item["tool_calls"] = msg.tool_calls
            result.append(item)
        return result
    
    def _convert_tools(self, tools: List[Tool]) -> List[Dict]:
        """转换工具格式（子类可覆盖）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in tools
        ]
