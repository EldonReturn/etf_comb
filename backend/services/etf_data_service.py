"""
ETF数据服务模块

本模块负责从AkShare获取ETF数据并存储到数据库。

核心功能：
1. fetch_etf_list(): 获取全量ETF列表
2. fetch_etf_history(): 获取单只ETF历史行情
3. sync_all_etf_data(): 批量同步所有ETF数据
4. get_etf_history_from_db(): 从数据库读取历史行情

数据来源：
- ETF列表: akshare的fund_etf_spot_em() 获取东方财富ETF列表
- 历史行情: akshare的fund_etf_hist_em() 获取ETF历史K线数据

数据字段说明：
- fund_etf_hist_em 返回的是市场交易价格，不是基金净值
- 但对于投资组合的收益率计算，交易价格和净值效果相同
- 收益率计算使用收盘价的日变化率

AkShare接口文档：https://akshare.akfamily.xyz/data/fund/fund_public.html

作者: ETF组合系统
版本: 1.1.0
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple

import pandas as pd
import akshare as ak
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from backend.db.models import ETFInfo, ETFNavHistory
from backend.db.database import get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


ETF_CATEGORY_MAP = {
    "沪深": "宽基指数",
    "上证": "宽基指数",
    "深证": "宽基指数",
    "中证": "宽基指数",
    "创业板": "宽基指数",
    "科创": "宽基指数",
    "MSCI": "宽基指数",
    "纳斯达克": "境外",
    "标普": "境外",
    "日经": "境外",
    "恒生": "境外",
    "德国": "境外",
    "黄金": "商品",
    "白银": "商品",
    "原油": "商品",
    "豆粕": "商品",
    "军工": "行业指数",
    "医药": "行业指数",
    "医疗": "行业指数",
    "科技": "行业指数",
    "半导体": "行业指数",
    "新能源": "行业指数",
    "光伏": "行业指数",
    "银行": "行业指数",
    "证券": "行业指数",
    "保险": "行业指数",
    "房地产": "行业指数",
    "消费": "行业指数",
    "白酒": "行业指数",
    "食品": "行业指数",
    "家电": "行业指数",
    "汽车": "行业指数",
    "环保": "行业指数",
    "5G": "行业指数",
    "人工智能": "行业指数",
    "债券": "债券",
    "国债": "债券",
    "信用债": "债券",
}


def determine_category(etf_name: str) -> str:
    """
    根据ETF名称推断分类

    通过匹配ETF名称中的关键词来确定其分类。
    如果没有匹配到任何关键词，默认为"宽基指数"。

    参数:
        etf_name: ETF名称，如"沪深300ETF"

    返回:
        str: 分类名称
    """
    for keyword, category in ETF_CATEGORY_MAP.items():
        if keyword in etf_name:
            return category
    return "宽基指数"


def fetch_etf_list_from_em() -> pd.DataFrame:
    """
    从东方财富获取ETF列表

    使用AkShare的fund_etf_spot_em()获取在东方财富上市的ETF列表。
    该列表包含ETF代码、名称、类型等信息。

    返回:
        pd.DataFrame: ETF列表数据，列包括：
            - 代码: ETF代码
            - 名称: ETF名称
            - 最新价: 当前价格
            - 涨跌幅: 日涨跌幅(%)

    异常:
        RuntimeError: 获取数据失败时抛出

    示例:
        >>> df = fetch_etf_list_from_em()
        >>> print(df.head())
              代码    名称    最新价   涨跌幅
        0    520890  港股通红利低波ETF  ...
    """
    try:
        logger.info("正在从东方财富获取ETF列表...")
        df = ak.fund_etf_spot_em()
        logger.info(f"成功获取{len(df)}只ETF")
        return df
    except Exception as e:
        logger.error(f"获取ETF列表失败: {e}")
        raise RuntimeError(f"获取ETF列表失败: {e}")


def fetch_etf_history(code: str, period: str = "daily", start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
    """
    获取单只ETF的历史行情数据

    使用AkShare的fund_etf_hist_em()获取ETF的历史K线数据。
    数据包含日期、开盘价、收盘价、最高价、最低价、成交量、涨跌幅等信息。

    注意：
        - 使用后复权(hfq)模式，保证历史价格稳定，适合量化回测
        - AkShare fund_etf_hist_em 返回的是市场交易价格，不是基金净值
        - 后复权价格能准确反映包含分红的真实长期收益
        - 收益率 = (今日收盘 - 昨日收盘) / 昨日收盘

    参数:
        code: ETF代码，如 "510300"
        period: 时间周期，可选值：
            - "daily": 日线
            - "weekly": 周线
            - "monthly": 月线
        start_date: 起始日期，格式 "YYYYMMDD"，默认为一年前
        end_date: 结束日期，格式 "YYYYMMDD"，默认为今天

    返回:
        pd.DataFrame: 历史数据，包含列：
            - 日期: 交易日期
            - 开盘: 开盘价
            - 收盘: 收盘价（用于计算收益率）
            - 最高: 最高价
            - 最低: 最低价
            - 成交量: 成交量
            - 成交额: 成交额
            - 涨跌幅: 日涨跌幅(%)
            - 涨跌额: 日涨跌额
            - 换手率: 换手率(%)

    异常:
        RuntimeError: 获取数据失败时抛出

    示例:
        >>> df = fetch_etf_history("510300", "daily", "20240101", "20241231")
        >>> print(df.head())
               日期      开盘      收盘      最高      最低       成交量       成交额     涨跌幅
        0  2024-01-02  3.8765  3.8900  3.9100  3.8600  12345678  123456789  -0.35
    """
    try:
        if start_date is None:
            start_date = (date.today() - timedelta(days=365)).strftime("%Y%m%d")
        if end_date is None:
            end_date = date.today().strftime("%Y%m%d")

        logger.info(f"正在获取ETF {code} 的历史数据 ({start_date} ~ {end_date})...")
        df = ak.fund_etf_hist_em(
            symbol=code,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust="hfq"
        )
        logger.info(f"成功获取ETF {code} 的 {len(df)} 条历史记录")
        return df
    except Exception as e:
        logger.error(f"获取ETF {code} 历史数据失败: {e}")
        raise RuntimeError(f"获取ETF {code} 历史数据失败: {e}")


def save_etf_info_to_db(session: Session, etf_list: pd.DataFrame) -> int:
    """
    保存ETF基本信息到数据库

    遍历ETF列表，将每只ETF的基本信息存储到数据库。
    如果ETF已存在则更新，不存在则插入。

    参数:
        session: 数据库会话
        etf_list: ETF列表DataFrame，需要包含列：
            - 代码: ETF代码
            - 名称: ETF名称

    返回:
        int: 成功保存的ETF数量

    示例:
        >>> with get_session() as session:
        >>>     df = fetch_etf_list_from_em()
        >>>     count = save_etf_info_to_db(session, df)
        >>>     print(f"保存了{count}只ETF")
    """
    saved_count = 0
    now = datetime.utcnow()

    for _, row in etf_list.iterrows():
        code = str(row.get("代码", "")).strip()
        name = str(row.get("名称", "")).strip()

        if not code or not name:
            continue

        existing = session.query(ETFInfo).filter(ETFInfo.code == code).first()

        if existing:
            existing.name = name
            existing.category = determine_category(name)
            existing.updated_at = now
        else:
            etf_info = ETFInfo(
                code=code,
                name=name,
                category=determine_category(name),
                updated_at=now
            )
            session.add(etf_info)

        saved_count += 1

    session.commit()
    return saved_count


def save_etf_nav_to_db(session: Session, code: str, nav_df: pd.DataFrame) -> int:
    """
    保存ETF历史行情到数据库

    将ETF的历史行情数据批量插入数据库。
    使用INSERT OR REPLACE策略，确保同一ETF同一日期的数据唯一。

    参数:
        session: 数据库会话
        code: ETF代码
        nav_df: AkShare fund_etf_hist_em 返回的DataFrame，字段映射如下：
            - 日期 -> nav_date (交易日期)
            - 收盘 -> nav (收盘价/单位净值，用于计算收益率)
            - 收盘 -> accum_nav (后复权收盘价=累计净值，反映真实长期收益)
            - 涨跌幅 -> change_pct (日涨跌幅，百分比)
            - 成交量 -> volume (成交量)
            - 成交额 -> amount (成交额)

    返回:
        int: 成功保存的行情记录数

    注意:
        - AkShare fund_etf_hist_em 返回的是市场交易价格，不是基金净值
        - 使用 adjust="hfq" 后复权模式，收盘价即为反映分红再投资的累计净值
        - nav 和 accum_nav 在当前数据源下均为后复权收盘价
        - DataFrame中的日期列需要能够转换为date对象
    """
    saved_count = 0

    for _, row in nav_df.iterrows():
        try:
            nav_date_str = str(row.get("日期", ""))

            close_price = float(row.get("收盘", 0))
            open_price = float(row.get("开盘", close_price))
            high_price = float(row.get("最高", close_price))
            low_price = float(row.get("最低", close_price))
            change_pct = float(row.get("涨跌幅", 0))
            volume = float(row.get("成交量", 0))
            amount = float(row.get("成交额", 0))

            if not nav_date_str or close_price <= 0:
                continue

            nav_date = pd.to_datetime(nav_date_str).date()

            existing = session.query(ETFNavHistory).filter(
                ETFNavHistory.etf_code == code,
                ETFNavHistory.nav_date == nav_date
            ).first()

            if existing:
                existing.nav = close_price
                existing.accum_nav = close_price
            else:
                nav_record = ETFNavHistory(
                    etf_code=code,
                    nav_date=nav_date,
                    nav=close_price,
                    accum_nav=close_price
                )
                session.add(nav_record)

            saved_count += 1
        except Exception as e:
            logger.warning(f"处理行情记录失败 (ETF: {code}): {e}")
            continue

    session.commit()
    return saved_count


def get_etf_info_from_db(session: Session) -> List[Dict]:
    """
    从数据库获取所有ETF基本信息

    参数:
        session: 数据库会话

    返回:
        List[Dict]: ETF信息列表，每项包含code, name, category, updated_at

    示例:
        >>> with get_session() as session:
        >>>     etfs = get_etf_info_from_db(session)
        >>>     print(f"数据库中有{len(etfs)}只ETF")
    """
    results = session.query(ETFInfo).all()
    return [
        {
            "code": etf.code,
            "name": etf.name,
            "category": etf.category,
            "updated_at": etf.updated_at.isoformat() if etf.updated_at else None
        }
        for etf in results
    ]


def get_etf_history_from_db(session: Session, code: str, 
                              start_date: Optional[date] = None,
                              end_date: Optional[date] = None) -> List[Dict]:
    """
    从数据库读取ETF历史净值

    参数:
        session: 数据库会话
        code: ETF代码
        start_date: 起始日期（可选）
        end_date: 结束日期（可选）

    返回:
        List[Dict]: 净值记录列表，每项包含date, nav, accum_nav

    示例:
        >>> with get_session() as session:
        >>>     history = get_etf_history_from_db(session, "510300")
        >>>     print(f"获取到{len(history)}条记录")
    """
    query = session.query(ETFNavHistory).filter(ETFNavHistory.etf_code == code)

    if start_date:
        query = query.filter(ETFNavHistory.nav_date >= start_date)
    if end_date:
        query = query.filter(ETFNavHistory.nav_date <= end_date)

    results = query.order_by(ETFNavHistory.nav_date).all()
    return [
        {
            "date": nav.nav_date.isoformat(),
            "nav": float(nav.nav),
            "accum_nav": float(nav.accum_nav)
        }
        for nav in results
    ]


def sync_single_etf(session: Session, code: str) -> Tuple[int, int]:
    """
    同步单只ETF的数据（基本信息 + 历史净值）

    依次获取ETF的基本信息和最近1年的历史净值，
    并保存到数据库。

    参数:
        session: 数据库会话
        code: ETF代码

    返回:
        Tuple[int, int]: (基本信息更新数, 净值记录更新数)

    示例:
        >>> with get_session() as session:
        >>>     info_count, nav_count = sync_single_etf(session, "510300")
    """
    info_count = 0
    nav_count = 0

    try:
        df = fetch_etf_history(code)
        if df is not None and not df.empty:
            nav_count = save_etf_nav_to_db(session, code, df)
    except Exception as e:
        logger.error(f"同步ETF {code} 历史数据失败: {e}")

    return info_count, nav_count


def sync_all_etf_data(progress_callback=None) -> Dict[str, int]:
    """
    同步所有ETF数据（完整流程）

    完整的数据同步流程：
    1. 从东方财富获取ETF列表
    2. 保存ETF基本信息到数据库
    3. 遍历每只ETF获取并保存历史净值

    参数:
        progress_callback: 进度回调函数，签名为 callback(current, total, message)
            - current: 当前处理的ETF索引
            - total: ETF总数
            - message: 当前状态描述

    返回:
        Dict[str, int]: 同步统计，包含：
            - etf_count: ETF总数
            - nav_count: 更新的净值记录总数
            - errors: 失败的ETF数量

    示例:
        >>> def my_progress(current, total, msg):
        >>>     print(f"[{current}/{total}] {msg}")
        >>>
        >>> stats = sync_all_etf_data(progress_callback=my_progress)
        >>> print(f"同步完成: {stats}")
    """
    stats = {"etf_count": 0, "nav_count": 0, "errors": 0}

    with get_session() as session:
        etf_list = fetch_etf_list_from_em()
        save_etf_info_to_db(session, etf_list)
        stats["etf_count"] = len(etf_list)

    etf_codes = etf_list["代码"].astype(str).tolist()
    total = len(etf_codes)

    with get_session() as session:
        for i, code in enumerate(etf_codes):
            try:
                if progress_callback and callable(progress_callback):
                    progress_callback(i + 1, total, f"同步ETF {code}")

                _, nav_count = sync_single_etf(session, code)
                stats["nav_count"] += nav_count
            except Exception as e:
                logger.error(f"同步ETF {code} 失败: {e}")
                stats["errors"] += 1

    return stats


def clear_etf_data(session: Session, code: Optional[str] = None) -> int:
    """
    清除ETF数据（用于测试或重置）

    参数:
        session: 数据库会话
        code: ETF代码，如果为None则清除所有ETF数据

    返回:
        int: 删除的记录数
    """
    if code:
        count = session.query(ETFNavHistory).filter(
            ETFNavHistory.etf_code == code
        ).delete()
        session.commit()
        return count
    else:
        count = session.query(ETFNavHistory).delete()
        session.query(ETFInfo).delete()
        session.commit()
        return count
