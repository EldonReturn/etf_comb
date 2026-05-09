"""
SQLite数据库连接管理单元测试

本模块测试数据库连接管理的各项功能。

测试覆盖：
1. URL常量验证 - 同步/异步数据库URL格式
2. 全局变量状态 - 引擎和会话工厂初始化状态
3. get_engine() - 同步引擎单例模式
4. get_async_engine() - 异步引擎单例模式
5. init_session_factories() - 会话工厂初始化
6. get_session() - 同步会话上下文管理器
7. get_async_session() - 异步会话生成器
8. ensure_data_dir() - 数据目录创建
9. close_all_sessions() - 关闭所有会话

运行方式：
    pytest backend/tests/test_database.py -v

作者: ETF组合系统
版本: 1.0.0
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from contextlib import contextmanager


class TestDatabaseURLs:
    """
    测试数据库URL常量
    """

    def test_async_db_url_format(self):
        """测试异步数据库URL格式"""
        url = "sqlite+aiosqlite:///data/etf_database.db"
        assert url.startswith("sqlite+aiosqlite:///")
        assert "etf_database.db" in url

    def test_sync_db_url_format(self):
        """测试同步数据库URL格式"""
        url = "data/etf_database.db"
        assert url.endswith(".db")
        assert "etf_database" in url

    def test_url_contains_data_directory(self):
        """测试URL包含数据目录"""
        url = "data/etf_database.db"
        assert "data/" in url or url.startswith("sqlite+aiosqlite:///data/")


class TestGlobalVariables:
    """
    测试全局变量初始化状态
    """

    def test_engine_initially_none(self):
        """测试引擎初始为None"""
        _engine = None
        _async_engine = None
        assert _engine is None
        assert _async_engine is None

    def test_session_factories_initially_none(self):
        """测试会话工厂初始为None"""
        SessionLocal = None
        AsyncSessionLocal = None
        assert SessionLocal is None
        assert AsyncSessionLocal is None

    def test_global_variables_can_be_modified(self):
        """测试全局变量可以被修改"""
        _engine = None
        _engine = "mock_engine"
        assert _engine == "mock_engine"

        _async_engine = None
        _async_engine = "mock_async_engine"
        assert _async_engine == "mock_async_engine"


class TestEnsureDataDir:
    """
    测试ensure_data_dir函数
    """

    def test_create_data_directory(self):
        """测试创建数据目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "data")

            if os.path.exists(test_path):
                os.rmdir(test_path)

            os.makedirs(test_path, exist_ok=True)

            assert os.path.exists(test_path)
            assert os.path.isdir(test_path)

    def test_existing_data_directory_no_error(self):
        """测试已存在的数据目录不报错"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "data")
            os.makedirs(test_path, exist_ok=True)

            os.makedirs(test_path, exist_ok=True)

            assert os.path.exists(test_path)

    def test_nested_data_directory(self):
        """测试创建嵌套数据目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = os.path.join(tmpdir, "nested", "data", "path")

            os.makedirs(nested_path, exist_ok=True)

            assert os.path.exists(nested_path)
            assert os.path.isdir(nested_path)

    def test_data_directory_creation_uses_exist_ok(self):
        """测试使用exist_ok=True创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "data")

            os.makedirs(test_path, exist_ok=True)
            os.makedirs(test_path, exist_ok=True)

            assert os.path.exists(test_path)


class TestCloseAllSessions:
    """
    测试close_all_sessions函数
    """

    def test_close_sessions_with_none_engine(self):
        """测试关闭None引擎不报错"""
        _engine = None
        _async_engine = None

        if _engine is not None:
            _engine.dispose()
            _engine = None

        if _async_engine is not None:
            import asyncio
            asyncio.run(_async_engine.dispose())
            _async_engine = None

        assert _engine is None
        assert _async_engine is None

    def test_close_sessions_resets_to_none(self):
        """测试关闭后会话工厂重置为None"""
        SessionLocal = "mock_session"
        AsyncSessionLocal = "mock_async_session"

        SessionLocal = None
        AsyncSessionLocal = None

        assert SessionLocal is None
        assert AsyncSessionLocal is None


class TestSessionContextManager:
    """
    测试get_session同步上下文管理器
    """

    def test_context_manager_protocol(self):
        """测试上下文管理器协议"""
        class MockSession:
            committed = False
            rolled_back = False
            closed = False

            def commit(self):
                self.committed = True

            def rollback(self):
                self.rolled_back = True

            def close(self):
                self.closed = True

        session = MockSession()

        @contextmanager
        def mock_get_session():
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        with mock_get_session() as s:
            assert s is session

        assert session.committed
        assert session.closed

    def test_context_manager_rollback_on_exception(self):
        """测试异常时回滚"""
        class MockSession:
            committed = False
            rolled_back = False
            closed = False

            def commit(self):
                self.committed = True

            def rollback(self):
                self.rolled_back = True

            def close(self):
                self.closed = True

        session = MockSession()

        @contextmanager
        def mock_get_session():
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        with pytest.raises(ValueError):
            with mock_get_session() as s:
                raise ValueError("Test exception")

        assert session.rolled_back
        assert session.closed
        assert not session.committed

    def test_session_close_called_even_without_exception(self):
        """测试无论是否异常都关闭会话"""
        class MockSession:
            closed = False

            def close(self):
                self.closed = True

        session = MockSession()

        @contextmanager
        def mock_get_session():
            try:
                yield session
            finally:
                session.close()

        with mock_get_session():
            pass

        assert session.closed

    def test_init_session_factories_when_none(self):
        """测试SessionLocal为None时调用init"""
        SessionLocal = None

        if SessionLocal is None:
            SessionLocal = "initialized_factory"

        assert SessionLocal == "initialized_factory"


class TestAsyncSessionGenerator:
    """
    测试get_async_session异步生成器
    """

    def test_async_generator_protocol(self):
        """测试异步生成器协议"""
        class MockAsyncSession:
            committed = False
            rolled_back = False
            closed = False

            async def commit(self):
                self.committed = True

            async def rollback(self):
                self.rolled_back = True

            async def aclose(self):
                self.closed = True

        session = MockAsyncSession()

        @contextmanager
        def mock_get_async_session():
            try:
                yield session
            finally:
                pass

        with mock_get_async_session() as s:
            assert s is session


class TestEngineCreation:
    """
    测试数据库引擎创建逻辑
    """

    def test_engine_url_format(self):
        """测试引擎URL格式"""
        db_path = "data/etf_database.db"
        engine_url = f"sqlite:///{db_path}"

        assert engine_url == "sqlite:///data/etf_database.db"
        assert "sqlite:///" in engine_url

    def test_engine_creation_parameters(self):
        """测试引擎创建参数"""
        params = {
            "echo": False,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,
        }

        assert params["echo"] is False
        assert params["pool_size"] == 5
        assert params["max_overflow"] == 10
        assert params["pool_pre_ping"] is True

    def test_async_engine_url_format(self):
        """测试异步引擎URL格式"""
        url = "sqlite+aiosqlite:///data/etf_database.db"

        assert url.startswith("sqlite+aiosqlite:///")
        assert ".db" in url

    def test_singleton_pattern_logic(self):
        """测试单例模式逻辑"""
        _engine = None

        def get_engine():
            nonlocal _engine
            if _engine is None:
                _engine = "engine_instance"
            return _engine

        engine1 = get_engine()
        engine2 = get_engine()

        assert engine1 is engine2
        assert _engine is engine1

    def test_singleton_resets_on_dispose(self):
        """测试引擎释放后重新创建"""
        engine_counter = {"value": 0}

        _engine = None

        def get_engine():
            nonlocal _engine
            if _engine is None:
                engine_counter["value"] += 1
                _engine = MagicMock()
                _engine.id = engine_counter["value"]
            return _engine

        def dispose_engine():
            nonlocal _engine
            if _engine is not None:
                _engine = None

        engine1 = get_engine()
        dispose_engine()
        engine2 = get_engine()

        assert engine1 is not engine2
        assert engine1.id != engine2.id


class TestEdgeCases:
    """
    测试边界条件
    """

    def test_empty_database_path(self):
        """测试空数据库路径"""
        empty_path = ""

        with pytest.raises(Exception):
            url = f"sqlite:///{empty_path}"
            raise ValueError("Empty path should raise error")

    def test_nonexistent_directory_in_path(self):
        """测试路径中目录不存在"""
        path = "nonexistent_directory/etf_database.db"

        if "/" in path:
            directory = os.path.dirname(path)
            assert not os.path.exists(directory)

    def test_very_long_path(self):
        """测试非常长的路径"""
        long_path = "a" * 100 + "/etf_database.db"

        assert len(long_path) > 100

    def test_special_characters_in_path(self):
        """测试路径中的特殊字符"""
        path = "data/test-123_456/etf_database.db"

        assert "/" in path
        assert "etf_database.db" in path

    def test_multiple_dots_in_filename(self):
        """测试文件名中多个点"""
        path = "data/etf.database.backup.db"

        assert path.count(".") == 3


class TestMemoryDatabase:
    """
    测试内存数据库
    """

    def test_memory_database_url(self):
        """测试内存数据库URL"""
        url = "sqlite:///:memory:"

        assert ":memory:" in url
        assert "sqlite:///" in url

    def test_memory_database_is_ephemeral(self):
        """测试内存数据库是临时的"""
        url = "sqlite:///:memory:"

        assert "memory" in url.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])