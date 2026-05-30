"""
组合服务模块 - 组合评估与业绩计算

本模块负责组合的业绩评估和风险指标计算。

核心功能：
1. 计算组合的收益率（年化收益率、日收益率等）
2. 计算组合的波动率（年化波动率）
3. 计算夏普比率（风险调整后的收益指标）
4. 计算最大回撤（历史最大跌幅）
5. 计算其他风险指标

算法说明：
- 年化收益率: (1 + 累计收益率)^(252/交易天数) - 1
- 年化波动率: 日收益率标准差 * sqrt(252)
- 夏普比率: (年化收益率 - 无风险利率) / 年化波动率
- 最大回撤: max(最高点 - 最低点) / 最高点

作者: ETF组合系统
版本: 1.0.0
"""

import logging
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.db.models import ETFNavHistory
from backend.db.database import get_session

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.03
TRADING_DAYS_PER_YEAR = 252
BENCHMARK_ETF_CODE = "510310.SH"


def _parse_period(period: str) -> Tuple[int, str]:
    """解析period字符串，返回(数字, 单位)的元组"""
    if not period:
        return 1, 'y'
    unit = period[-1]
    try:
        num = int(period[:-1])
    except ValueError:
        num = 1
    return num, unit


def get_annual_factor(period: Optional[str]) -> int:
    """
    根据period返回年化因子（月数）

    按实际统计时间范围计算年化因子，而非固定252个交易日。

    参数:
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'

    返回:
        int: 年化因子（如1m=12, 3m=4, 6m=2, 1y+=1）

    示例:
        >>> get_annual_factor("1m")
        12
        >>> get_annual_factor("3m")
        4
        >>> get_annual_factor("1y")
        1
    """
    if not period:
        return 1
    num, unit = _parse_period(period)
    if unit == 'm':
        return 12 // num
    return 1


def period_to_days(period: Optional[str]) -> int:
    """
    将时间区段字符串转换为精确的天数

    使用 dateutil.relativedelta 计算精确的日历天数，考虑闰年、闰月等。

    参数:
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'

    返回:
        int: 对应的天数，默认365天
    """
    if not period:
        return 365

    num, unit = _parse_period(period)
    today = date.today()

    if unit == 'm':
        target_date = today + relativedelta(months=num)
    elif unit == 'y':
        target_date = today + relativedelta(years=num)
    else:
        return 365

    delta = target_date - today
    return delta.days


def period_to_trading_days(period: Optional[str]) -> int:
    """
    将时间区段字符串转换为交易日天数

    基于 period_to_days 计算的精确日历天数，再按 252/365 的比例换算为交易日天数。

    参数:
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'

    返回:
        int: 对应的交易日天数，默认252天（约1年）
    """
    if not period:
        return 252

    calendar_days = period_to_days(period)
    trading_days = round(calendar_days * 252 / 365)
    return max(trading_days, 1)


@dataclass
class PortfolioMetrics:
    """
    组合业绩指标数据类

    存储组合的各项评估指标，便于传递和序列化。

    属性说明：
    - total_return: 累计收益率（百分比）
    - annualized_return: 年化收益率（百分比）
    - volatility: 年化波动率（百分比）
    - sharpe_ratio: 夏普比率
    - max_drawdown: 最大回撤（百分比）
    - max_drawdown_date: 最大回撤发生日期
    - daily_returns: 每日收益率列表
    - nav_series: 净值序列（用于绘图）
    - nav_dates: 净值日期序列（对应nav_series的每个值）

    示例:
        >>> metrics = PortfolioMetrics(
        >>>     total_return=15.5,
        >>>     annualized_return=12.3,
        >>>     volatility=18.7,
        >>>     sharpe_ratio=0.67,
        >>>     max_drawdown=-8.2,
        >>>     max_drawdown_date="2024-03-15",
        >>>     daily_returns=[0.01, -0.02, 0.015...],
        >>>     nav_series=[1.0, 1.01, 0.99...],
        >>>     nav_dates=["2024-01-02", "2024-01-03", ...]
        >>> )
    """
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_date: Optional[str]
    daily_returns: List[float]
    nav_series: List[float]
    nav_dates: List[str]
    holding_period: int


