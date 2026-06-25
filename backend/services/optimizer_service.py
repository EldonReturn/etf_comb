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
    get_annual_factor,
    period_to_days,
    check_etf_dates_aligned
)

logger = logging.getLogger(__name__)

RISK_AVERSION_DEFAULT = 0.0
# 优化器输入上限：超过此数量的 ETF 会触发相关性自动去重
MAX_ETF_COUNT_BEFORE_DEDUP = 15
# 最小非零权重阈值：最终结果中权重低于此值的 ETF 将被剔除
MIN_WEIGHT_THRESHOLD = 0.02
# 相关性去重阈值：相关系数超过此值的 ETF 视为跟踪同一底层资产
RHO_DEDUP_THRESHOLD = 0.95


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
    - max_drawdown: 组合最大回撤(%)，负值如 -12.5 表示 -12.5%
    - iterations: 罚项优化的迭代次数
    """
    success: bool
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    message: str
    max_drawdown: float = 0.0
    iterations: int = 0


def ledoit_wolf_shrinkage(returns_matrix: np.ndarray) -> np.ndarray:
    """
    Ledoit-Wolf 收缩协方差估计（2004）

    将样本协方差向对角矩阵（常数相关性模型）收缩，减少估计误差。
    收缩强度 δ 通过解析公式自动计算，无需调参。

    理论背景：
    - 样本协方差在高 N/p 比值下估计误差大
    - Ledoit-Wolf 是最优线性收缩估计器（在 Frobenius 范数下渐近最优）
    - Σ_shrunk = (1-δ) × Σ_sample + δ × Σ_target

    参数:
        returns_matrix: T×N 收益率矩阵，行=时间，列=资产（已去均值）

    返回:
        np.ndarray: N×N 收缩协方差矩阵（正定）

    参考:
        Ledoit, O., & Wolf, M. (2004). "A well-conditioned estimator for
        large-dimensional covariance matrices."
        Journal of Multivariate Analysis, 88(2), 365-411.
    """
    T, N = returns_matrix.shape

    if T < 2 or N < 2:
        return np.cov(returns_matrix, rowvar=False)

    # 样本协方差矩阵
    S = np.cov(returns_matrix, rowvar=False)

    # 收缩目标：对角矩阵，对角线为样本协方差的均值
    mu = np.trace(S) / N
    F_target = mu * np.eye(N)

    # --- 计算 π̂（样本协方差矩阵所有元素的方差之和）---
    # π̂ = Σ_{i=1}^N Σ_{j=1}^N asy.var[√T × s_{ij}]
    # 实现：对每个 (i,j) 对，计算 z_{t,ij} = (x_{ti} - x̄_i)(x_{tj} - x̄_j) - s_{ij}
    # 然后 π̂ = (1/T) Σ_{i,j} Σ_{t} z_{t,ij}² × T/(T-1) 的简化近似

    # 使用 Ledoit-Wolf (2004) 简化公式
    X_centered = returns_matrix - returns_matrix.mean(axis=0)

    # π̂ 计算：样本协方差元素的方差之和
    # 简化: pi = sum_{i,j} var(sqrt(T) * s_{ij})
    pi_mat = np.zeros((N, N))
    for t in range(T):
        outer_t = np.outer(X_centered[t], X_centered[t])
        pi_mat += (outer_t - S) ** 2
    pi_hat = np.sum(pi_mat) / T * (T / (T - 1)) if T > 1 else 0.0

    # --- 计算 ρ̂（对角线元素之间的协方差）---
    # ρ̂ = Σ_{i≠j} asy.cov[√T × s_{ii}, √T × s_{jj}]
    # 简化: 对角线元素方差之和
    # 移除对角线的 π̂ 贡献，只保留对角线间的协方差部分

    # 对角线部分的方差贡献
    diag_vars = np.zeros(N)
    s_diag = np.diag(S)
    for i in range(N):
        diag_vars[i] = np.mean(
            ((X_centered[:, i] ** 2 - s_diag[i]) ** 2)
        ) * T / (T - 1) if T > 1 else 0.0

    # ρ̂ 近似为对角线方差之和（非对角线贡献很小）
    # 更精确的近似：r̂ = sum_i var(s_{ii}) - (去除交叉项的方差)
    # 参考 Ledoit-Wolf (2004) 公式 (4) 和 (5)
    theta_sum = np.sum(diag_vars)

    # 非对角线部分
    off_diag_sum = 0.0
    for i in range(N):
        for j in range(N):
            if i != j:
                theta_ij = np.mean(
                    (X_centered[:, i] * X_centered[:, j] - S[i, j]) ** 2
                ) * T / (T - 1) if T > 1 else 0.0
                off_diag_sum += theta_ij

    pi_hat_2 = theta_sum + off_diag_sum

    # ρ̂：对角元素之间的渐进协方差之和
    # 简化：rho = sum_{i=1}^N var(s_{ii}) + sum_{i,j' where i != j and i' == j'} cov(...)
    # 实际上 ρ̂ 近似为 pi_hat 中对角线部分 + 交叉项校正
    rho_hat = 0.0
    for i in range(N):
        for j in range(N):
            if i != j:
                theta_ii_jj = np.mean(
                    (X_centered[:, i] * X_centered[:, j] - S[i, j]) ** 2
                ) * T / (T - 1) if T > 1 else 0.0
                rho_hat += theta_ii_jj * T / (T - 1) if T > 1 else 0.0

    # γ̂ = ||F - S||²_F（收缩目标与样本协方差的差异）
    gamma_hat = np.sum((F_target - S) ** 2)

    if gamma_hat < 1e-12:
        return S

    # κ̂ = (π̂ - ρ̂) / γ̂
    kappa_hat = (pi_hat_2 - rho_hat) / gamma_hat

    # δ̂ = max(0, min(1, κ̂ / T))
    delta = max(0.0, min(1.0, kappa_hat / T))

    return (1.0 - delta) * S + delta * F_target


def auto_dedup_by_correlation(
    navs_list: List[List[float]],
    etf_codes: List[str],
    rho_threshold: float = 0.95
) -> List[str]:
    """
    基于净值相关性自动去重 ETF。

    核心思想：跟踪同一指数的 ETF 净值走势高度相关（ρ > 0.95），
    无需数据库字段即可自动发现并合并。

    算法：
    1. 从净值序列计算对数收益率，过滤 NaN 和过短序列（< 30 个有效值）
    2. 对齐所有序列到共同长度
    3. 计算 N×N 相关系数矩阵
    4. 贪婪聚类：ρ > rho_threshold 的归为同一簇
    5. 每簇保留夏普比率最优的 ETF

    参数:
        navs_list: 净值序列列表（每个元素是一个 ETF 的净值序列）
        etf_codes: ETF 代码列表（与 navs_list 一一对应）
        rho_threshold: 相关性阈值，默认 0.95

    返回:
        List[str]: 去重后的 ETF 代码列表
    """
    if not navs_list or not etf_codes:
        return []

    if len(navs_list) == 1:
        return list(etf_codes)

    # Step 1: 计算对数收益率，过滤无效序列
    log_returns = []
    valid_indices = []
    for i, navs in enumerate(navs_list):
        nav_arr = np.array(navs, dtype=float)
        # 过滤 NaN 和零值
        nav_arr = nav_arr[~np.isnan(nav_arr)]
        nav_arr = nav_arr[nav_arr > 1e-12]
        if len(nav_arr) < 31:  # 至少需要 30 个收益率点
            continue
        r = np.diff(np.log(nav_arr))
        r = r[~np.isnan(r)]
        if len(r) >= 30:
            log_returns.append(r)
            valid_indices.append(i)

    if len(log_returns) < 2:
        if valid_indices:
            return [etf_codes[valid_indices[0]]]
        return []

    # Step 2: 对齐到共同长度
    min_len = min(len(r) for r in log_returns)
    aligned = np.array([r[-min_len:] for r in log_returns])

    # Step 3: 计算相关系数矩阵
    corr = np.corrcoef(aligned)
    n = len(log_returns)

    # Step 4: 简单夏普比率（用于择优）
    def _quick_sharpe(returns):
        if len(returns) < 2:
            return -float('inf')
        mean_ret = np.mean(returns)
        std_ret = np.std(returns, ddof=1)
        if std_ret < 1e-12:
            return 0.0
        return float(mean_ret / std_ret)

    # Step 5: 贪婪聚类
    clusters = []
    visited = [False] * n

    for i in range(n):
        if visited[i]:
            continue
        # 找到所有与 i 高度相关的 ETF
        cluster = [i]
        visited[i] = True
        for j in range(n):
            if not visited[j] and not np.isnan(corr[i][j]) and corr[i][j] > rho_threshold:
                cluster.append(j)
                visited[j] = True
        clusters.append(cluster)

    # Step 6: 每簇保留夏普最优
    kept = []
    for cluster in clusters:
        if len(cluster) == 1:
            idx = cluster[0]
        else:
            idx = max(cluster, key=lambda k: _quick_sharpe(log_returns[k]))
        kept.append(etf_codes[valid_indices[idx]])

    return kept


def calculate_covariance_matrix(returns_list: List[List[float]]) -> np.ndarray:
    """
    计算收益率序列的协方差矩阵（Ledoit-Wolf 收缩估计）

    使用 Ledoit-Wolf (2004) 收缩估计替代传统样本协方差。
    在高 N/p 比值（ETF 数量多 / 回看天数少）场景下，收缩估计
    比样本协方差更稳定、更可靠。

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

    if len(returns_list) == 1:
        # 单资产：直接计算方差
        r = np.array(returns_list[0])
        r = r[~np.isnan(r)]
        if len(r) < 2:
            return np.zeros((1, 1))
        return np.array([[np.var(r, ddof=1)]])

    min_len = min(len(r) for r in returns_list)
    aligned_returns = np.array([r[-min_len:] for r in returns_list])
    aligned_returns = aligned_returns[:, ~np.isnan(aligned_returns).any(axis=0)]

    if aligned_returns.shape[1] < 2:
        n = len(returns_list)
        return np.zeros((n, n))

    # Ledoit-Wolf 收缩估计：输入为 T×N（行=时间，列=资产）
    # aligned_returns 为 N×T，需转置
    cov_matrix = ledoit_wolf_shrinkage(aligned_returns.T)

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


