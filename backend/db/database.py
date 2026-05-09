"""
SQLite数据库连接管理模块

本模块提供数据库会话管理功能，支持同步和异步两种访问方式。
使用会话工厂模式确保数据库操作的正确性和效率。

核心功能：
1. get_engine(): 创建并返回数据库引擎（单例模式）
2. get_session(): 创建新的数据库会话
3. AsyncSessionLocal: 异步会话工厂（用于FastAPI异步路由）

使用示例:
    # 同步方式
    with get_session() as session:
        etfs = session.query(ETFInfo).all()

    # 异步方式（推荐用于FastAPI）
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ETFInfo))

作者: ETF组合系统
版本: 1.0.0
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session, session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# 异步引擎URL（aiosqlite驱动）
ASYNC_DB_URL = "sqlite+aiosqlite:///data/etf_database.db"
# 同步引擎URL
SYNC_DB_URL = "data/etf_database.db"

# 全局引擎实例（延迟初始化）
_engine: Engine = None
_async_engine = None

# 会话工厂
SessionLocal = None
AsyncSessionLocal = None


def get_engine() -> Engine:
    """
    获取同步数据库引擎（单例模式）

    首次调用时创建引擎，后续调用直接返回已创建的引擎实例。
    这确保了整个应用使用同一个数据库连接池。

    返回:
        Engine: SQLAlchemy数据库引擎实例

    注意:
        同步引擎用于后台任务、定时任务等场景
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            f"sqlite:///{SYNC_DB_URL}",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False}
        )
    return _engine


def get_async_engine():
    """
    获取异步数据库引擎（单例模式）

    首次调用时创建异步引擎，后续调用直接返回已创建的引擎实例。
    异步引擎用于FastAPI的异步路由处理。

    返回:
        AsyncEngine: SQLAlchemy异步数据库引擎实例
    """
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            ASYNC_DB_URL,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _async_engine


def init_session_factories():
    """
    初始化会话工厂

    在应用启动时调用此函数，初始化同步和异步会话工厂。
    会话工厂用于创建数据库会话实例。

    示例:
        >>> init_session_factories()
        >>> session = SessionLocal()
    """
    global SessionLocal, AsyncSessionLocal

    engine = get_engine()
    async_engine = get_async_engine()

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False
    )

    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    获取数据库会话的上下文管理器（同步方式）

    使用with语句自动管理会话的创建和销毁，
    确保操作完成后正确关闭会话。

    使用示例:
        >>> with get_session() as session:
        >>>     etfs = session.query(ETFInfo).all()
        >>>     for etf in etfs:
        >>>         print(etf.name)

    参数:
        无

    生成器:
        Session: SQLAlchemy会话实例
    """
    if SessionLocal is None:
        init_session_factories()

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_async_session() -> AsyncSession:
    """
    获取异步数据库会话（用于FastAPI依赖注入）

    这是一个异步生成器函数，用于FastAPI的Depends()依赖注入。
    调用者需要使用 async with 语句来管理会话生命周期。

    使用示例:
        @app.get("/etfs")
        async def get_etfs(session: AsyncSession = Depends(get_async_session)):
            result = await session.execute(select(ETFInfo))
            return result.scalars().all()

    参数:
        无

    返回:
        AsyncSession: SQLAlchemy异步会话实例
    """
    if AsyncSessionLocal is None:
        init_session_factories()

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def ensure_data_dir():
    """
    确保数据目录存在

    检查data目录是否存在，如果不存在则创建。
    数据库文件需要存储在data目录下。
    """
    os.makedirs("data", exist_ok=True)


def close_all_sessions():
    """
    关闭所有数据库会话和连接池

    在应用关闭时调用，确保所有数据库连接被正确释放。
    避免连接泄漏和资源浪费。
    """
    global _engine, _async_engine

    if _engine is not None:
        _engine.dispose()
        _engine = None

    if _async_engine is not None:
        import asyncio
        asyncio.run(_async_engine.dispose())
        _async_engine = None


if __name__ == "__main__":
    ensure_data_dir()
    init_session_factories()
    print("数据库连接管理模块初始化完成！")