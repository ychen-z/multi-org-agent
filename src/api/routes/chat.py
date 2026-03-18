"""
对话接口路由
支持 SSE 流式对话和普通对话
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from Logging import logger

from src.agents.conversational import ConversationalAgent, SSEEvent, SSEEventType
from src.llm.factory import get_llm


router = APIRouter()

# 全局 ConversationalAgent 实例
_conversational_agent: Optional[ConversationalAgent] = None


def get_conversational_agent() -> ConversationalAgent:
    """获取或创建 ConversationalAgent 实例"""
    global _conversational_agent
    if _conversational_agent is None:
        llm = get_llm()  # 自动从配置获取默认 provider
        _conversational_agent = ConversationalAgent(llm=llm)
    return _conversational_agent


class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # user / assistant
    content: str


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    history: Optional[List[ChatMessage]] = None
    context: Optional[dict] = None


class ChatStreamRequest(BaseModel):
    """流式对话请求"""
    message: str
    history: Optional[List[ChatMessage]] = None


@router.post("/")
async def chat(request: ChatRequest):
    """普通对话式分析"""
    try:
        agent = get_conversational_agent()
        
        # 转换历史格式
        history = []
        if request.history:
            history = [{"role": m.role, "content": m.content} for m in request.history]
        
        # 收集所有输出
        full_content = ""
        thinking_steps = []
        suggestions = []
        
        async for event in agent.process_stream(request.message, history):
            if event.event == SSEEventType.CONTENT:
                full_content += event.data.get("delta", "")
            elif event.event in [SSEEventType.THINK, SSEEventType.ACTION, SSEEventType.OBSERVATION]:
                thinking_steps.append(event.data)
            elif event.event == SSEEventType.DONE:
                suggestions = event.data.get("suggestions", [])
            elif event.event == SSEEventType.ERROR:
                raise HTTPException(status_code=500, detail=event.data.get("error"))
        
        return {
            "success": True,
            "data": {
                "message": full_content,
                "thinking": thinking_steps,
                "suggestions": suggestions
            }
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest):
    """
    流式对话分析 (SSE)
    
    返回 Server-Sent Events 流，包含以下事件类型：
    - think: 思考过程 {"type": "thought", "content": "..."}
    - plan: 执行计划 {"reasoning": "...", "steps": [...]}
    - action: 执行动作 {"step": 1, "action": "...", "agent": "..."}
    - observation: 观察结果 {"step": 1, "result": "..."}
    - content: 回复内容 {"delta": "..."}
    - done: 完成 {"suggestions": [...]}
    - error: 错误 {"error": "..."}
    """
    
    async def generate_sse():
        """生成 SSE 事件流"""
        try:
            agent = get_conversational_agent()
            
            # 转换历史格式
            history = []
            if request.history:
                history = [{"role": m.role, "content": m.content} for m in request.history]
            
            # 流式处理
            async for event in agent.process_stream(request.message, history):
                yield event.to_sse()
                
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            error_event = SSEEvent(
                event=SSEEventType.ERROR,
                data={"error": str(e)}
            )
            yield error_event.to_sse()
    
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
        }
    )


@router.get("/health")
async def chat_health():
    """对话服务健康检查"""
    return {
        "status": "ok",
        "agent_initialized": _conversational_agent is not None
    }