def portfolio_cdar(weights: np.ndarray, aligned_navs: List[List[float]], alpha: float = 0.05) -> float:
    """
    计算组合条件回撤 (CDaR / Conditional Drawdown at Risk)

    CDaR 是最大回撤的平滑近似，取最差 alpha% 回撤的平均值。
    比 max_drawdown 更平滑，对权重微小变化不敏感。

    参数:
        weights: 权重数组
        aligned_navs: 对齐后的净值序列列表
        alpha: 取最差的 alpha 比例计算 CDaR（默认 0.05，即 5%）

    返回:
        float: CDaR 值（负值，如 -0.08 表示平均最差 8% 回撤）
    """
    if not aligned_navs or len(weights) == 0:
        return 0.0

    n = len(aligned_navs)
    min_len = len(aligned_navs[0])

    portfolio_navs = []
    for i in range(min_len):
        nav = sum(aligned_navs[j][i] * weights[j] for j in range(n))
        portfolio_navs.append(nav)

    if len(portfolio_navs) < 2:
        return 0.0

    rolling_max = np.maximum.accumulate(portfolio_navs)
    drawdowns = (np.array(portfolio_navs) - rolling_max) / rolling_max

    worst_n = max(1, int(len(drawdowns) * alpha))
    sorted_drawdowns = np.sort(drawdowns)
    cdar = float(np.mean(sorted_drawdowns[:worst_n]))
    return cdar


