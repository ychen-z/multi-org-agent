"""
WebSocket 进度推送
用于长时间运行任务的实时进度更新
"""

import asyncio
import json
from typing import Dict, Set
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # task_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # 任务进度缓存
        self.task_progress: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """建立连接"""
        await websocket.accept()
        
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        
        self.active_connections[task_id].add(websocket)
        logger.info(f"WebSocket connected for task: {task_id}")
        
        # 发送当前进度（如果有）
        if task_id in self.task_progress:
            await websocket.send_json(self.task_progress[task_id])
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """断开连接"""
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        logger.info(f"WebSocket disconnected for task: {task_id}")
    
    async def send_progress(
        self,
        task_id: str,
        progress: float,
        message: str,
        status: str = "running",
        data: dict = None
    ):
        """发送进度更新"""
        payload = {
            "task_id": task_id,
            "progress": progress,
            "message": message,
            "status": status,  # running, completed, failed
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 缓存进度
        self.task_progress[task_id] = payload
        
        # 广播给所有连接
        if task_id in self.active_connections:
            disconnected = set()
            
            for websocket in self.active_connections[task_id]:
                try:
                    await websocket.send_json(payload)
                except Exception as e:
                    logger.error(f"Error sending to websocket: {e}")
                    disconnected.add(websocket)
            
            # 清理断开的连接
            for ws in disconnected:
                self.active_connections[task_id].discard(ws)
    
    async def complete_task(self, task_id: str, result: dict = None):
        """标记任务完成"""
        await self.send_progress(
            task_id=task_id,
            progress=100,
            message="任务完成",
            status="completed",
            data=result
        )
        
        # 清理
        await asyncio.sleep(5)  # 保留5秒让客户端收到完成消息
        if task_id in self.task_progress:
            del self.task_progress[task_id]
    
    async def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        await self.send_progress(
            task_id=task_id,
            progress=-1,
            message=f"任务失败: {error}",
            status="failed"
        )
    
    async def update_progress(self, task_id: str, step: str, progress: int):
        """
        更新任务进度（供 Orchestrator 回调使用）
        
        Args:
            task_id: 任务 ID
            step: 当前步骤描述
            progress: 进度百分比 (0-100)
        """
        payload = {
            "type": "progress",
            "data": {
                "step": step,
                "progress": progress,
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # 缓存进度
        self.task_progress[task_id] = payload
        
        # 广播给所有连接
        if task_id in self.active_connections:
            disconnected = set()
            
            for websocket in self.active_connections[task_id]:
                try:
                    await websocket.send_json(payload)
                except Exception as e:
                    logger.warning(f"Error sending progress to websocket: {e}")
                    disconnected.add(websocket)
            
            # 清理断开的连接
            for ws in disconnected:
                self.active_connections[task_id].discard(ws)
        
        logger.debug(f"Progress update for {task_id}: {step} ({progress}%)")
    
    async def get_last_progress(self, task_id: str) -> dict:
        """获取最后的进度（用于重连时恢复）"""
        return self.task_progress.get(task_id)


# 全局连接管理器
ws_manager = ConnectionManager()


class ProgressTracker:
    """进度追踪器，用于在任务中报告进度"""
    
    def __init__(self, task_id: str, total_steps: int = 100):
        self.task_id = task_id
        self.total_steps = total_steps
        self.current_step = 0
    
    async def update(self, step: int = None, message: str = ""):
        """更新进度"""
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
        
        progress = min(100, (self.current_step / self.total_steps) * 100)
        await ws_manager.send_progress(
            task_id=self.task_id,
            progress=progress,
            message=message
        )
    
    async def complete(self, result: dict = None):
        """完成任务"""
        await ws_manager.complete_task(self.task_id, result)
    
    async def fail(self, error: str):
        """任务失败"""
        await ws_manager.fail_task(self.task_id, error)