@dataclass
class SingleETFFMetrics:
    """
    单只ETF业绩指标数据类

    属性说明：
    - code: ETF代码
    - name: ETF名称
    - total_return: 累计收益率
    - annualized_return: 年化收益率
    - volatility: 年化波动率
    - sharpe_ratio: 夏普比率
    - max_drawdown: 最大回撤
    - nav_series: 净值序列
    """
    code: str
    name: str
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    nav_series: List[float]


def calculate_returns_from_nav(nav_series: List[float]) -> List[float]:
    """
    从净值序列计算收益率序列

    收益率 = (今日净值 - 昨日净值) / 昨日净值

    参数:
        nav_series: 净值序列，如 [1.0, 1.02, 1.01, 1.05]

    返回:
        List[float]: 收益率序列，如 [0.02, -0.0098, 0.0396]
        第一天没有收益率，返回NaN

    示例:
        >>> nav = [1.0, 1.02, 1.01, 1.05]
        >>> returns = calculate_returns_from_nav(nav)
        >>> print(returns)  # [0.02, -0.0098, 0.0396]
    """
    if len(nav_series) < 2:
        return [float('nan')]

    arr = np.array(nav_series, dtype=float)
    prev = arr[:-1]
    curr = arr[1:]
    with np.errstate(divide='ignore', invalid='ignore'):
        returns = (curr - prev) / np.where(prev != 0, prev, np.nan)
    return returns.tolist()


def calculate_annualized_return(total_return: float, days: int) -> float:
    """
    计算年化收益率

    年化收益率将任意周期的收益率标准化为年度收益率，
    便于不同投资期限的比较。

    公式: 年化收益率 = (1 + 累计收益率)^(252/交易天数) - 1

    参数:
        total_return: 累计收益率（小数形式，如0.15表示15%）
        days: 持有天数

    返回:
        float: 年化收益率（小数形式）

    示例:
        >>> total_ret = 0.15  # 15%累计收益
        >>> days = 180  # 持有180天
        >>> ann_ret = calculate_annualized_return(total_ret, days)
        >>> print(f"年化收益: {ann_ret*100:.2f}%")  # 年化收益: 25.69%
    """
    if days <= 0:
        return 0.0
    return (1 + total_return) ** (TRADING_DAYS_PER_YEAR / days) - 1


def calculate_volatility(daily_returns: List[float], annual_factor: int = TRADING_DAYS_PER_YEAR) -> float:
    """
    计算年化波动率

    波动率是收益率序列的标准差，反映投资的波动程度。
    年化波动率 = 日波动率 * sqrt(annual_factor)

    参数:
        daily_returns: 日收益率序列
        annual_factor: 年化因子（默认252），根据统计时间范围确定

    返回:
        float: 年化波动率（小数形式）

    示例:
        >>> returns = [0.01, -0.02, 0.015, -0.005]
        >>> vol = calculate_volatility(returns)
        >>> print(f"年化波动率: {vol*100:.2f}%")
    """
    if not daily_returns:
        return 0.0

    valid_returns = np.array(daily_returns)[~np.isnan(np.array(daily_returns))]

    if len(valid_returns) < 2:
        return 0.0

    daily_volatility = np.std(valid_returns, ddof=1)
    annualized_vol = daily_volatility * np.sqrt(annual_factor)
    return annualized_vol


def calculate_sharpe_ratio(annualized_return: float, volatility: float,
                            risk_free_rate: float = RISK_FREE_RATE) -> float:
    """
    计算夏普比率

    夏普比率衡量单位风险所获得的超额收益，
    是最常用的风险调整收益指标。

    公式: 夏普比率 = (年化收益率 - 无风险利率) / 年化波动率

    参数:
        annualized_return: 年化收益率（小数形式）
        volatility: 年化波动率（小数形式）
        risk_free_rate: 无风险利率（默认3%）

    返回:
        float: 夏普比率

    注意:
        - 波动率为0时返回0（避免除零错误）
        - 夏普比率越大越好

    示例:
        >>> sharpe = calculate_sharpe_ratio(0.12, 0.18)
        >>> print(f"夏普比率: {sharpe:.2f}")  # 0.50
    """
    if volatility == 0:
        return 0.0
    return (annualized_return - risk_free_rate) / volatility