def portfolio_max_drawdown(weights: np.ndarray, aligned_navs: List[List[float]]) -> float:
    """
    计算组合最大回撤

    参数:
        weights: 权重数组
        aligned_navs: 对齐后的净值序列列表

    返回:
        float: 最大回撤值（负值，如 -0.15 表示 -15%）
    """
    if not aligned_navs or len(weights) == 0:
        return 0.0

    n = len(aligned_navs)
    min_len = len(aligned_navs[0])

    portfolio_navs = []
    for i in range(min_len):
        nav = sum(aligned_navs[j][i] * weights[j] for j in range(n))
        portfolio_navs.append(nav)

    if len(portfolio_navs) < 2:
        return 0.0

    rolling_max = np.maximum.accumulate(portfolio_navs)
    drawdowns = (np.array(portfolio_navs) - rolling_max) / rolling_max
    return float(np.min(drawdowns))


def portfolio_hhi(weights: np.ndarray) -> float:
    """
    计算组合权重的 Herfindahl-Hirschman 指数（集中度指标）

    HHI = Σ(wᵢ²)，取值范围 [1/n, 1]。
    - 等权组合的 HHI = 1/n（n 为资产数量）
    - 完全集中单资产的 HHI = 1

    参数:
        weights: 权重数组

    返回:
        float: HHI 值
    """
    return float(np.sum(weights ** 2))


