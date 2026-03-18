"""
FastAPI 应用主入口
Multi-Agent 组织智能分析系统 API
"""

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from Logging import logger
from pydantic import BaseModel

from src.config import settings
from src.data.mongodb import init_mongodb, close_mongodb


# ============ 生命周期 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info("Starting HR Analytics API...")
    
    # 初始化 MongoDB
    db_config = settings.database.get("mongodb", {})
    await init_mongodb(
        uri=db_config.get("uri", "mongodb://localhost:27017"),
        database=db_config.get("database", "hr_analytics"),
        max_pool_size=db_config.get("max_pool_size", 100),
        min_pool_size=db_config.get("min_pool_size", 10),
    )
    
    logger.info("HR Analytics API started successfully")
    
    yield
    
    # 关闭
    logger.info("Shutting down HR Analytics API...")
    await close_mongodb()
    logger.info("HR Analytics API shut down")


# ============ 应用实例 ============

app = FastAPI(
    title="Multi-Agent 组织智能分析系统",
    description="""
    一个可处理 500 万级 HR 数据的多智能体组织分析系统。
    
    ## 功能模块
    
    * **数据治理** - 数据清洗、口径统一、质量评估
    * **招聘效能** - 渠道 ROI、漏斗分析、人岗匹配
    * **绩效目标** - OKR 分析、绩效分布、管理者风格
    * **人才风险** - 离职预测、高潜识别、团队稳定性
    * **组织健康** - 人效分析、编制分析、人口结构
    * **战略报告** - CEO 一页纸报告、Action List
    """,
    version="1.0.0",
    lifespan=lifespan,
)


# ============ 中间件 ============

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors.get("allow_origins", ["*"]),
    allow_credentials=True,
    allow_methods=settings.api.cors.get("allow_methods", ["*"]),
    allow_headers=settings.api.cors.get("allow_headers", ["*"]),
)


# 请求日志
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    import time
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"- {response.status_code} "
        f"- {duration:.3f}s"
    )
    
    return response


# ============ 全局异常处理 ============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "meta": {"request_id": request.headers.get("X-Request-ID", "")}
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "meta": {"request_id": request.headers.get("X-Request-ID", "")}
        }
    )


# ============ 响应模型 ============

class APIResponse(BaseModel):
    success: bool = True
    data: Any = None
    meta: Dict[str, Any] = {}


# ============ 基础路由 ============

@app.get("/", tags=["Root"])
async def root():
    """API 根路径"""
    return {
        "name": "Multi-Agent 组织智能分析系统",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查"""
    from src.data.mongodb import mongodb
    
    db_health = await mongodb.health_check()
    
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
        "components": {
            "api": "healthy",
            "database": db_health
        }
    }


# ============ API 路由 ============

from src.api.routes import analysis, data, reports, chat, system
from src.api.websocket import ws_manager

app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(data.router, prefix="/api/v1/data", tags=["Data"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(system.router, prefix="/api/v1/system", tags=["System"])


# WebSocket 端点
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/analysis/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket 端点，用于接收分析任务进度"""
    await ws_manager.connect(websocket, task_id)
    try:
        while True:
            # 保持连接，等待客户端消息或断开
            data = await websocket.receive_text()
            # 可以处理客户端发送的消息（如取消任务）
            if data == "cancel":
                await ws_manager.fail_task(task_id, "用户取消")
                break
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, task_id)


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
