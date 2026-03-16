"""
对话接口路由
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # user / assistant
    content: str


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    history: Optional[List[ChatMessage]] = None
    context: Optional[dict] = None


@router.post("/")
async def chat(request: ChatRequest):
    """对话式分析"""
    # TODO: 调用主控 Agent 进行对话
    
    # 简单回复示例
    response_content = f"""收到您的问题："{request.message}"

我正在分析相关数据...

根据当前数据，我的分析如下：
1. 系统已初始化，可以进行组织智能分析
2. 请先通过 /api/v1/data/generate 生成模拟数据
3. 然后可以使用各分析接口进行详细分析

如需进一步帮助，请告诉我您想了解的具体问题。
"""
    
    return {
        "success": True,
        "data": {
            "message": response_content,
            "suggestions": [
                "分析招聘渠道 ROI",
                "查看绩效分布情况",
                "识别高风险员工",
                "生成战略报告"
            ]
        }
    }