def calculate_max_drawdown(nav_series: List[float], nav_dates: Optional[List[str]] = None) -> Tuple[float, Optional[str]]:
    """
    计算最大回撤

    最大回撤是历史最高点到最低点的最大跌幅，
    反映投资可能遭受的最大损失。

    公式: 最大回撤 = max(最高点 - 最低点) / 最高点

    参数:
        nav_series: 净值序列
        nav_dates: 净值日期序列（可选）

    返回:
        Tuple[float, Optional[str]]: (最大回撤值, 最大回撤发生日期)

    示例:
        >>> nav = [1.0, 1.1, 1.05, 0.95, 1.0]
        >>> mdd, date = calculate_max_drawdown(nav)
        >>> print(f"最大回撤: {mdd*100:.2f}%, 发生在: {date}")
    """
    if not nav_series or len(nav_series) < 2:
        return 0.0, None

    df = pd.DataFrame({'nav': nav_series})
    df['rolling_max'] = df['nav'].cummax()
    df['drawdown'] = (df['nav'] - df['rolling_max']) / df['rolling_max']

    max_dd_idx = int(df['drawdown'].idxmin())
    max_drawdown = df.loc[max_dd_idx, 'drawdown']
    max_dd_date = nav_dates[max_dd_idx] if nav_dates and max_dd_idx < len(nav_dates) else None

    return max_drawdown, max_dd_date


def calculate_portfolio_metrics(daily_returns: List[float],
                                   nav_series: List[float],
                                   nav_dates: List[str],
                                   benchmark_navs: Optional[List[float]] = None,
                                   annual_factor: int = TRADING_DAYS_PER_YEAR) -> PortfolioMetrics:
    """
    计算组合完整业绩指标

    综合计算组合的各项风险收益指标。

    参数:
        daily_returns: 每日收益率序列
        nav_series: 净值序列
        nav_dates: 净值日期序列
        annual_factor: 年化因子（默认252），根据统计时间范围确定

    返回:
        PortfolioMetrics: 组合业绩指标对象

    示例:
        >>> metrics = calculate_portfolio_metrics(returns, navs, dates)
        >>> print(f"年化收益: {metrics.annualized_return*100:.2f}%")
    """
    if not daily_returns or not nav_series or len(nav_series) < 2:
        return PortfolioMetrics(
            total_return=0.0,
            annualized_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_date=None,
            daily_returns=[],
            nav_series=[],
            nav_dates=[],
            holding_period=0
        )

    total_return = (nav_series[-1] - nav_series[0]) / nav_series[0]
    annualized_return = calculate_annualized_return(total_return, len(daily_returns))
    volatility = calculate_volatility(daily_returns, annual_factor)

    risk_free_rate = RISK_FREE_RATE
    if benchmark_navs and len(benchmark_navs) >= 2:
        benchmark_total_return = (benchmark_navs[-1] - benchmark_navs[0]) / benchmark_navs[0]
        benchmark_ann_return = calculate_annualized_return(benchmark_total_return, len(benchmark_navs))
        risk_free_rate = max(0, benchmark_ann_return)

    sharpe_ratio = calculate_sharpe_ratio(annualized_return, volatility, risk_free_rate)
    max_drawdown, max_dd_date = calculate_max_drawdown(nav_series, nav_dates)

    return PortfolioMetrics(
        total_return=total_return * 100,
        annualized_return=annualized_return * 100,
        volatility=volatility * 100,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown * 100,
        max_drawdown_date=max_dd_date,
        daily_returns=daily_returns,
        nav_series=nav_series,
        nav_dates=nav_dates,
        holding_period=len(nav_series)
    )


