"""
OpenAI Provider 实现
"""

import json
from typing import List, Dict, Any, Optional, AsyncGenerator

from openai import AsyncOpenAI
from Logging import logger

from ..base import LLMProvider, Message, Tool, ToolCall, ToolCallResult


class OpenAIProvider(LLMProvider):
    """OpenAI LLM Provider"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        base_url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    async def chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> str:
        """普通对话"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self._convert_messages(messages),
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise
    
    async def chat_with_tools(
        self,
        messages: List[Message],
        tools: List[Tool],
        **kwargs
    ) -> ToolCallResult:
        """带工具的对话"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self._convert_messages(messages),
                tools=self._convert_tools(tools),
                tool_choice=kwargs.get("tool_choice", "auto"),
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )
            
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            
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
                finish_reason=finish_reason
            )
        except Exception as e:
            logger.error(f"OpenAI chat_with_tools error: {e}")
            raise
    
    async def stream_chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=self._convert_messages(messages),
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI stream_chat error: {e}")
            raise
