"""
通义千问 (Qwen) Provider 实现
"""

from typing import List, AsyncGenerator

from dashscope import Generation
from dashscope.api_entities.dashscope_response import GenerationResponse
from loguru import logger

from ..base import LLMProvider, Message, Tool, ToolCall, ToolCallResult


class QwenProvider(LLMProvider):
    """通义千问 LLM Provider"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "qwen-max",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        super().__init__(model, temperature, max_tokens, **kwargs)
        import dashscope
        dashscope.api_key = api_key
    
    async def chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> str:
        """普通对话"""
        try:
            response = Generation.call(
                model=self.model,
                messages=self._convert_messages(messages),
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                result_format='message'
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise Exception(f"Qwen API error: {response.code} - {response.message}")
        except Exception as e:
            logger.error(f"Qwen chat error: {e}")
            raise
    
    async def chat_with_tools(
        self,
        messages: List[Message],
        tools: List[Tool],
        **kwargs
    ) -> ToolCallResult:
        """带工具的对话"""
        # Qwen 工具调用格式
        qwen_tools = []
        for tool in tools:
            qwen_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        
        try:
            response = Generation.call(
                model=self.model,
                messages=self._convert_messages(messages),
                tools=qwen_tools,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                result_format='message'
            )
            
            if response.status_code != 200:
                raise Exception(f"Qwen API error: {response.code}")
            
            message = response.output.choices[0].message
            tool_calls = []
            
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(ToolCall(
                        id=tc.get('id', ''),
                        name=tc['function']['name'],
                        arguments=tc['function']['arguments']
                    ))
            
            return ToolCallResult(
                content=message.content or "",
                tool_calls=tool_calls,
                finish_reason=response.output.choices[0].finish_reason
            )
        except Exception as e:
            logger.error(f"Qwen chat_with_tools error: {e}")
            raise
    
    async def stream_chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        try:
            responses = Generation.call(
                model=self.model,
                messages=self._convert_messages(messages),
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                result_format='message',
                stream=True,
                incremental_output=True
            )
            
            for response in responses:
                if response.status_code == 200:
                    content = response.output.choices[0].message.content
                    if content:
                        yield content
        except Exception as e:
            logger.error(f"Qwen stream_chat error: {e}")
            raise