def maximize_return_objective(weights: np.ndarray, returns: np.ndarray,
                               cov_matrix: np.ndarray, risk_aversion: float,
                               annual_factor: int = 252) -> float:
    """
    最大收益优化目标函数

    目标 = Σ(wᵢ × rᵢ) - λ × ΣΣ(wᵢ × wⱼ × σᵢⱼ)

    当risk_aversion=0时，只最大化收益。

    参数:
        weights: 权重数组
        returns: 各ETF年化收益率数组
        cov_matrix: 协方差矩阵（已按日收益率计算）
        risk_aversion: 风险厌恶系数
        annual_factor: 年化因子（默认252），根据统计时间范围确定

    返回:
        float: 目标函数值（最小化）
    """
    p_return = portfolio_return(weights, returns)
    p_volatility_sq = np.dot(weights.T, np.dot(cov_matrix, weights)) * annual_factor

    objective = -(p_return - risk_aversion * p_volatility_sq)
    return objective


def drawdown_penalty_objective(weights: np.ndarray, returns: np.ndarray,
                               cov_matrix: np.ndarray, risk_aversion: float,
                               annual_factor: int, aligned_navs: List[List[float]],
                               gamma: float, target_mdd: float,
                               alpha: float = 0.05,
                               hhi_target: Optional[float] = None,
                               gamma_hhi: float = 2.0) -> float:
    """
    带回撤罚项和集中度罚项的优化目标函数

    目标 = -(Σwᵢ × rᵢ) + λ × ΣΣ(wᵢ × wⱼ × σᵢⱼ)
         + γ × max(0, |CDaR(w, α)| - target)²
         + γ_hhi × max(0, HHI(w) - hhi_target)²

    当 CDaR <= target 时，回撤罚项为 0（约束满足）。
    当 CDaR > target 时，罚项以二次方增长。
    HHI 集中度罚项同理，防止权重过度集中于单一资产。

    参数:
        weights: 权重数组
        returns: 各ETF年化收益率数组
        cov_matrix: 协方差矩阵（已按日收益率计算）
        risk_aversion: 风险厌恶系数
        annual_factor: 年化因子
        aligned_navs: 对齐后的净值序列列表
        gamma: 回撤惩罚系数
        target_mdd: 目标最大回撤上限（小数形式，如 0.15 表示 15%）
        alpha: CDaR 尾部比例（默认 0.05）。越小越接近真实最大回撤
        hhi_target: HHI 集中度上限（默认 None 表示不限制）。0.5 约等于 2 个等权资产
        gamma_hhi: HHI 惩罚系数（默认 2.0）

    返回:
        float: 目标函数值（最小化）
    """
    base_obj = maximize_return_objective(weights, returns, cov_matrix, risk_aversion, annual_factor)

    cdar = portfolio_cdar(weights, aligned_navs, alpha=alpha)
    violation = max(0.0, abs(cdar) - target_mdd)
    penalty = gamma * violation ** 2

    if hhi_target is not None:
        hhi = portfolio_hhi(weights)
        hhi_violation = max(0.0, hhi - hhi_target)
        penalty += gamma_hhi * hhi_violation ** 2

    return base_obj + penalty


# ============================================================
# 优化器内部辅助函数（消除三个优化函数间的重复代码）
# ============================================================

