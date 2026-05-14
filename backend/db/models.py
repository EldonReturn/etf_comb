"""
ETF数据库模型模块

本模块定义了ETF组合推荐系统所需的数据库表结构，使用SQLAlchemy ORM进行映射。

数据库表结构：
1. ETFInfo: ETF基本信息表（代码、名称、分类）
2. ETFNavHistory: ETF历史净值表（日期、单位净值、累计净值）

作者: ETF组合系统
版本: 1.1.0
"""

import logging
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    String, Date, DateTime, Numeric, Integer,
    ForeignKey, UniqueConstraint, Index, create_engine,
    PrimaryKeyConstraint
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column,
    relationship, Session
)

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """
    基础ORM基类

    所有数据库模型都需要继承此类，以获得SQLAlchemy ORM的基本功能。
    使用mapped_column()进行列映射，这是SQLAlchemy 2.0推荐的方式。
    """
    pass


class ETFInfo(Base):
    """
    ETF基本信息表

    存储ETF的基础信息，包括代码、名称、分类等。
    该表是主表，通过code字段与历史净值表关联。

    属性说明：
    - code: ETF代码，主键，如 '510300' 代表华泰柏瑞沪深300ETF
    - name: ETF简称，如 '沪深300ETF'
    - category: 分类，可选值包括：
        * '宽基指数' - 跟踪宽基指数的ETF，如沪深300、中证500
        * '行业指数' - 跟踪特定行业的ETF，如军工、医药
        * '债券' - 债券型ETF
        * '商品' - 商品型ETF，如黄金ETF
        * '境外' - 投资境外市场的ETF
    - updated_at: 最后一次从数据源更新该ETF信息的时间
    """
    __tablename__ = "etf_info"

    code: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
        comment="ETF代码，主键"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="ETF名称"
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="宽基指数",
        comment="ETF分类：宽基指数/行业指数/债券/商品/境外"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="最后更新时间"
    )

    nav_history: Mapped[List["ETFNavHistory"]] = relationship(
        "ETFNavHistory",
        back_populates="etf_info",
        cascade="all, delete-orphan",
        doc="该ETF的所有历史净值记录，一对多关系"
    )

    def __repr__(self) -> str:
        return f"<ETFInfo(code='{self.code}', name='{self.name}', category='{self.category}')>"


class ETFNavHistory(Base):
    """
    ETF历史净值表

    存储ETF每天的净值数据，用于计算收益率、波动率等指标。
    通过(etf_code, nav_date)唯一索引确保同一天只有一条记录。

    属性说明：
    - etf_code: ETF代码，外键关联到etf_info表的code字段
    - nav_date: 净值日期
    - nav: 单位净值（也称为单位份额净值），反映每份基金的价值
    - accum_nav: 累计净值，考虑了分红再投资的净值增长
    - created_at: 记录创建时间

    注意：
    - nav和accum_nav的关系：accum_nav >= nav（考虑分红）
    - 计算收益率时通常使用nav的日变化率
    """
    __tablename__ = "etf_nav_history"

    etf_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("etf_info.code", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ETF代码，外键"
    )
    nav_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="净值日期"
    )
    nav: Mapped[float] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="单位净值"
    )
    accum_nav: Mapped[float] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="累计净值"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="记录创建时间"
    )

    etf_info: Mapped["ETFInfo"] = relationship(
        "ETFInfo",
        back_populates="nav_history",
        doc="关联的ETF基本信息"
    )

    __table_args__ = (
        PrimaryKeyConstraint(
            'etf_code', 'nav_date',
            name='pk_etf_nav_history'
        ),
        Index(
            'ix_etf_code_nav_date',
            'etf_code', 'nav_date'
        ),
    )

    def __repr__(self) -> str:
        return f"<ETFNavHistory(etf_code='{self.etf_code}', nav_date={self.nav_date}, nav={self.nav})>"


def create_database(db_path: str = "data/etf_database.db") -> None:
    """
    创建数据库和所有表

    如果数据库文件已存在，则保持现有数据不变，不会重新创建表。
    只有在数据库不存在时，才会创建新的数据库和表结构。

    参数:
        db_path: 数据库文件路径，默认为 'data/etf_database.db'

    返回:
        Engine: SQLAlchemy数据库引擎实例，如果数据库已存在则返回None

    示例:
        >>> engine = create_database()
        >>> if engine:
        >>>     print("新数据库已创建")
        >>> else:
        >>>     print("使用现有数据库")
    """
    import os

    if os.path.exists(db_path):
        logger.info(f"数据库文件已存在，保持现有数据不变: {db_path}")
        return None

    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)

    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    logger.info(f"新数据库已创建: {db_path}")
    return engine


def drop_database(db_path: str = "data/etf_database.db") -> None:
    """
    删除数据库和所有表（仅用于测试）

    警告：此函数会删除整个数据库文件，请谨慎使用！

    参数:
        db_path: 数据库文件路径
    """
    import os
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"数据库已删除: {db_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    create_database()
    print("数据库创建成功！")