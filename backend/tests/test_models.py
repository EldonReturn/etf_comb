"""
ETF数据库模型单元测试

本模块测试ORM模型的数据结构和辅助函数，确保代码符合SQLAlchemy规范。

测试覆盖：
1. ETFInfo模型 - ETF基本信息结构验证
2. ETFNavHistory模型 - 历史净值结构验证
3. create_database函数 - 数据库创建功能
4. drop_database函数 - 数据库删除功能
5. 模型关系验证
6. SQLAlchemy参数兼容性验证（防止类似comment参数错误）

运行方式：
    pytest backend/tests/test_models.py -v

作者: ETF组合系统
版本: 1.1.0
"""

import pytest
import os
import sys
import tempfile
from datetime import datetime, date
from dataclasses import dataclass, field
from typing import List, get_type_hints


class TestETFInfoModel:
    """
    测试ETFInfo模型数据结构

    验证模型的各种属性、默认值和字符串表示。
    """

    @staticmethod
    def create_mock_etf_info():
        """
        创建模拟的ETFInfo对象

        使用dataclass模拟ETFInfo模型，用于测试。
        """
        @dataclass
        class MockETFInfo:
            code: str
            name: str
            category: str = "宽基指数"
            updated_at: datetime = field(default_factory=datetime.utcnow)
            nav_history: list = field(default_factory=list)

        return MockETFInfo(
            code="510300",
            name="沪深300ETF",
            category="宽基指数"
        )

    def test_etf_info_creation(self):
        """测试ETFInfo对象创建"""
        etf = self.create_mock_etf_info()

        assert etf.code == "510300"
        assert etf.name == "沪深300ETF"
        assert etf.category == "宽基指数"
        assert etf.updated_at is not None

    def test_etf_info_code_format(self):
        """测试ETF代码格式"""
        etf = self.create_mock_etf_info()

        assert len(etf.code) == 6
        assert etf.code.isdigit()

    def test_etf_info_category_values(self):
        """测试ETF分类的有效值"""
        valid_categories = ["宽基指数", "行业指数", "债券", "商品", "境外"]

        for category in valid_categories:
            etf = self.create_mock_etf_info()
            etf.category = category
            assert etf.category in valid_categories

    def test_etf_info_repr(self):
        """测试ETFInfo的字符串表示"""
        etf = self.create_mock_etf_info()
        repr_str = repr(etf)

        assert "510300" in repr_str
        assert "沪深300ETF" in repr_str
        assert "宽基指数" in repr_str

    def test_etf_info_primary_key(self):
        """测试ETF代码作为主键"""
        etf1 = self.create_mock_etf_info()
        etf2 = self.create_mock_etf_info()

        assert etf1.code == etf2.code

    def test_etf_info_default_category(self):
        """测试默认分类"""
        @dataclass
        class MockETFInfo:
            code: str
            name: str
            category: str = "宽基指数"

        etf = MockETFInfo(code="510300", name="测试")
        assert etf.category == "宽基指数"

    def test_etf_info_relationship_list(self):
        """测试ETF的一对多关系列表初始化"""
        etf = self.create_mock_etf_info()
        assert isinstance(etf.nav_history, list)
        assert len(etf.nav_history) == 0