def _load_and_dedup_navs(
    session: Session,
    etf_codes: List[str],
    days: int
) -> Tuple[List[List[float]], List[str]]:
    """
    加载 ETF 净值序列并按相关性自动去重。

    流程：
    1. 从数据库加载净值，过滤不足 30 个数据点的 ETF
    2. 若 ETF 数量超过 MAX_ETF_COUNT_BEFORE_DEDUP，自动按相关性聚类去重
    3. 每簇保留夏普比率最优的一只

    参数:
        session: 数据库会话
        etf_codes: 原始 ETF 代码列表
        days: 回看天数

    返回:
        (navs_list, valid_codes): 去重后的净值序列列表和对应代码列表
    """
    navs_list = []
    valid_codes = []
    for code in etf_codes:
        navs = get_etf_nav_series(session, code, days)
        if len(navs) >= 30:
            navs_list.append(navs)
            valid_codes.append(code)

    if len(valid_codes) > MAX_ETF_COUNT_BEFORE_DEDUP:
        deduped_codes = auto_dedup_by_correlation(
            navs_list, valid_codes, rho_threshold=RHO_DEDUP_THRESHOLD
        )
        if len(deduped_codes) < len(valid_codes):
            logger.info(
                f"优化前自动去重：{len(valid_codes)} → {len(deduped_codes)}，"
                f"移除 {len(valid_codes) - len(deduped_codes)} 只高相关 ETF"
            )
            deduped_set = set(deduped_codes)
            kept_indices = [i for i, c in enumerate(valid_codes) if c in deduped_set]
            navs_list = [navs_list[i] for i in kept_indices]
            valid_codes = [valid_codes[i] for i in kept_indices]

    return navs_list, valid_codes


def _compute_returns_and_cov(
    navs_list: List[List[float]]
) -> Tuple[List[List[float]], List[float], np.ndarray, int, int]:
    """
    从净值序列计算对齐后的收益率和协方差矩阵。

    流程：
    1. 对齐净值到共同长度，归一化为基期=1
    2. 计算日收益率序列
    3. 计算年化收益率
    4. 计算 Ledoit-Wolf 收缩协方差矩阵

    参数:
        navs_list: 净值序列列表（每个元素是一只 ETF 的净值序列）

    返回:
        (aligned_navs, annual_returns, cov_matrix, min_len, n):
        - aligned_navs: 对齐后的归一化净值序列 (n_etfs × min_len)
        - annual_returns: 年化收益率列表 (n_etfs,)
        - cov_matrix: 收缩协方差矩阵 (n_etfs × n_etfs)
        - min_len: 对齐后的共同长度
        - n: ETF 数量
    """
    min_len = min(len(navs) for navs in navs_list)
    aligned_navs = [[v / navs[0] for v in navs[-min_len:]] for navs in navs_list]

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
    n = len(navs_list)

    return aligned_navs, annual_returns, cov_matrix, min_len, n


def _build_trimmed_weights(
    codes: List[str],
    weights_vec: np.ndarray
) -> Dict[str, float]:
    """
    构建权重字典，剔除低于 MIN_WEIGHT_THRESHOLD 的微权重并重新归一化。

    参数:
        codes: ETF 代码列表
        weights_vec: 权重数组（与 codes 同长度）

    返回:
        归一化后的权重字典 {code: weight}
    """
    weights_dict = {codes[i]: float(weights_vec[i]) for i in range(len(codes))}
    n_before = len(weights_dict)
    weights_dict = {k: v for k, v in weights_dict.items() if v >= MIN_WEIGHT_THRESHOLD}
    if weights_dict and len(weights_dict) < n_before:
        total = sum(weights_dict.values())
        weights_dict = {k: v / total for k, v in weights_dict.items()}
        logger.info(
            f"最小权重剔除：{n_before} → {len(weights_dict)} 只 ETF"
            f"（阈值={MIN_WEIGHT_THRESHOLD:.0%}）"
        )
    return weights_dict


