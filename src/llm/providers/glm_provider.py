"""
智谱 GLM Provider 实现
"""

import json
from typing import List, AsyncGenerator

from zhipuai import ZhipuAI
from Logging import logger

from ..base import LLMProvider, Message, Tool, ToolCall, ToolCallResult


class GLMProvider(LLMProvider):
    """智谱 GLM Provider"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "glm-4",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.client = ZhipuAI(api_key=api_key)
    
    async def chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> str:
        """普通对话"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self._convert_messages(messages),
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"GLM chat error: {e}")
            raise
    
    async def chat_with_tools(
        self,
        messages: List[Message],
        tools: List[Tool],
        **kwargs
    ) -> ToolCallResult:
        """带工具的对话"""
        glm_tools = self._convert_tools(tools)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self._convert_messages(messages),
                tools=glm_tools,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )
            
            message = response.choices[0].message
            tool_calls = []
            
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments)
                    ))
            
            return ToolCallResult(
                content=message.content or "",
                tool_calls=tool_calls,
                finish_reason=response.choices[0].finish_reason
            )
        except Exception as e:
            logger.error(f"GLM chat_with_tools error: {e}")
            raise
    
    async def stream_chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self._convert_messages(messages),
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True,
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"GLM stream_chat error: {e}")
            raise
