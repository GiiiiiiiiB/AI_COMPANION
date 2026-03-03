"""
数据库连接管理
"""
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from redis import asyncio as aioredis
from src.config.settings import settings

# 创建异步引擎
engine = create_async_engine(
    settings.database.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Redis连接
redis_client = None


async def init_redis():
    """初始化Redis连接"""
    global redis_client
    redis_client = aioredis.from_url(
        settings.database.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    return redis_client


async def close_redis():
    """关闭Redis连接"""
    global redis_client
    if redis_client:
        await redis_client.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis_client():
    """获取Redis客户端"""
    global redis_client
    if redis_client is None:
        await init_redis()
    return redis_client


async def init_database():
    """初始化数据库"""
    from src.storage.models import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 初始化Redis
    await init_redis()


async def close_database():
    """关闭数据库连接"""
    await engine.dispose()
    await close_redis()