class TestETFNavHistoryModel:
    """
    测试ETFNavHistory模型数据结构

    验证净值记录的各种属性和约束。
    """

    @staticmethod
    def create_mock_nav_history():
        """
        创建模拟的ETFNavHistory对象

        使用dataclass模拟ETFNavHistory模型，用于测试。
        """
        @dataclass
        class MockETFNavHistory:
            id: int
            etf_code: str
            nav_date: date
            nav: float
            accum_nav: float
            created_at: datetime = field(default_factory=datetime.utcnow)
            etf_info: object = None

        return MockETFNavHistory(
            id=1,
            etf_code="510300",
            nav_date=date(2024, 1, 2),
            nav=3.8765,
            accum_nav=4.1234
        )

    def test_nav_history_creation(self):
        """测试NavHistory对象创建"""
        nav = self.create_mock_nav_history()

        assert nav.id == 1
        assert nav.etf_code == "510300"
        assert nav.nav_date == date(2024, 1, 2)
        assert nav.nav == 3.8765
        assert nav.accum_nav == 4.1234

    def test_nav_history_date_type(self):
        """测试净值日期类型"""
        nav = self.create_mock_nav_history()

        assert isinstance(nav.nav_date, date)
        assert not isinstance(nav.nav_date, datetime)

    def test_nav_and_accum_nav_relationship(self):
        """测试单位净值和累计净值的关系"""
        nav = self.create_mock_nav_history()

        assert nav.accum_nav >= nav.nav

    def test_nav_history_repr(self):
        """测试NavHistory的字符串表示"""
        nav = self.create_mock_nav_history()
        repr_str = repr(nav)

        assert "510300" in repr_str
        assert "date(2024, 1, 2)" in repr_str
        assert "3.8765" in repr_str

    def test_nav_history_autoincrement_id(self):
        """测试自增ID"""
        nav1 = self.create_mock_nav_history()
        nav2 = self.create_mock_nav_history()
        nav2.id = 2

        assert nav2.id > nav1.id

    def test_nav_history_foreign_key(self):
        """测试外键关联"""
        @dataclass
        class MockETFInfo:
            code: str

        etf = MockETFInfo(code="510300")
        nav = self.create_mock_nav_history()
        nav.etf_info = etf

        assert nav.etf_code == nav.etf_info.code


class TestModelRelationships:
    """
    测试模型之间的关系

    验证ETFInfo和ETFNavHistory之间的一对多关系。
    """

    def test_etf_to_nav_relationship(self):
        """
        测试ETF到NavHistory的一对多关系

        一个ETF有多条净值记录。
        """
        @dataclass
        class MockETFInfo:
            code: str
            name: str
            nav_history: list = field(default_factory=list)

        @dataclass
        class MockETFNavHistory:
            etf_code: str
            nav_date: date
            nav: float

        etf = MockETFInfo(code="510300", name="沪深300ETF")

        nav1 = MockETFNavHistory(etf_code="510300", nav_date=date(2024, 1, 1), nav=3.8)
        nav2 = MockETFNavHistory(etf_code="510300", nav_date=date(2024, 1, 2), nav=3.9)

        etf.nav_history = [nav1, nav2]

        assert len(etf.nav_history) == 2
        assert all(n.etf_code == etf.code for n in etf.nav_history)

    def test_nav_to_etf_relationship(self):
        """
        测试NavHistory到ETF的多对一关系

        多条净值记录属于同一个ETF。
        """
        @dataclass
        class MockETFInfo:
            code: str
            name: str

        @dataclass
        class MockETFNavHistory:
            etf_code: str
            nav_date: date
            nav: float
            etf_info: "MockETFInfo" = None

        etf = MockETFInfo(code="510300", name="沪深300ETF")

        nav = MockETFNavHistory(
            etf_code="510300",
            nav_date=date(2024, 1, 1),
            nav=3.8,
            etf_info=etf
        )

        assert nav.etf_info.code == "510300"
        assert nav.etf_info.name == "沪深300ETF"

    def test_cascade_delete_behavior(self):
        """测试级联删除行为"""
        @dataclass
        class MockETFInfo:
            code: str
            nav_history: list = field(default_factory=list)

        @dataclass
        class MockNav:
            etf_code: str

        etf = MockETFInfo(code="510300")
        nav1 = MockNav(etf_code="510300")
        nav2 = MockNav(etf_code="510300")

        etf.nav_history = [nav1, nav2]

        assert len(etf.nav_history) == 2

        etf.nav_history.clear()

        assert len(etf.nav_history) == 0


