"""
系统接口路由
"""

from fastapi import APIRouter

from src.data.cache import cache_manager, CacheManager
from src.data.mongodb import mongodb


router = APIRouter()


@router.get("/cache-stats")
async def get_cache_stats():
    """获取缓存统计"""
    stats = CacheManager.get_stats()
    entries_count = await cache_manager.get_entries_count()
    
    return {
        "success": True,
        "data": {
            **stats,
            "entries_count": entries_count
        }
    }


@router.post("/cache-clear")
async def clear_cache():
    """清除所有缓存"""
    cleared = await cache_manager.clear_cache()
    CacheManager.reset_stats()
    
    return {
        "success": True,
        "data": {
            "cleared_entries": cleared
        }
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    db_health = await mongodb.health_check()
    
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "database": db_health
        }
    }
