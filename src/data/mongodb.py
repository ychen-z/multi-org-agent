"""
MongoDB 连接管理器
提供异步连接池和数据库操作
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import IndexModel, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from loguru import logger


class MongoDB:
    """MongoDB 异步连接管理器"""
    
    _instance: Optional["MongoDB"] = None
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(
        self,
        uri: str = "mongodb://localhost:27017",
        database: str = "hr_analytics",
        max_pool_size: int = 100,
        min_pool_size: int = 10,
    ) -> None:
        """连接到 MongoDB"""
        if self._client is not None:
            logger.warning("MongoDB already connected")
            return
        
        try:
            self._client = AsyncIOMotorClient(
                uri,
                maxPoolSize=max_pool_size,
                minPoolSize=min_pool_size,
                serverSelectionTimeoutMS=5000,
            )
            
            # 验证连接
            await self._client.admin.command("ping")
            
            self._db = self._client[database]
            logger.info(f"Connected to MongoDB: {database}")
            
            # 创建索引
            await self._create_indexes()
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Disconnected from MongoDB")
    
    @property
    def client(self) -> AsyncIOMotorClient:
        """获取客户端实例"""
        if self._client is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return self._client
    
    @property
    def db(self) -> AsyncIOMotorDatabase:
        """获取数据库实例"""
        if self._db is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return self._db
    
    def collection(self, name: str) -> AsyncIOMotorCollection:
        """获取集合"""
        return self.db[name]
    
    # 集合快捷访问
    @property
    def employees(self) -> AsyncIOMotorCollection:
        return self.collection("employees")
    
    @property
    def departments(self) -> AsyncIOMotorCollection:
        return self.collection("departments")
    
    @property
    def performance_records(self) -> AsyncIOMotorCollection:
        return self.collection("performance_records")
    
    @property
    def recruitment_records(self) -> AsyncIOMotorCollection:
        return self.collection("recruitment_records")
    
    @property
    def risk_assessments(self) -> AsyncIOMotorCollection:
        return self.collection("risk_assessments")
    
    @property
    def analysis_cache(self) -> AsyncIOMotorCollection:
        return self.collection("analysis_cache")
    
    async def _create_indexes(self) -> None:
        """创建数据库索引"""
        try:
            # employees 索引
            await self.employees.create_indexes([
                IndexModel([("employee_id", ASCENDING)], unique=True),
                IndexModel([("department_id", ASCENDING)]),
                IndexModel([("status", ASCENDING), ("department_id", ASCENDING)]),
                IndexModel([("hire_date", ASCENDING)]),
                IndexModel([("manager_id", ASCENDING)]),
                IndexModel([("level", ASCENDING)]),
            ])
            
            # departments 索引
            await self.departments.create_indexes([
                IndexModel([("department_id", ASCENDING)], unique=True),
                IndexModel([("parent_id", ASCENDING)]),
            ])
            
            # performance_records 索引
            await self.performance_records.create_indexes([
                IndexModel([("employee_id", ASCENDING), ("period", ASCENDING)]),
                IndexModel([("period", ASCENDING), ("rating", ASCENDING)]),
                IndexModel([("reviewer_id", ASCENDING)]),
            ])
            
            # recruitment_records 索引
            await self.recruitment_records.create_indexes([
                IndexModel([("channel", ASCENDING), ("created_at", DESCENDING)]),
                IndexModel([("stage", ASCENDING)]),
                IndexModel([("requisition_id", ASCENDING)]),
                IndexModel([("position_id", ASCENDING)]),
            ])
            
            # risk_assessments 索引
            await self.risk_assessments.create_indexes([
                IndexModel([("employee_id", ASCENDING), ("assessment_date", DESCENDING)]),
                IndexModel([("risk_level", ASCENDING)]),
                IndexModel([("turnover_risk_score", DESCENDING)]),
            ])
            
            # analysis_cache 索引 (TTL 索引用于自动过期)
            await self.analysis_cache.create_indexes([
                IndexModel([("cache_key", ASCENDING)], unique=True),
                IndexModel([("type", ASCENDING)]),
                IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
            ])
            
            logger.info("Database indexes created")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def health_check(self) -> dict:
        """健康检查"""
        try:
            await self._client.admin.command("ping")
            
            # 获取数据库统计
            stats = await self.db.command("dbStats")
            
            return {
                "status": "healthy",
                "database": self.db.name,
                "collections": stats.get("collections", 0),
                "dataSize": stats.get("dataSize", 0),
                "indexSize": stats.get("indexSize", 0),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# 全局实例
mongodb = MongoDB()


@asynccontextmanager
async def get_mongodb():
    """上下文管理器，用于获取数据库连接"""
    yield mongodb


async def init_mongodb(
    uri: str = "mongodb://localhost:27017",
    database: str = "hr_analytics",
    **kwargs
) -> MongoDB:
    """初始化 MongoDB 连接"""
    await mongodb.connect(uri=uri, database=database, **kwargs)
    return mongodb


async def close_mongodb() -> None:
    """关闭 MongoDB 连接"""
    await mongodb.disconnect()