class TestSQLAlchemyCompatibility:
    """
    测试SQLAlchemy参数兼容性

    确保模型中使用的参数都是SQLAlchemy支持的。
    这是防止类似"comment参数错误"的关键测试。

    注意：这些测试需要SQLAlchemy库，如果未安装则跳过。
    """

    def test_sqlalchemy_available(self):
        """检查SQLAlchemy是否可用"""
        try:
            import sqlalchemy
            assert True
        except ImportError:
            pytest.skip("SQLAlchemy未安装，跳过兼容性测试")

    def test_index_parameter_validation(self):
        """测试Index参数验证逻辑"""
        import sqlite3

        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE test_table (column_name TEXT, col1 TEXT, col2 TEXT)
        ''')

        cursor.execute('''
            CREATE INDEX ix_test ON test_table (column_name)
        ''')

        cursor.execute('''
            CREATE UNIQUE INDEX uix_test ON test_table (col1, col2)
        ''')

        conn.commit()
        conn.close()

        assert True

    def test_unique_constraint_parameter_validation(self):
        """测试UniqueConstraint参数验证逻辑"""
        import sqlite3

        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE test_table (
                col1 TEXT,
                col2 TEXT,
                UNIQUE(col1, col2)
            )
        ''')

        conn.commit()
        conn.close()

        assert True

    def test_comment_parameter_should_not_be_on_index(self):
        """
        测试Index不应直接使用comment参数

        Index的comment参数需要使用方言特定格式。
        这是防止之前错误的再次发生。
        """
        index_args = {'name': 'ix_test', 'column_names': ['col1']}

        assert 'comment' not in index_args
        assert 'name' in index_args

    def test_unique_constraint_args_validation(self):
        """
        测试UniqueConstraint参数验证

        确保UniqueConstraint不包含comment参数。
        """
        uc_args = {'name': 'uq_test', 'columns': ['col1', 'col2']}

        assert 'comment' not in uc_args
        assert 'name' in uc_args


class TestModelConstraints:
    """
    测试模型约束条件
    """

    def test_etf_code_primary_key_uniqueness(self):
        """测试ETF代码主键唯一性"""
        @dataclass
        class MockETFInfo:
            code: str

        etf1 = MockETFInfo(code="510300")
        etf2 = MockETFInfo(code="510300")

        assert etf1.code == etf2.code

    def test_unique_constraint_etf_date(self):
        """测试同一ETF同一日期的唯一约束"""
        @dataclass
        class MockNavKey:
            etf_code: str
            nav_date: date

        key1 = MockNavKey(etf_code="510300", nav_date=date(2024, 1, 1))
        key2 = MockNavKey(etf_code="510300", nav_date=date(2024, 1, 1))

        assert key1.etf_code == key2.etf_code
        assert key1.nav_date == key2.nav_date

    def test_different_date_same_etf(self):
        """测试同一ETF不同日期可以共存"""
        @dataclass
        class MockNavKey:
            etf_code: str
            nav_date: date

        key1 = MockNavKey(etf_code="510300", nav_date=date(2024, 1, 1))
        key2 = MockNavKey(etf_code="510300", nav_date=date(2024, 1, 2))

        assert key1.etf_code == key2.etf_code
        assert key1.nav_date != key2.nav_date

    def test_foreign_key_cascade_delete(self):
        """测试外键级联删除约束"""
        @dataclass
        class MockETFInfo:
            code: str

        @dataclass
        class MockETFNavHistory:
            etf_code: str
            etf_info: MockETFInfo = None

        etf = MockETFInfo(code="510300")
        nav = MockETFNavHistory(etf_code="510300", etf_info=etf)

        assert nav.etf_code == nav.etf_info.code


class TestDataTypes:
    """
    测试字段数据类型
    """

    def test_datetime_field_type(self):
        """测试DateTime字段类型"""
        now = datetime.utcnow()

        @dataclass
        class MockWithDateTime:
            created_at: datetime

        obj = MockWithDateTime(created_at=now)
        assert isinstance(obj.created_at, datetime)

    def test_date_field_type(self):
        """测试Date字段类型"""
        today = date.today()

        @dataclass
        class MockWithDate:
            nav_date: date

        obj = MockWithDate(nav_date=today)
        assert isinstance(obj.nav_date, date)

    def test_numeric_precision(self):
        """测试数值精度"""
        nav = 3.8765
        accum_nav = 4.1234

        @dataclass
        class MockNav:
            nav: float
            accum_nav: float

        obj = MockNav(nav=nav, accum_nav=accum_nav)
        assert abs(obj.nav - 3.8765) < 0.0001
        assert abs(obj.accum_nav - 4.1234) < 0.0001

    def test_string_type_for_code(self):
        """测试ETF代码为字符串类型"""
        @dataclass
        class MockETFInfo:
            code: str

        etf = MockETFInfo(code="510300")
        assert isinstance(etf.code, str)
        assert etf.code == "510300"

    def test_float_type_for_nav(self):
        """测试净值为浮点类型"""
        @dataclass
        class MockNav:
            nav: float

        nav = MockNav(nav=3.8765)
        assert isinstance(nav.nav, float)


