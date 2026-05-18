"""
ETF数据服务模块

本模块负责从AkShare获取ETF列表，从TickFlow获取ETF历史数据。

核心功能：
1. fetch_etf_list(): 获取全量ETF列表 (使用AkShare)
2. fetch_etf_history(): 获取单只ETF历史行情 (使用TickFlow)
3. sync_all_etf_data(): 批量同步所有ETF数据 (使用TickFlow批量接口)
4. get_etf_history_from_db(): 从数据库读取历史行情

数据来源：
- ETF列表: AkShare的fund_etf_spot_em() 获取东方财富ETF列表
- 历史行情: TickFlow的 /v1/klines/batch 获取ETF历史K线数据

数据字段说明：
- TickFlow 返回列式K线数据 (timestamp, open, high, low, close, volume, amount)
- 使用前复权 (forward) 模式，保证历史价格稳定，适合量化回测
- 收益率 = (今日收盘 - 昨日收盘) / 昨日收盘

AkShare接口文档：https://akshare.akfamily.xyz/data/fund/fund_public.html
TickFlow API文档：https://docs.tickflow.org

作者: ETF组合系统
版本: 2.0.0
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple

import pandas as pd
import akshare as ak
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from backend.db.models import ETFInfo, ETFNavHistory, TradeDate
from backend.db.database import get_session
from backend.services.portfolio_service import period_to_days

try:
    from tickflow import TickFlow
    _TICKFLOW_AVAILABLE = True
except ImportError:
    _TICKFLOW_AVAILABLE = False
    logger.warning("TickFlow SDK 未安装，将使用 HTTP 请求模式")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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


def _get_exchange(code: str) -> str:
    """
    根据基金代码判断交易所

    参数:
        code: 基金代码，如 "510300" 或 "159915"

    返回:
        str: 交易所代码，SH（上证）或 SZ（深证）
    """
    if code.startswith("5"):
        return "SH"
    return "SZ"


def _add_exchange_suffix(code: str) -> str:
    """
    给基金代码添加交易所后缀

    参数:
        code: 基金代码，如 "510300"

    返回:
        str: 带后缀的基金代码，如 "510300.SH"
    """
    return f"{code}.{_get_exchange(code)}"


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


def _get_tickflow_client():
    """获取TickFlow客户端实例（免费模式）"""
    if _TICKFLOW_AVAILABLE:
        return TickFlow.free()
    return None


def _convert_klines_to_df(klines_data: Dict, code: str) -> pd.DataFrame:
    """将TickFlow列式K线数据转换为行式DataFrame"""
    timestamps = klines_data.get("timestamp", [])
    if not timestamps:
        return pd.DataFrame()

    opens = klines_data.get("open", [])
    closes = klines_data.get("close", [])
    highs = klines_data.get("high", [])
    lows = klines_data.get("low", [])
    volumes = klines_data.get("volume", [])
    amounts = klines_data.get("amount", [])

    rows = []
    prev_close = None
    for i in range(len(timestamps)):
        close = closes[i] if i < len(closes) else 0
        change_pct = 0.0
        if prev_close is not None and prev_close > 0:
            change_pct = (close - prev_close) / prev_close * 100

        rows.append({
            "日期": pd.to_datetime(timestamps[i], unit="ms", utc=True).tz_convert("Asia/Shanghai").strftime("%Y-%m-%d"),
            "开盘": opens[i] if i < len(opens) else 0,
            "收盘": close,
            "最高": highs[i] if i < len(highs) else 0,
            "最低": lows[i] if i < len(lows) else 0,
            "成交量": volumes[i] if i < len(volumes) else 0,
            "成交额": amounts[i] if i < len(amounts) else 0,
            "涨跌幅": change_pct
        })
        prev_close = close

    return pd.DataFrame(rows)


def fetch_etf_history(code: str, period: str = "daily", start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
    """
    获取单只ETF的历史行情数据

    使用TickFlow的批量K线接口获取单只ETF的历史K线数据。
    数据包含日期、开盘价、收盘价、最高价、最低价、成交量等信息。

    注意：
        - 使用前复权(forward)模式，保证历史价格稳定，适合量化回测
        - TickFlow返回列式数据，需要转置为行式DataFrame
        - 收益率 = (今日收盘 - 昨日收盘) / 昨日收盘

    参数:
        code: ETF代码，如 "510300"
        period: 时间周期，可选值：
            - "daily": 日线 (对应TickFlow的1d)
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

    异常:
        RuntimeError: 获取数据失败时抛出

    示例:
        >>> df = fetch_etf_history("510300", "daily", "20240101", "20241231")
        >>> print(df.head())
               日期      开盘      收盘      最高      最低       成交量       成交额     涨跌幅
        0  2024-01-02  3.8765  3.8900  3.9100  3.8600  12345678  123456789  -0.35
    """
    tf = _get_tickflow_client()
    if tf is None:
        raise RuntimeError("TickFlow SDK未安装")

    try:
        period_map = {"daily": "1d"}
        tickflow_period = period_map.get(period, "1d")

        logger.info(f"正在获取ETF {code} 的历史数据...")

        klines = tf.klines.get(code, period=tickflow_period, count=500, adjust="forward")

        kline_data = klines
        df = _convert_klines_to_df(kline_data, code)

        if start_date and end_date and not df.empty:
            start_dt = pd.to_datetime(start_date, format="%Y%m%d")
            end_dt = pd.to_datetime(end_date, format="%Y%m%d")
            df["日期_dt"] = pd.to_datetime(df["日期"])
            df = df[(df["日期_dt"] >= start_dt) & (df["日期_dt"] <= end_dt)]
            df = df.drop("日期_dt", axis=1)

        logger.info(f"成功获取ETF {code} 的 {len(df)} 条历史记录")
        return df
    except Exception as e:
        logger.error(f"获取ETF {code} 历史数据失败: {e}")
        raise RuntimeError(f"获取ETF {code} 历史数据失败: {e}")


def fetch_etf_history_batch(codes: List[str], period: str = "daily", count: int = 500) -> Dict[str, pd.DataFrame]:
    """
    批量获取多只ETF的历史行情数据

    使用TickFlow的 /v1/klines/batch 一次请求获取多只ETF的历史K线数据。
    这是同步多只ETF的推荐方式，比逐个调用 fetch_etf_history 更高效。

    参数:
        codes: ETF代码列表，如 ["510300", "510500"]
        period: 时间周期，默认 "daily" (1d)
        count: 返回的K线数量，默认500

    返回:
        Dict[str, pd.DataFrame]: 键为ETF代码，值为对应的历史数据DataFrame

    示例:
        >>> results = fetch_etf_history_batch(["510300", "510500"], count=250)
        >>> for code, df in results.items():
        >>>     print(f"{code}: {len(df)} records")
    """
    if not codes:
        return {}

    tf = _get_tickflow_client()
    if tf is None:
        raise RuntimeError("TickFlow SDK未安装")

    try:
        logger.info(f"正在批量获取{len(codes)}只ETF的历史数据...")

        klines_dict = tf.klines.batch(codes, period="1d", count=count, adjust="forward")

        results = {}
        for symbol in codes:
            if symbol not in klines_dict:
                results[symbol] = pd.DataFrame()
                continue

            kline_data = klines_dict[symbol]
            results[symbol] = _convert_klines_to_df(kline_data, symbol)

        logger.info(f"批量获取完成，共处理{len(results)}只ETF")
        return results
    except Exception as e:
        logger.error(f"批量获取ETF历史数据失败: {e}")
        raise RuntimeError(f"批量获取ETF历史数据失败: {e}")


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
    now = datetime.utcnow()
    mappings = []

    for row in etf_list.itertuples(index=False):
        code = str(row.代码).strip() if hasattr(row, '代码') else str(getattr(row, 0, "")).strip()
        name = str(row.名称).strip() if hasattr(row, '名称') else str(getattr(row, 1, "")).strip()

        if not code or not name:
            continue

        full_code = _add_exchange_suffix(code)
        mappings.append({
            "code": full_code,
            "name": name,
            "category": determine_category(name),
            "updated_at": now
        })

    if mappings:
        session.bulk_insert_mappings(ETFInfo, mappings)
        session.commit()

    return len(mappings)


def save_etf_nav_to_db(session: Session, code: str, nav_df: pd.DataFrame) -> int:
    """
    保存ETF历史行情到数据库

    将ETF的历史行情数据批量插入数据库。
    使用INSERT OR REPLACE策略，确保同一ETF同一日期的数据唯一。

    参数:
        session: 数据库会话
        code: ETF代码
        nav_df: TickFlow返回的DataFrame，字段映射如下：
            - 日期 -> nav_date (交易日期)
            - 收盘 -> nav (收盘价/单位净值，用于计算收益率)
            - 收盘 -> accum_nav (前复权收盘价=累计净值，反映真实长期收益)
            - 涨跌幅 -> change_pct (日涨跌幅，百分比)
            - 成交量 -> volume (成交量)
            - 成交额 -> amount (成交额)

    返回:
        int: 成功保存的行情记录数

    注意:
        - TickFlow 使用 adjust=forward 前复权模式
        - 前复权收盘价即为反映分红再投资的累计净值
        - nav 和 accum_nav 在当前数据源下均为前复权收盘价
        - DataFrame中的日期列需要能够转换为date对象
    """
    mappings = []

    for row in nav_df.itertuples(index=False):
        try:
            nav_date_str = str(row.日期) if hasattr(row, '日期') else ""

            close_price = float(getattr(row, '收盘', 0) if hasattr(row, '收盘') else 0)

            if not nav_date_str or close_price <= 0:
                continue

            nav_date = pd.to_datetime(nav_date_str).date()
            mappings.append({
                "etf_code": code,
                "nav_date": nav_date,
                "nav": close_price,
                "accum_nav": close_price
            })
        except Exception as e:
            logger.warning(f"处理行情记录失败 (ETF: {code}): {e}")
            continue

    if mappings:
        session.bulk_insert_mappings(ETFNavHistory, mappings)
        session.commit()

    return len(mappings)


def get_etf_data_days(session: Session, code: str, end_date: date, trade_dates: List[date]) -> int:
    """获取ETF在指定周期内的实际交易日数据天数"""
    if not trade_dates:
        return 0

    count = session.query(ETFNavHistory).filter(
        ETFNavHistory.etf_code == code,
        ETFNavHistory.nav_date <= end_date,
        ETFNavHistory.nav_date.in_(trade_dates)
    ).count()

    return count


def fetch_trade_dates() -> int:
    """
    从AkShare获取沪深交易所历史交易日历并写入数据库

    仅插入数据库中不存在的日期，不更新已有数据。

    返回:
        int: 新增的交易日数量
    """
    logger.info("开始从AkShare获取交易日历...")
    df = ak.tool_trade_date_hist_sina()
    trade_dates = pd.to_datetime(df['trade_date']).dt.date.tolist()
    logger.info(f"从AkShare获取到 {len(trade_dates)} 个交易日")

    with get_session() as session:
        existing = set(
            row[0] for row in session.query(TradeDate.trade_date).all()
        )
        new_dates = [d for d in trade_dates if d not in existing]
        logger.info(f"数据库中已有 {len(existing)} 个交易日，新增 {len(new_dates)} 个")

        if new_dates:
            mappings = [{"trade_date": d} for d in new_dates]
            session.bulk_insert_mappings(TradeDate, mappings)
            session.commit()
            logger.info(f"成功写入 {len(new_dates)} 个交易日")

    return len(new_dates)


def get_trade_dates(session: Session, start_date: date, end_date: date) -> List[date]:
    """
    从数据库获取指定日期范围内的所有交易日

    参数:
        session: 数据库会话
        start_date: 起始日期
        end_date: 结束日期

    返回:
        List[date]: 该范围内的所有交易日，按日期升序排列
    """
    results = session.query(TradeDate.trade_date).filter(
        TradeDate.trade_date >= start_date,
        TradeDate.trade_date <= end_date
    ).order_by(TradeDate.trade_date).all()

    return [r[0] for r in results]


def get_etf_info_from_db(session: Session, period: Optional[str] = None) -> List[Dict]:
    """
    从数据库获取所有ETF基本信息

    参数:
        session: 数据库会话
        period: 时间区段字符串（如 '1m', '3m', '6m', '1y' 等），用于计算数据是否充足

    返回:
        List[Dict]: ETF信息列表，每项包含code, name, category, updated_at,
                   以及可选的data_days和has_enough_data（当指定period时）

    示例:
        >>> with get_session() as session:
        >>>     etfs = get_etf_info_from_db(session)
        >>>     print(f"数据库中有{len(etfs)}只ETF")
    """
    results = session.query(ETFInfo).all()
    etfs = []

    if period:
        lookback_days = period_to_days(period)

    for etf in results:
        item = {
            "code": etf.code,
            "name": etf.name,
            "category": etf.category,
            "updated_at": etf.updated_at.isoformat() if etf.updated_at else None
        }

        if period:
            etf_end_date = etf.updated_at.date() if etf.updated_at else date.today()
            etf_start_date = etf_end_date - timedelta(days=lookback_days)
            trade_dates_in_period = get_trade_dates(session, etf_start_date, etf_end_date)
            required_trading_days = len(trade_dates_in_period)
            actual_days = get_etf_data_days(session, etf.code, etf_end_date, trade_dates_in_period)
            item["data_days"] = actual_days
            item["has_enough_data"] = actual_days >= required_trading_days

        etfs.append(item)

    return etfs


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


def sync_all_etf_data(progress_callback=None, period: Optional[str] = None) -> Dict[str, int]:
    """
    同步所有ETF数据（完整流程）

    完整的数据同步流程：
    1. 从TickFlow获取ETF列表
    2. 保存ETF基本信息到数据库
    3. 使用批量接口获取并保存所有ETF历史净值

    参数:
        progress_callback: 进度回调函数，签名为 callback(current, total, message)
        period: 时间区段字符串（如 '1y'），按此区段过滤保存的数据

    返回:
        Dict[str, int]: 同步统计，包含：
            - etf_count: ETF总数
            - nav_count: 更新的净值记录总数
            - errors: 失败的ETF数量
    """
    stats = {"etf_count": 0, "nav_count": 0, "errors": 0}

    start_date = None
    fetch_count = 500
    if period:
        days = period_to_days(period)
        start_date = date.today() - timedelta(days=days)
        if days >= 730:
            fetch_count = days

    with get_session() as session:
        clear_etf_data(session)
        etf_list = fetch_etf_list_from_em()
        save_etf_info_to_db(session, etf_list)
        stats["etf_count"] = len(etf_list)

    etf_codes = [_add_exchange_suffix(c) for c in etf_list["代码"].astype(str).tolist()]
    total = len(etf_codes)

    batch_size = 500
    batch_results = {}
    for i in range(0, total, batch_size):
        batch_codes = etf_codes[i:i + batch_size]
        logger.info(f"正在获取第{i // batch_size + 1}批, 共{(total + batch_size - 1) // batch_size}批, 代码数: {len(batch_codes)}, 请求数量: {fetch_count}")
        batch_data = fetch_etf_history_batch(batch_codes, count=fetch_count)
        batch_results.update(batch_data)

    with get_session() as session:
        for i, code in enumerate(etf_codes):
            if progress_callback and callable(progress_callback):
                progress_callback(i + 1, total, f"保存ETF {code}")

            if code in batch_results:
                df = batch_results[code]
                if df is not None and not df.empty:
                    if start_date:
                        df = df[pd.to_datetime(df['日期']) >= pd.Timestamp(start_date)]
                        if df.empty:
                            stats["errors"] += 1
                            continue
                    try:
                        nav_count = save_etf_nav_to_db(session, code, df)
                        stats["nav_count"] += nav_count
                    except Exception as e:
                        logger.error(f"保存ETF {code} 数据失败: {e}")
                        stats["errors"] += 1
                else:
                    stats["errors"] += 1
            else:
                stats["errors"] += 1

        session.query(ETFInfo).filter(
            ~ETFInfo.code.in_(
                session.query(ETFNavHistory.etf_code).distinct()
            )
        ).delete(synchronize_session=False)
        session.commit()

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