"""
分析缓存管理器
提供 MongoDB 缓存层，支持 TTL 自动过期
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from Logging import logger

from src.data.mongodb import mongodb


class CacheManager:
    """分析缓存管理器"""
    
    # 缓存统计
    _stats = {
        "hits": 0,
        "misses": 0
    }
    
    def __init__(self, default_ttl: int = None):
        """
        初始化缓存管理器
        
        Args:
            default_ttl: 默认 TTL（秒），默认从环境变量读取或使用 3600
        """
        self.default_ttl = default_ttl or int(os.getenv("ANALYSIS_CACHE_TTL", "3600"))
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """获取缓存统计"""
        total = cls._stats["hits"] + cls._stats["misses"]
        hit_rate = (cls._stats["hits"] / total * 100) if total > 0 else 0
        return {
            "hits": cls._stats["hits"],
            "misses": cls._stats["misses"],
            "hit_rate": round(hit_rate, 2),
            "total_requests": total
        }
    
    @classmethod
    def reset_stats(cls) -> None:
        """重置统计"""
        cls._stats = {"hits": 0, "misses": 0}
    
    @staticmethod
    def generate_cache_key(
        analysis_type: str,
        department_id: Optional[str] = None,
        granularity: str = "hour"
    ) -> str:
        """
        生成缓存键
        
        Args:
            analysis_type: 分析类型 (cross_analysis, recruitment, etc.)
            department_id: 部门 ID（可选）
            granularity: 时间粒度 (hour, day)
        
        Returns:
            缓存键字符串
        """
        now = datetime.utcnow()
        
        if granularity == "hour":
            time_part = now.strftime("%Y-%m-%d-%H")
        elif granularity == "day":
            time_part = now.strftime("%Y-%m-%d")
        else:
            time_part = now.strftime("%Y-%m-%d-%H")
        
        if department_id:
            return f"{analysis_type}_{time_part}_{department_id}"
        return f"{analysis_type}_{time_part}"
    
    async def get_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存
        
        Args:
            cache_key: 缓存键
        
        Returns:
            缓存数据，如果不存在或已过期返回 None
        """
        try:
            doc = await mongodb.analysis_cache.find_one({"cache_key": cache_key})
            
            if doc is None:
                self._stats["misses"] += 1
                logger.debug(f"Cache miss: {cache_key}")
                return None
            
            # 检查是否过期（虽然 TTL 索引会自动清理，但可能有延迟）
            if doc.get("expires_at") and doc["expires_at"] < datetime.utcnow():
                self._stats["misses"] += 1
                logger.debug(f"Cache expired: {cache_key}")
                return None
            
            self._stats["hits"] += 1
            logger.debug(f"Cache hit: {cache_key}")
            return doc.get("data")
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self._stats["misses"] += 1
            return None
    
    async def set_cache(
        self,
        cache_key: str,
        data: Dict[str, Any],
        analysis_type: str,
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存
        
        Args:
            cache_key: 缓存键
            data: 要缓存的数据
            analysis_type: 分析类型
            ttl: TTL（秒），默认使用 default_ttl
        
        Returns:
            是否成功
        """
        try:
            ttl = ttl or self.default_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            doc = {
                "cache_key": cache_key,
                "type": analysis_type,
                "data": data,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at
            }
            
            # upsert: 如果存在则更新，否则插入
            await mongodb.analysis_cache.replace_one(
                {"cache_key": cache_key},
                doc,
                upsert=True
            )
            
            logger.debug(f"Cache set: {cache_key}, TTL: {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def clear_cache(
        self,
        analysis_type: Optional[str] = None,
        cache_key: Optional[str] = None
    ) -> int:
        """
        清除缓存
        
        Args:
            analysis_type: 按类型清除（可选）
            cache_key: 按键清除（可选）
        
        Returns:
            删除的文档数
        """
        try:
            if cache_key:
                result = await mongodb.analysis_cache.delete_one({"cache_key": cache_key})
            elif analysis_type:
                result = await mongodb.analysis_cache.delete_many({"type": analysis_type})
            else:
                # 清除所有缓存
                result = await mongodb.analysis_cache.delete_many({})
            
            deleted = result.deleted_count
            logger.info(f"Cache cleared: {deleted} entries")
            return deleted
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0
    
    async def get_entries_count(self) -> int:
        """获取缓存条目数"""
        try:
            return await mongodb.analysis_cache.count_documents({})
        except Exception as e:
            logger.error(f"Cache count error: {e}")
            return 0


# 全局缓存管理器实例
cache_manager = CacheManager()
