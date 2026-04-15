"""
数据库连接管理
"""
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.core.config import DATABASE_URL


class DatabaseManager:
    """数据库管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)        # 无论调用多少次都是创建一个引擎，避免很多引擎小黑膏资源
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        """初始化数据库引擎"""
        self.engine = create_engine(
            DATABASE_URL,
            poolclass=StaticPool,#连接池里只保持一个全局数据库连接，测试稳定
            pool_pre_ping=True,
            echo=False  # 生产环境设为False
        )

    def execute(self, query: str, params: dict = None):
        """执行SQL"""
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            return result
    
    async def async_execute(self, query: str, params: dict = None):
        """异步执行SQL（在线程池中运行同步操作）"""
        import asyncio
        return await asyncio.to_thread(self.execute, query, params)

    def fetchall(self, query: str, params: dict = None):
        """查询多条"""
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]

    def fetchone(self, query: str, params: dict = None):
        """查询单条"""
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            row = result.fetchone()
            return dict(row._mapping) if row else None


# 全局实例
db = DatabaseManager()