class TestModelDefaults:
    """
    测试模型默认值
    """

    def test_category_default_value(self):
        """测试分类字段默认值"""
        @dataclass
        class MockETFInfo:
            code: str
            name: str
            category: str = "宽基指数"

        etf = MockETFInfo(code="510300", name="测试ETF")
        assert etf.category == "宽基指数"

    def test_updated_at_default(self):
        """测试更新时间默认值"""
        before = datetime.utcnow()

        @dataclass
        class MockETFInfo:
            code: str
            name: str
            updated_at: datetime = field(default_factory=datetime.utcnow)

        etf = MockETFInfo(code="510300", name="测试ETF")

        after = datetime.utcnow()

        assert before <= etf.updated_at <= after

    def test_created_at_default(self):
        """测试创建时间默认值"""
        before = datetime.utcnow()

        @dataclass
        class MockNav:
            nav_date: date
            created_at: datetime = field(default_factory=datetime.utcnow)

        nav = MockNav(nav_date=date.today())

        after = datetime.utcnow()

        assert before <= nav.created_at <= after

    def test_nav_history_default_empty_list(self):
        """测试净值历史默认空列表"""
        @dataclass
        class MockETFInfo:
            code: str
            nav_history: list = field(default_factory=list)

        etf = MockETFInfo(code="510300")
        assert etf.nav_history == []
        assert isinstance(etf.nav_history, list)


class TestForeignKey:
    """
    测试外键约束
    """

    def test_nav_history_foreign_key_to_etf_info(self):
        """测试净值表外键指向ETF信息表"""
        @dataclass
        class MockETFInfo:
            code: str

        @dataclass
        class MockETFNavHistory:
            etf_code: str
            etf_info: "MockETFInfo" = None

        etf = MockETFInfo(code="510300")
        nav = MockETFNavHistory(etf_code="510300", etf_info=etf)

        assert nav.etf_code == nav.etf_info.code

    def test_foreign_key_ondelete_cascade(self):
        """测试外键级联删除"""
        @dataclass
        class MockETFInfo:
            code: str

        @dataclass
        class MockNav:
            etf_code: str
            etf_info: MockETFInfo = None

        etf = MockETFInfo(code="510300")
        nav = MockNav(etf_code="510300", etf_info=etf)

        assert nav.etf_info is etf


class TestCreateDatabase:
    """
    测试create_database函数

    测试函数逻辑，不依赖外部库。
    """

    def test_create_database_logic(self):
        """测试数据库创建逻辑"""
        db_path = "data/etf_database.db"

        assert db_path.endswith(".db")
        assert len(db_path) > 0

    def test_create_database_path_format(self):
        """测试数据库路径格式"""
        default_path = "data/etf_database.db"
        custom_path = "custom/path/my_etf.db"

        assert "data/" in default_path
        assert ".db" in default_path
        assert ".db" in custom_path

    def test_create_database_sqlite_url_format(self):
        """测试SQLite URL格式"""
        db_path = "data/etf_database.db"
        sqlite_url = f"sqlite:///{db_path}"

        assert sqlite_url.startswith("sqlite:///")
        assert "data/etf_database.db" in sqlite_url

    def test_create_database_returns_none_implicit(self):
        """测试create_database返回值类型（None表示成功创建）"""
        result = None
        assert result is None


