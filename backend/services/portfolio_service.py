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


def period_to_days(period: Optional[str]) -> int:
    """
    将时间区段字符串转换为天数

    参数:
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'

    返回:
        int: 对应的天数，默认365天
    """
    if not period:
        return 365

    period_map = {
        '1m': 30,
        '3m': 90,
        '6m': 180,
        '1y': 365,
        '2y': 730,
        '3y': 1095,
        '5y': 1825,
    }

    return period_map.get(period, 365)


def period_to_trading_days(period: Optional[str]) -> int:
    """
    将时间区段字符串转换为交易日天数

    参数:
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'

    返回:
        int: 对应的交易日天数，默认252天（约1年）
    """
    if not period:
        return 252

    trading_day_map = {
        '1m': 21,
        '3m': 63,
        '6m': 126,
        '1y': 252,
        '2y': 504,
        '3y': 756,
        '5y': 1260,
    }

    return trading_day_map.get(period, 252)


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
        >>> print(returns)  # [nan, 0.02, -0.0098, 0.0396]
    """
    if len(nav_series) < 2:
        return [float('nan')]

    returns = []
    for i in range(1, len(nav_series)):
        if nav_series[i-1] != 0:
            ret = (nav_series[i] - nav_series[i-1]) / nav_series[i-1]
            returns.append(ret)
        else:
            returns.append(float('nan'))
    return returns


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


def calculate_volatility(daily_returns: List[float]) -> float:
    """
    计算年化波动率

    波动率是收益率序列的标准差，反映投资的波动程度。
    年化波动率 = 日波动率 * sqrt(252)

    参数:
        daily_returns: 日收益率序列

    返回:
        float: 年化波动率（小数形式）

    示例:
        >>> returns = [0.01, -0.02, 0.015, -0.005]
        >>> vol = calculate_volatility(returns)
        >>> print(f"年化波动率: {vol*100:.2f}%")
    """
    if not daily_returns or len(daily_returns) < 2:
        return 0.0

    returns_array = np.array(daily_returns)
    valid_returns = returns_array[~np.isnan(returns_array)]

    if len(valid_returns) < 2:
        return 0.0

    daily_volatility = np.std(valid_returns, ddof=1)
    annualized_vol = daily_volatility * np.sqrt(TRADING_DAYS_PER_YEAR)
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


def calculate_max_drawdown(nav_series: List[float]) -> Tuple[float, Optional[str]]:
    """
    计算最大回撤

    最大回撤是历史最高点到最低点的最大跌幅，
    反映投资可能遭受的最大损失。

    公式: 最大回撤 = max(最高点 - 最低点) / 最高点

    参数:
        nav_series: 净值序列

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

    max_drawdown_idx = df['drawdown'].idxmin()
    max_drawdown = df.loc[max_drawdown_idx, 'drawdown']

    return max_drawdown, None


