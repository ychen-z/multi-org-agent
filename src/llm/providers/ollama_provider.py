"""
Ollama 本地模型 Provider 实现
"""

import json
from typing import List, AsyncGenerator

import httpx
from Logging import logger

from ..base import LLMProvider, Message, Tool, ToolCall, ToolCallResult


class OllamaProvider(LLMProvider):
    """Ollama 本地模型 Provider"""
    
    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> str:
        """普通对话"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": self._convert_messages(messages),
                    "options": {
                        "temperature": kwargs.get("temperature", self.temperature),
                        "num_predict": kwargs.get("max_tokens", self.max_tokens),
                    },
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
    
    async def chat_with_tools(
        self,
        messages: List[Message],
        tools: List[Tool],
        **kwargs
    ) -> ToolCallResult:
        """带工具的对话 (Ollama 工具调用支持有限)"""
        # Ollama 对工具的支持有限，这里使用提示词方式
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in tools
        ])
        
        system_prompt = f"""你可以使用以下工具：
{tool_descriptions}

如果需要使用工具，请用以下 JSON 格式回复：
{{"tool": "工具名", "arguments": {{参数}}}}

否则直接回答问题。"""
        
        # 在消息前添加系统提示
        enhanced_messages = [
            Message(role="system", content=system_prompt)
        ] + messages
        
        content = await self.chat(enhanced_messages, **kwargs)
        
        # 尝试解析工具调用
        tool_calls = []
        try:
            if content.strip().startswith("{") and "tool" in content:
                data = json.loads(content)
                if "tool" in data:
                    tool_calls.append(ToolCall(
                        id="ollama-1",
                        name=data["tool"],
                        arguments=data.get("arguments", {})
                    ))
                    content = ""
        except json.JSONDecodeError:
            pass
        
        return ToolCallResult(
            content=content,
            tool_calls=tool_calls,
            finish_reason="stop"
        )
    
    async def stream_chat(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": self._convert_messages(messages),
                    "options": {
                        "temperature": kwargs.get("temperature", self.temperature),
                        "num_predict": kwargs.get("max_tokens", self.max_tokens),
                    },
                    "stream": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Ollama stream_chat error: {e}")
            raise
    
    async def list_models(self) -> List[str]:
        """列出可用模型"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Ollama list_models error: {e}")
            return []