def _evaluate_portfolio(
    weights_vec: np.ndarray,
    aligned_navs: List[List[float]],
    min_len: int,
    n: int,
    annual_factor: int
) -> Tuple[float, float, float, float]:
    """
    计算组合表现指标。

    参数:
        weights_vec: 权重数组
        aligned_navs: 对齐后的归一化净值序列
        min_len: 共同长度
        n: ETF 数量
        annual_factor: 年化因子

    返回:
        (annual_return, volatility, sharpe, max_drawdown) — 全部为小数形式
    """
    portfolio_navs = [
        float(sum(aligned_navs[j][i] * weights_vec[j] for j in range(n)))
        for i in range(min_len)
    ]
    pf_returns = calculate_returns_from_nav(portfolio_navs)
    total_ret = (portfolio_navs[-1] - portfolio_navs[0]) / portfolio_navs[0]
    annual_return = calculate_annualized_return(total_ret, len(pf_returns))
    volatility = calculate_volatility(pf_returns, annual_factor)
    sharpe = calculate_sharpe_ratio(annual_return, volatility)
    max_dd = portfolio_max_drawdown(weights_vec, aligned_navs)
    return annual_return, volatility, sharpe, max_dd


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
    annual_factor = get_annual_factor(period)

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

        warning = check_etf_dates_aligned(session, etf_codes, days)
        if warning:
            return OptimizationResult(success=False, weights={}, expected_return=0.0, volatility=0.0, sharpe_ratio=0.0, message=warning)

        navs_list, valid_codes = _load_and_dedup_navs(session, etf_codes, days)

        if len(valid_codes) < 2:
            if len(valid_codes) == 1:
                return OptimizationResult(
                    success=True,
                    weights={valid_codes[0]: 1.0},
                    expected_return=0.0, volatility=0.0, sharpe_ratio=0.0,
                    message="只有一只ETF有足够数据，权重为100%"
                )
            return OptimizationResult(
                success=False, weights={}, expected_return=0.0,
                volatility=0.0, sharpe_ratio=0.0, message="没有足够的ETF数据用于优化"
            )

        aligned_navs, annual_returns, cov_matrix, min_len, n = _compute_returns_and_cov(navs_list)

        initial_weights = np.ones(n) / n

        bounds = [(0, 1) for _ in range(n)]
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}

        result = minimize(
            maximize_return_objective,
            initial_weights,
            args=(np.array(annual_returns), cov_matrix, risk_aversion, annual_factor),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )

        if not result.success:
            return OptimizationResult(
                success=False, weights={}, expected_return=0.0,
                volatility=0.0, sharpe_ratio=0.0, message=f"优化失败: {result.message}"
            )

        optimal_weights = result.x
        optimal_weights = np.maximum(optimal_weights, 0)
        optimal_weights = optimal_weights / np.sum(optimal_weights)

        weights_dict = _build_trimmed_weights(valid_codes, optimal_weights)
        annual_ret, volatility, sharpe, max_dd = _evaluate_portfolio(
            optimal_weights, aligned_navs, min_len, n, annual_factor
        )

        return OptimizationResult(
            success=True,
            weights=weights_dict,
            expected_return=annual_ret * 100,
            volatility=volatility * 100,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd * 100,
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
        if close_session and session is not None:
            session.close()


def optimize_with_drawdown_penalty(etf_codes: List[str],
                                     max_weight: Optional[float] = None,
                                     target_volatility: Optional[float] = None,
                                     target_max_drawdown: Optional[float] = None,
                                     session: Optional[Session] = None,
                                     period: Optional[str] = None) -> OptimizationResult:
    """
    带回撤罚项的最大收益优化（迭代升温法）

    使用二次罚项 + 迭代升温机制处理最大回撤约束。
    波动率和权重和仍作为 SLSQP 硬约束。

    参数:
        etf_codes: 可选ETF代码列表
        max_weight: 单个ETF最大权重（可选）
        target_volatility: 目标波动率上限（小数形式，可选）
        target_max_drawdown: 目标最大回撤上限（小数形式，如 0.15 表示 15%）
        session: 数据库会话
        period: 时间区段字符串

    返回:
        OptimizationResult: 优化结果
    """
    close_session = False
    if session is None:
        session = get_session().__enter__()
        close_session = True

    days = period_to_days(period)
    annual_factor = get_annual_factor(period)

    try:
        if len(etf_codes) == 0:
            return OptimizationResult(
                success=False, weights={}, expected_return=0.0,
                volatility=0.0, sharpe_ratio=0.0, message="没有提供ETF代码",
                max_drawdown=0.0, iterations=0
            )

        if len(etf_codes) == 1:
            return OptimizationResult(
                success=True, weights={etf_codes[0]: 1.0}, expected_return=0.0,
                volatility=0.0, sharpe_ratio=0.0, message="只有一只ETF，权重为100%",
                max_drawdown=0.0, iterations=0
            )

        warning = check_etf_dates_aligned(session, etf_codes, days)
        if warning:
            return OptimizationResult(success=False, weights={}, expected_return=0.0, volatility=0.0, sharpe_ratio=0.0, message=warning, max_drawdown=0.0, iterations=0)

        navs_list, valid_codes = _load_and_dedup_navs(session, etf_codes, days)

        if len(valid_codes) < 2:
            return OptimizationResult(
                success=False, weights={}, expected_return=0.0,
                volatility=0.0, sharpe_ratio=0.0, message="没有足够的ETF数据用于优化",
                max_drawdown=0.0, iterations=0
            )

        aligned_navs, annual_returns, cov_matrix, min_len, n = _compute_returns_and_cov(navs_list)
        initial_weights = np.ones(n) / n

        bounds = [(0, max_weight) for _ in range(n)] if max_weight is not None else [(0, 1) for _ in range(n)]

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]

        if target_volatility:
            constraints.append({
                'type': 'ineq',
                'fun': lambda w: target_volatility - portfolio_volatility(w, cov_matrix) * np.sqrt(annual_factor)
            })

        gamma = 0.5
        best_result = None
        best_mdd_violation = float('inf')
        optimal_weights = None
        result_iterations = 0

        for iteration in range(1, 7):
            result_iterations = iteration
            current_weights = initial_weights if iteration == 1 else optimal_weights

            # 动态缩小 alpha：前几轮用较大的 alpha 保证光滑性，后几轮缩小使 CDaR 逐步逼近真实最大回撤
            alpha = max(0.01, 0.05 / iteration) if target_max_drawdown is not None else 0.05
            # HHI 集中度上限：0.5 约等于 2 个等权资产，防止权重过度集中于单一 ETF
            hhi_target = 0.5 if n >= 3 else 1.0 / n

            if target_max_drawdown is not None:
                def obj_with_penalty(w):
                    return drawdown_penalty_objective(
                        w, np.array(annual_returns), cov_matrix, 0.0, annual_factor,
                        aligned_navs, gamma, target_max_drawdown,
                        alpha=alpha, hhi_target=hhi_target, gamma_hhi=2.0
                    )
            else:
                obj_with_penalty = lambda w: maximize_return_objective(
                    w, np.array(annual_returns), cov_matrix, 0.0, annual_factor
                )

            result = minimize(
                obj_with_penalty,
                current_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-9}
            )

            if result.success:
                opt_w = np.maximum(result.x, 0)
                opt_w = opt_w / np.sum(opt_w)
                actual_mdd = portfolio_max_drawdown(opt_w, aligned_navs)

                if target_max_drawdown is not None and abs(actual_mdd) <= target_max_drawdown * 1.01:
                    mdd_pct = actual_mdd * 100
                    annual_ret, vol, sharpe, _ = _evaluate_portfolio(
                        opt_w, aligned_navs, min_len, n, annual_factor
                    )
                    weights_dict = _build_trimmed_weights(valid_codes, opt_w)

                    return OptimizationResult(
                        success=True, weights=weights_dict,
                        expected_return=annual_ret * 100, volatility=vol * 100,
                        sharpe_ratio=sharpe, message="优化成功",
                        max_drawdown=mdd_pct, iterations=result_iterations
                    )

                cdar_val = portfolio_cdar(opt_w, aligned_navs, alpha=alpha)
                tdd = target_max_drawdown or 0.0
                violation = max(0.0, abs(cdar_val) - tdd)
                if violation < best_mdd_violation:
                    best_mdd_violation = violation
                    best_result = opt_w

                if iteration < 6:
                    gamma *= 2
                    optimal_weights = opt_w
            else:
                if iteration < 6:
                    gamma *= 2
                    if optimal_weights is None:
                        optimal_weights = np.ones(n) / n

        if best_result is not None:
            opt_w = np.maximum(best_result, 0)
            opt_w = opt_w / np.sum(opt_w)
            actual_mdd = portfolio_max_drawdown(opt_w, aligned_navs)
            mdd_pct = actual_mdd * 100
            annual_ret, vol, sharpe, _ = _evaluate_portfolio(
                opt_w, aligned_navs, min_len, n, annual_factor
            )
            weights_dict = _build_trimmed_weights(valid_codes, opt_w)

            return OptimizationResult(
                success=True, weights=weights_dict,
                expected_return=annual_ret * 100, volatility=vol * 100,
                sharpe_ratio=sharpe,
                message=f"优化完成，回撤约束未能完全满足（{mdd_pct:.2f}%）",
                max_drawdown=mdd_pct, iterations=result_iterations
            )

        return OptimizationResult(
            success=False, weights={}, expected_return=0.0,
            volatility=0.0, sharpe_ratio=0.0,
            message="优化失败：无法找到可行解",
            max_drawdown=0.0, iterations=result_iterations
        )

    except Exception as e:
        logger.error(f"回撤罚项优化过程出错: {e}")
        return OptimizationResult(
            success=False, weights={}, expected_return=0.0,
            volatility=0.0, sharpe_ratio=0.0, message=f"优化出错: {str(e)}",
            max_drawdown=0.0, iterations=0
        )
    finally:
        if close_session and session is not None:
            session.close()