def _query_etf_nav_records(session: Session, code: str, days: int = 365) -> List[ETFNavHistory]:
    """Query ETF NAV history records from DB (used by get_etf_nav_series/get_etf_nav_dates)."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return session.query(ETFNavHistory).filter(
        ETFNavHistory.etf_code == code,
        ETFNavHistory.nav_date >= start_date,
        ETFNavHistory.nav_date <= end_date
    ).order_by(ETFNavHistory.nav_date).all()


def _get_etf_name(session: Session, code: str) -> str:
    """Query ETF name from DB; returns code if not found."""
    record = session.query(ETFNavHistory).filter(ETFNavHistory.etf_code == code).first()
    return record.etf_info.name if record and record.etf_info else code


def get_etf_nav_series(session: Session, code: str, days: int = 365) -> List[float]:
    """
    从数据库获取ETF净值序列

    参数:
        session: 数据库会话
        code: ETF代码
        days: 获取最近多少天的数据

    返回:
        List[float]: 净值序列

    示例:
        >>> with get_session() as session:
        >>>     navs = get_etf_nav_series(session, "510300", 365)
    """
    records = _query_etf_nav_records(session, code, days)
    return [float(r.accum_nav) for r in records]


def get_etf_nav_dates(session: Session, code: str, days: int = 365) -> List[str]:
    """
    从数据库获取ETF净值日期序列

    参数:
        session: 数据库会话
        code: ETF代码
        days: 获取最近多少天的数据

    返回:
        List[str]: 日期序列（格式：YYYY-MM-DD）

    示例:
        >>> with get_session() as session:
        >>>     dates = get_etf_nav_dates(session, "510300", 365)
    """
    records = _query_etf_nav_records(session, code, days)
    return [r.nav_date.isoformat() for r in records]


def calculate_single_etf_metrics(session: Session, code: str, name: str,
                                  period: Optional[str] = None) -> SingleETFFMetrics:
    """
    计算单只ETF的业绩指标

    参数:
        session: 数据库会话
        code: ETF代码
        name: ETF名称
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'（可选）

    返回:
        SingleETFFMetrics: ETF业绩指标对象
    """
    days = period_to_days(period)
    nav_series = get_etf_nav_series(session, code, days)
    nav_dates = get_etf_nav_dates(session, code, days)

    if len(nav_series) < 2:
        return SingleETFFMetrics(
            code=code,
            name=name,
            total_return=0.0,
            annualized_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            nav_series=[]
        )

    daily_returns = calculate_returns_from_nav(nav_series)
    total_return = (nav_series[-1] - nav_series[0]) / nav_series[0]
    annualized_return = calculate_annualized_return(total_return, len(daily_returns))
    volatility = calculate_volatility(daily_returns, get_annual_factor(period))
    sharpe_ratio = calculate_sharpe_ratio(annualized_return, volatility)
    max_drawdown, _ = calculate_max_drawdown(nav_series, nav_dates)

    return SingleETFFMetrics(
        code=code,
        name=name,
        total_return=total_return * 100,
        annualized_return=annualized_return * 100,
        volatility=volatility * 100,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown * 100,
        nav_series=nav_series
    )


def evaluate_portfolio(weights: Dict[str, float],
                        session: Optional[Session] = None,
                        period: Optional[str] = None,
                        benchmark_code: Optional[str] = None) -> Dict:
    """
    评估组合业绩

    参数:
        weights: ETF权重字典，键为代码，值为权重（0-1之间）
            示例: {"510300": 0.5, "510500": 0.5}
        session: 数据库会话（可选）
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'（可选）
        benchmark_code: 基准ETF代码（可选，默认510310）

    返回:
        Dict: 组合业绩指标字典
    """
    own_session = None
    if session is None:
        own_session = get_session().__enter__()
        session = own_session

    days = period_to_days(period)

    try:
        etf_codes_all = list(weights.keys())
        etf_weights_all = list(weights.values())

        etf_navs_list = []
        valid_codes = []
        valid_weights = []
        for code, w in zip(etf_codes_all, etf_weights_all):
            navs = get_etf_nav_series(session, code, days)
            if navs:
                etf_navs_list.append(navs)
                valid_codes.append(code)
                valid_weights.append(w)

        if not etf_navs_list:
            return {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "holding_period": 0,
                "nav_series": [],
                "nav_dates": [],
                "etf_metrics": {}
            }

        nav_dates = get_etf_nav_dates(session, valid_codes[0], days)[-len(etf_navs_list[0]):] if etf_navs_list else []  # defensive: guards against inconsistent data length; NOP when aligned
        benchmark_etf = benchmark_code or BENCHMARK_ETF_CODE
        benchmark_navs_raw = get_etf_nav_series(session, benchmark_etf, days) if valid_codes else []
        min_len = min(len(navs) for navs in etf_navs_list) if etf_navs_list else 0
        benchmark_navs = benchmark_navs_raw[max(0, len(benchmark_navs_raw)-min_len):]
        nav_dates = nav_dates[max(0, len(nav_dates)-min_len):]

        normalized_navs_list = [navs[-min_len:] for navs in etf_navs_list]

        portfolio_navs = []
        for i in range(min_len):
            portfolio_value = sum(
                normalized_navs_list[j][i] * valid_weights[j]
                for j in range(len(valid_codes))
            )
            portfolio_navs.append(portfolio_value)

        daily_returns = calculate_returns_from_nav(portfolio_navs)
        metrics = calculate_portfolio_metrics(daily_returns, portfolio_navs, nav_dates, benchmark_navs, get_annual_factor(period))

        etf_metrics = {}
        for i, code in enumerate(valid_codes):
            if i >= len(normalized_navs_list) or len(normalized_navs_list[i]) < 2:
                continue

            nav_data = normalized_navs_list[i]
            etf_returns = calculate_returns_from_nav(nav_data)
            etf_total_ret = (nav_data[-1] - nav_data[0]) / nav_data[0]
            etf_ann_ret = calculate_annualized_return(etf_total_ret, len(etf_returns))
            etf_vol = calculate_volatility(etf_returns)
            etf_sharpe = calculate_sharpe_ratio(etf_ann_ret, etf_vol)
            etf_mdd, _ = calculate_max_drawdown(nav_data, nav_dates)

            name = _get_etf_name(session, code)

            etf_metrics[code] = {
                "code": code,
                "name": name,
                "weight": valid_weights[i],
                "total_return": etf_total_ret * 100,
                "annualized_return": etf_ann_ret * 100,
                "volatility": etf_vol * 100,
                "sharpe_ratio": etf_sharpe,
                "max_drawdown": etf_mdd * 100
            }

        benchmark_name = _get_etf_name(session, benchmark_etf)

        return {
            "total_return": metrics.total_return,
            "annualized_return": metrics.annualized_return,
            "volatility": metrics.volatility,
            "sharpe_ratio": metrics.sharpe_ratio,
            "max_drawdown": metrics.max_drawdown,
            "holding_period": metrics.holding_period,
            "nav_series": metrics.nav_series,
            "nav_dates": metrics.nav_dates,
            "benchmark_nav_series": benchmark_navs,
            "benchmark_code": BENCHMARK_ETF_CODE,
            "benchmark_name": benchmark_name,
            "daily_returns": metrics.daily_returns,
            "etf_metrics": etf_metrics
        }
    finally:
        if own_session is not None:
            own_session.close()


def compare_portfolios(portfolios: List[Dict[str, float]],
                       period: Optional[str] = None,
                       benchmark_code: Optional[str] = None) -> List[Dict]:
    """
    比较多个组合的业绩

    参数:
        portfolios: 组合列表，每个组合是一个权重字典
            示例: [
                {"510300": 0.5, "510500": 0.5},
                {"510300": 1.0}
            ]
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'（可选）
        benchmark_code: 基准ETF代码（可选）

    返回:
        List[Dict]: 每个组合的业绩指标列表
    """
    results = []
    for i, weights in enumerate(portfolios):
        metrics = evaluate_portfolio(weights, period=period, benchmark_code=benchmark_code)
        metrics["portfolio_id"] = i + 1
        metrics["portfolio_name"] = f"组合{i + 1}"
        results.append(metrics)
    return results


if __name__ == "__main__":
    print("组合服务模块测试...")
    with get_session() as session:
        test_weights = {"510300": 0.6, "510500": 0.4}
        result = evaluate_portfolio(test_weights, session)
        print(f"组合年化收益: {result['annualized_return']:.2f}%")
        print(f"组合波动率: {result['volatility']:.2f}%")
        print(f"夏普比率: {result['sharpe_ratio']:.4f}")
        print(f"最大回撤: {result['max_drawdown']:.2f}%")