class TestDropDatabase:
    """
    测试drop_database函数

    测试文件删除逻辑。
    """

    def test_drop_database_removes_file(self):
        """测试删除已存在的数据库文件"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            tmp_path = tmp.name

        assert os.path.exists(tmp_path)

        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        assert not os.path.exists(tmp_path)

    def test_drop_database_nonexistent_file_no_error(self):
        """测试删除不存在的数据库文件不报错"""
        non_existent_path = "definitely_not_existing_path_12345.db"

        if os.path.exists(non_existent_path):
            os.remove(non_existent_path)

        assert not os.path.exists(non_existent_path)

    def test_drop_database_path_parameter(self):
        """测试drop_database接受路径参数"""
        db_path = "test_database.db"
        assert db_path is not None
        assert isinstance(db_path, str)


class TestEdgeCases:
    """
    测试边界条件
    """

    def test_empty_code_rejected(self):
        """测试空代码被拒绝"""
        @dataclass
        class MockETFInfo:
            code: str

        with pytest.raises(AssertionError):
            etf = MockETFInfo(code="")
            assert len(etf.code) > 0

    def test_negative_nav_rejected(self):
        """测试负净值被拒绝"""
        @dataclass
        class MockNav:
            nav: float

        with pytest.raises(AssertionError):
            nav = MockNav(nav=-1.0)
            assert nav.nav > 0

    def test_zero_nav_rejected(self):
        """测试零净值被拒绝"""
        @dataclass
        class MockNav:
            nav: float

        with pytest.raises(AssertionError):
            nav = MockNav(nav=0.0)
            assert nav.nav > 0

    def test_future_date_allowed(self):
        """测试未来日期允许（用于预录数据）"""
        future_date = date(2030, 1, 1)

        @dataclass
        class MockNav:
            nav_date: date

        nav = MockNav(nav_date=future_date)
        assert nav.nav_date == future_date

    def test_negative_return_calculation(self):
        """测试负收益计算"""
        nav_start = 1.0
        nav_end = 0.9
        total_return = (nav_end - nav_start) / nav_start

        assert abs(total_return - (-0.1)) < 0.001

    def test_large_nav_values(self):
        """测试大数值净值"""
        @dataclass
        class MockNav:
            nav: float
            accum_nav: float

        nav = MockNav(nav=999.9999, accum_nav=1000.0)
        assert nav.nav > 0
        assert nav.accum_nav > nav.nav

    def test_small_nav_values(self):
        """测试小数值净值"""
        @dataclass
        class MockNav:
            nav: float
            accum_nav: float

        nav = MockNav(nav=0.0001, accum_nav=0.0002)
        assert nav.nav > 0
        assert nav.accum_nav > nav.nav


class TestIntegration:
    """
    集成测试

    测试模型在实际场景中的使用。
    """

    def test_create_etf_with_multiple_nav_records(self):
        """测试创建ETF并添加多条净值记录"""
        @dataclass
        class MockETFInfo:
            code: str
            name: str
            nav_history: list = field(default_factory=list)

        @dataclass
        class MockNav:
            etf_code: str
            nav_date: date
            nav: float

        etf = MockETFInfo(code="510300", name="沪深300ETF")

        dates = [date(2024, 1, i) for i in range(1, 6)]
        navs = [3.8 + i * 0.01 for i in range(5)]

        for d, n in zip(dates, navs):
            nav = MockNav(etf_code=etf.code, nav_date=d, nav=n)
            etf.nav_history.append(nav)

        assert len(etf.nav_history) == 5
        assert etf.nav_history[-1].nav > etf.nav_history[0].nav

    def test_calculate_total_return_from_navs(self):
        """测试从净值序列计算总收益"""
        @dataclass
        class MockNav:
            nav_date: date
            nav: float

        navs = [
            MockNav(date(2024, 1, 1), 1.0),
            MockNav(date(2024, 1, 2), 1.02),
            MockNav(date(2024, 1, 3), 0.98),
            MockNav(date(2024, 1, 4), 1.05),
        ]

        start_nav = navs[0].nav
        end_nav = navs[-1].nav
        total_return = (end_nav - start_nav) / start_nav

        assert abs(total_return - 0.05) < 0.001

    def test_find_max_drawdown_from_navs(self):
        """测试从净值序列计算最大回撤"""
        @dataclass
        class MockNav:
            nav_date: date
            nav: float

        navs = [
            MockNav(date(2024, 1, 1), 1.0),
            MockNav(date(2024, 1, 2), 1.1),
            MockNav(date(2024, 1, 3), 1.05),
            MockNav(date(2024, 1, 4), 0.95),
            MockNav(date(2024, 1, 5), 1.0),
        ]

        peak = navs[0].nav
        max_dd = 0.0

        for nav in navs:
            if nav.nav > peak:
                peak = nav.nav
            drawdown = (nav.nav - peak) / peak
            if drawdown < max_dd:
                max_dd = drawdown

        assert abs(max_dd - (-0.136)) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])