def calculate_portfolio_metrics(daily_returns: List[float],
                                   nav_series: List[float],
                                   nav_dates: List[str]) -> PortfolioMetrics:
    """
    计算组合完整业绩指标

    综合计算组合的各项风险收益指标。

    参数:
        daily_returns: 每日收益率序列
        nav_series: 净值序列
        nav_dates: 净值日期序列

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
    annualized_return = calculate_annualized_return(total_return, len(nav_series))
    volatility = calculate_volatility(daily_returns)
    sharpe_ratio = calculate_sharpe_ratio(annualized_return, volatility)
    max_drawdown, max_dd_date = calculate_max_drawdown(nav_series)

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
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    records = session.query(ETFNavHistory).filter(
        ETFNavHistory.etf_code == code,
        ETFNavHistory.nav_date >= start_date,
        ETFNavHistory.nav_date <= end_date
    ).order_by(ETFNavHistory.nav_date).all()

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
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    records = session.query(ETFNavHistory).filter(
        ETFNavHistory.etf_code == code,
        ETFNavHistory.nav_date >= start_date,
        ETFNavHistory.nav_date <= end_date
    ).order_by(ETFNavHistory.nav_date).all()

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
    annualized_return = calculate_annualized_return(total_return, len(nav_series))
    volatility = calculate_volatility(daily_returns)
    sharpe_ratio = calculate_sharpe_ratio(annualized_return, volatility)
    max_drawdown, _ = calculate_max_drawdown(nav_series)

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
                        period: Optional[str] = None) -> Dict:
    """
    评估组合业绩

    参数:
        weights: ETF权重字典，键为代码，值为权重（0-1之间）
            示例: {"510300": 0.5, "510500": 0.5}
        session: 数据库会话（可选）
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'（可选）

    返回:
        Dict: 组合业绩指标字典
    """
    close_session = False
    if session is None:
        session = get_session().__enter__()
        close_session = True

    days = period_to_days(period)

    try:
        etf_codes = list(weights.keys())
        etf_weights = list(weights.values())

        etf_navs_list = []
        for code in etf_codes:
            navs = get_etf_nav_series(session, code, days)
            if navs:
                etf_navs_list.append(navs)

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

        nav_dates = get_etf_nav_dates(session, etf_codes[0], days)[-len(etf_navs_list[0]):] if etf_navs_list else []
        benchmark_navs = get_etf_nav_series(session, "510350.SH", days) if len(weights) > 0 else []
        min_len = min(len(navs) for navs in etf_navs_list) if etf_navs_list else 0
        benchmark_navs = benchmark_navs[-min_len:] if len(benchmark_navs) > min_len else benchmark_navs
        nav_dates = nav_dates[-min_len:] if len(nav_dates) > min_len else nav_dates

        normalized_navs_list = [navs[-min_len:] for navs in etf_navs_list]

        portfolio_navs = []
        for i in range(min_len):
            portfolio_value = sum(
                normalized_navs_list[j][i] * etf_weights[j]
                for j in range(len(etf_codes))
            )
            portfolio_navs.append(portfolio_value)

        daily_returns = calculate_returns_from_nav(portfolio_navs)
        metrics = calculate_portfolio_metrics(daily_returns, portfolio_navs, nav_dates)

        etf_metrics = {}
        for i, code in enumerate(etf_codes):
            if i >= len(normalized_navs_list) or len(normalized_navs_list[i]) < 2:
                continue

            nav_data = normalized_navs_list[i]
            etf_returns = calculate_returns_from_nav(nav_data)
            etf_total_ret = (nav_data[-1] - nav_data[0]) / nav_data[0]
            etf_ann_ret = calculate_annualized_return(etf_total_ret, len(nav_data))
            etf_vol = calculate_volatility(etf_returns)
            etf_sharpe = calculate_sharpe_ratio(etf_ann_ret, etf_vol)
            etf_mdd, _ = calculate_max_drawdown(nav_data)

            etf_info = session.query(ETFNavHistory).filter(
                ETFNavHistory.etf_code == code
            ).first()
            name = etf_info.etf_info.name if etf_info else code

            etf_metrics[code] = {
                "code": code,
                "name": name,
                "weight": etf_weights[i],
                "total_return": etf_total_ret * 100,
                "annualized_return": etf_ann_ret * 100,
                "volatility": etf_vol * 100,
                "sharpe_ratio": etf_sharpe,
                "max_drawdown": etf_mdd * 100
            }

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
            "daily_returns": metrics.daily_returns,
            "etf_metrics": etf_metrics
        }
    finally:
        if close_session:
            session.close()


def compare_portfolios(portfolios: List[Dict[str, float]],
                       period: Optional[str] = None) -> List[Dict]:
    """
    比较多个组合的业绩

    参数:
        portfolios: 组合列表，每个组合是一个权重字典
            示例: [
                {"510300": 0.5, "510500": 0.5},
                {"510300": 1.0}
            ]
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'（可选）

    返回:
        List[Dict]: 每个组合的业绩指标列表
    """
    results = []
    for i, weights in enumerate(portfolios):
        metrics = evaluate_portfolio(weights, period=period)
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