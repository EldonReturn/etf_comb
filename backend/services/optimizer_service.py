"""
组合优化服务模块 - 最大收益组合求解

本模块使用均值-方差优化框架寻找最大收益组合。

优化目标：
- 最大化组合预期收益 Σ(wᵢ × rᵢ)

优化方法：
- 使用scipy.optimize.minimize求解
- 将最大化问题转化为最小化问题（加负号）

约束条件：
- 权重和为1: Σwᵢ = 1
- 权重非负: 0 ≤ wᵢ ≤ 1
- 无单个ETF上限（用户要求）

风险厌恶系数：
- λ值越大表示越厌恶风险，λ=0时只追求最大收益
- 默认λ=0表示只最大化收益（用户目标是最大收益）

作者: ETF组合系统
版本: 1.0.0
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from sqlalchemy.orm import Session

from backend.services.portfolio_service import (
    get_etf_nav_series,
    calculate_returns_from_nav,
    calculate_annualized_return,
    calculate_volatility,
    calculate_sharpe_ratio,
    evaluate_portfolio,
    get_session,
    period_to_days
)

logger = logging.getLogger(__name__)

RISK_AVERSION_DEFAULT = 0.0


@dataclass
class OptimizationResult:
    """
    优化结果数据类

    存储组合优化的结果。

    属性说明：
    - success: 优化是否成功
    - weights: 最优权重字典 {ETF代码: 权重}
    - expected_return: 预期年化收益率(%)
    - volatility: 年化波动率(%)
    - sharpe_ratio: 夏普比率
    - message: 优化结果描述
    """
    success: bool
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    message: str


def calculate_covariance_matrix(returns_list: List[List[float]]) -> np.ndarray:
    """
    计算收益率序列的协方差矩阵

    协方差矩阵反映各ETF收益率之间的相关关系。
    用于计算组合的整体波动率。

    参数:
        returns_list: 收益率序列列表，每个元素是一个ETF的日收益率序列

    返回:
        np.ndarray: N×N协方差矩阵，N为ETF数量

    示例:
        >>> returns1 = [0.01, -0.02, 0.015]
        >>> returns2 = [0.005, -0.01, 0.02]
        >>> cov = calculate_covariance_matrix([returns1, returns2])
        >>> print(cov.shape)  # (2, 2)
    """
    if not returns_list or len(returns_list) == 0:
        return np.array([])

    min_len = min(len(r) for r in returns_list)
    aligned_returns = np.array([r[-min_len:] for r in returns_list])

    cov_matrix = np.cov(aligned_returns, rowvar=True)

    if cov_matrix.shape[0] != cov_matrix.shape[1]:
        n = len(returns_list)
        cov_matrix = np.zeros((n, n))

    return cov_matrix


def portfolio_return(weights: np.ndarray, returns: np.ndarray) -> float:
    """
    计算组合预期收益

    组合收益 = Σ(权重ᵢ × 收益率ᵢ)

    参数:
        weights: 权重数组
        returns: 各ETF的年化收益率数组

    返回:
        float: 组合预期收益率

    示例:
        >>> weights = np.array([0.6, 0.4])
        >>> returns = np.array([0.15, 0.10])  # 15%和10%年化收益
        >>> ret = portfolio_return(weights, returns)
        >>> print(f"组合收益: {ret:.4f}")  # 0.13
    """
    return np.dot(weights, returns)


def portfolio_volatility(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    """
    计算组合波动率

    组合波动率 = sqrt(weights' × Cov × weights)

    参数:
        weights: 权重数组
        cov_matrix: 协方差矩阵

    返回:
        float: 组合波动率

    示例:
        >>> weights = np.array([0.6, 0.4])
        >>> cov = np.array([[0.04, 0.01], [0.01, 0.025]])  # 20%波动率^2=0.04
        >>> vol = portfolio_volatility(weights, cov)
        >>> print(f"组合波动率: {vol:.4f}")
    """
    if cov_matrix.size == 0:
        return 0.0
    return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))


def negative_sharpe_ratio(weights: np.ndarray, returns: np.ndarray,
                            cov_matrix: np.ndarray, risk_free: float = 0.03) -> float:
    """
    计算负夏普比率（用于最小化）

    优化时最小化负夏普比率等同于最大化夏普比率。

    参数:
        weights: 权重数组
        returns: 各ETF年化收益率数组
        cov_matrix: 协方差矩阵
        risk_free: 无风险利率

    返回:
        float: 负夏普比率
    """
    p_return = portfolio_return(weights, returns)
    p_volatility = portfolio_volatility(weights, cov_matrix)
    if p_volatility == 0:
        return 0.0
    sharpe = (p_return - risk_free) / p_volatility
    return -sharpe


def maximize_return_objective(weights: np.ndarray, returns: np.ndarray,
                               cov_matrix: np.ndarray, risk_aversion: float) -> float:
    """
    最大收益优化目标函数

    目标 = Σ(wᵢ × rᵢ) - λ × ΣΣ(wᵢ × wⱼ × σᵢⱼ)

    当risk_aversion=0时，只最大化收益。

    参数:
        weights: 权重数组
        returns: 各ETF年化收益率数组
        cov_matrix: 协方差矩阵
        risk_aversion: 风险厌恶系数

    返回:
        float: 目标函数值（最小化）
    """
    p_return = portfolio_return(weights, returns)
    p_volatility_sq = np.dot(weights.T, np.dot(cov_matrix, weights))

    objective = -(p_return - risk_aversion * p_volatility_sq)
    return objective


def optimize_max_return(etf_codes: List[str],
                          session: Optional[Session] = None,
                          risk_aversion: float = RISK_AVERSION_DEFAULT,
                          period: Optional[str] = None) -> OptimizationResult:
    """
    优化求解最大收益组合

    参数:
        etf_codes: 可选ETF代码列表
        session: 数据库会话
        risk_aversion: 风险厌恶系数（0表示纯最大收益）
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'（可选）

    返回:
        OptimizationResult: 优化结果
    """
    close_session = False
    if session is None:
        session = get_session().__enter__()
        close_session = True

    days = period_to_days(period)

    try:
        if len(etf_codes) == 0:
            return OptimizationResult(
                success=False,
                weights={},
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                message="没有提供ETF代码"
            )

        if len(etf_codes) == 1:
            return OptimizationResult(
                success=True,
                weights={etf_codes[0]: 1.0},
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                message="只有一只ETF，权重为100%"
            )

        navs_list = []
        valid_codes = []
        for code in etf_codes:
            navs = get_etf_nav_series(session, code, days)
            if len(navs) >= 30:
                navs_list.append(navs)
                valid_codes.append(code)

        if len(valid_codes) < 2:
            if len(valid_codes) == 1:
                return OptimizationResult(
                    success=True,
                    weights={valid_codes[0]: 1.0},
                    expected_return=0.0,
                    volatility=0.0,
                    sharpe_ratio=0.0,
                    message="只有一只ETF有足够数据，权重为100%"
                )
            return OptimizationResult(
                success=False,
                weights={},
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                message="没有足够的ETF数据用于优化"
            )

        min_len = min(len(navs) for navs in navs_list)
        aligned_navs = [navs[-min_len:] for navs in navs_list]

        returns_list = [calculate_returns_from_nav(navs) for navs in aligned_navs]

        annual_returns = []
        for i, returns in enumerate(returns_list):
            if len(returns) >= 2:
                total_ret = aligned_navs[i][-1] / aligned_navs[i][0] - 1
                ann_ret = calculate_annualized_return(total_ret, len(returns))
                annual_returns.append(ann_ret)
            else:
                annual_returns.append(0.0)

        cov_matrix = calculate_covariance_matrix(returns_list)

        n = len(valid_codes)
        initial_weights = np.ones(n) / n

        bounds = [(0, 1) for _ in range(n)]

        constraints = {
            'type': 'eq',
            'fun': lambda w: np.sum(w) - 1
        }

        result = minimize(
            maximize_return_objective,
            initial_weights,
            args=(np.array(annual_returns), cov_matrix, risk_aversion),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )

        if not result.success:
            return OptimizationResult(
                success=False,
                weights={},
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                message=f"优化失败: {result.message}"
            )

        optimal_weights = result.x
        optimal_weights = np.maximum(optimal_weights, 0)
        optimal_weights = optimal_weights / np.sum(optimal_weights)

        weights_dict = {
            valid_codes[i]: float(optimal_weights[i])
            for i in range(len(valid_codes))
        }

        weights_dict = {k: v for k, v in weights_dict.items() if v > 1e-6}

        expected_return = portfolio_return(optimal_weights, np.array(annual_returns))
        volatility = portfolio_volatility(optimal_weights, cov_matrix)
        sharpe = calculate_sharpe_ratio(expected_return, volatility)

        return OptimizationResult(
            success=True,
            weights=weights_dict,
            expected_return=expected_return * 100,
            volatility=volatility * 100,
            sharpe_ratio=sharpe,
            message="优化成功"
        )

    except Exception as e:
        logger.error(f"优化过程出错: {e}")
        return OptimizationResult(
            success=False,
            weights={},
            expected_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            message=f"优化出错: {str(e)}"
        )
    finally:
        if close_session:
            session.close()


def optimize_with_constraints(etf_codes: List[str],
                                max_weight: Optional[float] = None,
                                target_volatility: Optional[float] = None,
                                session: Optional[Session] = None,
                                period: Optional[str] = None) -> OptimizationResult:
    """
    带约束的最大收益优化

    参数:
        etf_codes: 可选ETF代码列表
        max_weight: 单个ETF最大权重（可选）
        target_volatility: 目标波动率上限（可选）
        session: 数据库会话
        period: 时间区段字符串，如 '1m', '3m', '6m', '1y', '2y', '3y', '5y'（可选）

    返回:
        OptimizationResult: 优化结果
    """
    close_session = False
    if session is None:
        session = get_session().__enter__()
        close_session = True

    days = period_to_days(period)

    try:
        if len(etf_codes) == 0:
            return OptimizationResult(
                success=False,
                weights={},
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                message="没有提供ETF代码"
            )

        if len(etf_codes) == 1:
            return OptimizationResult(
                success=True,
                weights={etf_codes[0]: 1.0},
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                message="只有一只ETF，权重为100%"
            )

        navs_list = []
        valid_codes = []
        for code in etf_codes:
            navs = get_etf_nav_series(session, code, days)
            if len(navs) >= 30:
                navs_list.append(navs)
                valid_codes.append(code)

        if len(valid_codes) < 2:
            return OptimizationResult(
                success=False,
                weights={},
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                message="没有足够的ETF数据用于优化"
            )

        min_len = min(len(navs) for navs in navs_list)
        aligned_navs = [navs[-min_len:] for navs in navs_list]

        returns_list = [calculate_returns_from_nav(navs) for navs in aligned_navs]

        annual_returns = []
        for i, returns in enumerate(returns_list):
            if len(returns) >= 2:
                total_ret = aligned_navs[i][-1] / aligned_navs[i][0] - 1
                ann_ret = calculate_annualized_return(total_ret, len(returns))
                annual_returns.append(ann_ret)
            else:
                annual_returns.append(0.0)

        cov_matrix = calculate_covariance_matrix(returns_list)

        n = len(valid_codes)
        initial_weights = np.ones(n) / n

        bounds = [(0, max_weight) for _ in range(n)] if max_weight else [(0, 1) for _ in range(n)]

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]

        if target_volatility:
            constraints.append({
                'type': 'ineq',
                'fun': lambda w: target_volatility - portfolio_volatility(w, cov_matrix)
            })

        result = minimize(
            maximize_return_objective,
            initial_weights,
            args=(np.array(annual_returns), cov_matrix, 0.0),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )

        if not result.success:
            return OptimizationResult(
                success=False,
                weights={},
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                message=f"优化失败: {result.message}"
            )

        optimal_weights = result.x
        optimal_weights = np.maximum(optimal_weights, 0)
        optimal_weights = optimal_weights / np.sum(optimal_weights)

        weights_dict = {
            valid_codes[i]: float(optimal_weights[i])
            for i in range(len(valid_codes))
        }

        weights_dict = {k: v for k, v in weights_dict.items() if v > 1e-6}

        expected_return = portfolio_return(optimal_weights, np.array(annual_returns))
        volatility = portfolio_volatility(optimal_weights, cov_matrix)
        sharpe = calculate_sharpe_ratio(expected_return, volatility)

        return OptimizationResult(
            success=True,
            weights=weights_dict,
            expected_return=expected_return * 100,
            volatility=volatility * 100,
            sharpe_ratio=sharpe,
            message="优化成功"
        )

    except Exception as e:
        logger.error(f"优化过程出错: {e}")
        return OptimizationResult(
            success=False,
            weights={},
            expected_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            message=f"优化出错: {str(e)}"
        )
    finally:
        if close_session:
            session.close()


if __name__ == "__main__":
    print("组合优化服务模块测试...")
    with get_session() as session:
        result = optimize_max_return(["510300", "510500"])
        print(f"优化成功: {result.success}")
        print(f"最优权重: {result.weights}")
        print(f"预期收益: {result.expected_return:.2f}%")
        print(f"夏普比率: {result.sharpe_ratio:.4f}")