def optimize_with_constraints(etf_codes: List[str],
                                max_weight: Optional[float] = None,
                                target_volatility: Optional[float] = None,
                                target_max_drawdown: Optional[float] = None,
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
    annual_factor = get_annual_factor(period)

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

        warning = check_etf_dates_aligned(session, etf_codes, days)
        if warning:
            return OptimizationResult(success=False, weights={}, expected_return=0.0, volatility=0.0, sharpe_ratio=0.0, message=warning)

        # 带回撤约束时直接委托给带罚项的优化器，避免重复计算
        if target_max_drawdown:
            mdd_decimal = target_max_drawdown / 100.0
            return optimize_with_drawdown_penalty(
                etf_codes=etf_codes,
                max_weight=max_weight,
                target_volatility=target_volatility,
                target_max_drawdown=mdd_decimal,
                session=session,
                period=period,
            )

        navs_list, valid_codes = _load_and_dedup_navs(session, etf_codes, days)

        if len(valid_codes) < 2:
            return OptimizationResult(
                success=False, weights={}, expected_return=0.0,
                volatility=0.0, sharpe_ratio=0.0, message="没有足够的ETF数据用于优化"
            )

        aligned_navs, annual_returns, cov_matrix, min_len, n = _compute_returns_and_cov(navs_list)
        initial_weights = np.ones(n) / n

        bounds = [(0, max_weight) for _ in range(n)] if max_weight is not None else [(0, 1) for _ in range(n)]

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]

        if target_volatility:
            constraints.append({
                'type': 'ineq',
                'fun': lambda w: target_volatility - portfolio_volatility(w, cov_matrix) * np.sqrt(annual_factor)
            })

        result = minimize(
            maximize_return_objective,
            initial_weights,
            args=(np.array(annual_returns), cov_matrix, 0.0, annual_factor),
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

        weights_dict = _build_trimmed_weights(valid_codes, optimal_weights)
        annual_ret, volatility, sharpe, max_dd = _evaluate_portfolio(
            optimal_weights, aligned_navs, min_len, n, annual_factor
        )

        return OptimizationResult(
            success=True,
            weights=weights_dict,
            expected_return=annual_ret * 100,
            volatility=volatility * 100,
            sharpe_ratio=sharpe,
            message="优化成功",
            max_drawdown=max_dd * 100,
            iterations=0
        )

    except Exception as e:
        logger.error(f"优化过程出错: {e}")
        return OptimizationResult(
            success=False,
            weights={},
            expected_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            message=f"优化出错: {str(e)}",
            max_drawdown=0.0,
            iterations=0
        )
    finally:
        if close_session and session is not None:
            session.close()


if __name__ == "__main__":
    print("组合优化服务模块测试...")
    with get_session() as session:
        result = optimize_max_return(["510300", "510500"])
        print(f"优化成功: {result.success}")
        print(f"最优权重: {result.weights}")
        print(f"预期收益: {result.expected_return:.2f}%")
        print(f"夏普比率: {result.sharpe_ratio:.4f}")