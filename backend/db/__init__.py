"""
数据库模块初始化文件

导出核心类和函数供其他模块使用。

使用示例:
    from backend.db import get_session, init_session_factories, ETFInfo, ETFNavHistory
"""

from backend.db.database import (
    get_engine,
    get_session,
    init_session_factories,
    ensure_data_dir,
    close_all_sessions,
    SessionLocal,
)

from backend.db.models import (
    Base,
    ETFInfo,
    ETFNavHistory,
    create_database,
    drop_database,
)

__all__ = [
    # 数据库连接管理
    "get_engine",
    "get_session",
    "init_session_factories",
    "ensure_data_dir",
    "close_all_sessions",
    "SessionLocal",
    # ORM模型
    "Base",
    "ETFInfo",
    "ETFNavHistory",
    "create_database",
    "drop_database",
]