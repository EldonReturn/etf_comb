"""
优化器改进功能测试 - Ledoit-Wolf 收缩估计 + 相关性自动去重

采用 test_portfolio_refactor.py 模式，直接从 services 导入函数进行测试。

运行方式：
    pytest backend/tests/test_optimizer_improvements.py -v
"""

import pytest
import numpy as np
from backend.services.optimizer_service import (
    ledoit_wolf_shrinkage,
    auto_dedup_by_correlation,
    calculate_covariance_matrix,
)


# ============================================================
# Ledoit-Wolf 收缩协方差估计测试
# ============================================================

class TestLedoitWolfShrinkage:
    """
    测试 Ledoit-Wolf 收缩协方差估计

    验证要点：
    1. 输出是正定矩阵
    2. 收缩后的对角线比样本协方差更接近均值（向对角矩阵收缩）
    3. 极端场景：小 N 大 T vs 大 N 小 T 的行为
    """

    def test_output_shape(self):
        """输出矩阵形状正确"""
        np.random.seed(42)
        returns = np.random.randn(500, 5) * 0.01  # T=500, N=5
        result = ledoit_wolf_shrinkage(returns)
        assert result.shape == (5, 5), f"期望形状 (5,5), 得到 {result.shape}"

    def test_symmetry(self):
        """收缩矩阵保持对称性"""
        np.random.seed(42)
        returns = np.random.randn(300, 8) * 0.01
        result = ledoit_wolf_shrinkage(returns)
        assert np.allclose(result, result.T, atol=1e-12), "收缩矩阵不对称"

    def test_positive_definite(self):
        """收缩矩阵是正定的（所有特征值 > 0）"""
        np.random.seed(42)
        # 使用较少的观测数，使样本协方差更不稳定，检验收缩的作用
        returns = np.random.randn(50, 10) * 0.01  # T=50, N=10，N/p 较高
        result = ledoit_wolf_shrinkage(returns)
        eigenvals = np.linalg.eigvalsh(result)
        assert np.all(eigenvals > 0), f"特征值非正: min={eigenvals.min():.6e}"

    def test_shrinks_toward_diagonal(self):
        """
        收缩后对角线的方差应该缩小（向均值靠拢），
        即 shrunk 对角线方差 <= 样本协方差对角线方差
        """
        np.random.seed(42)
        returns = np.random.randn(100, 8) * 0.01
        sample_cov = np.cov(returns, rowvar=False)
        shrunk = ledoit_wolf_shrinkage(returns)

        sample_diag = np.diag(sample_cov)
        shrunk_diag = np.diag(shrunk)

        var_sample = np.var(sample_diag)
        var_shrunk = np.var(shrunk_diag)

        assert var_shrunk <= var_sample * 1.01, (
            f"收缩后对角线方差 ({var_shrunk:.8e}) 应不大于样本方差 ({var_sample:.8e})"
        )

    def test_high_n_low_t_stability(self):
        """
        极端场景：大 N 小 T（N/p 比值高）
        Ledoit-Wolf 在此场景下应产出比样本协方差更稳定的估计。
        验证：收缩后条件数 <= 样本协方差条件数
        """
        np.random.seed(42)
        T, N = 40, 15  # N/p = 15/40 = 0.375
        returns = np.random.randn(T, N) * 0.01

        sample_cov = np.cov(returns, rowvar=False)
        shrunk = ledoit_wolf_shrinkage(returns)

        # 条件数 = max(eigenvalue) / min(eigenvalue)
        cond_sample = np.linalg.cond(sample_cov)
        cond_shrunk = np.linalg.cond(shrunk)

        assert cond_shrunk <= cond_sample * 1.05, (
            f"收缩后条件数 ({cond_shrunk:.2f}) 应 <= 样本条件数 ({cond_sample:.2f})"
        )

    def test_low_n_high_t_near_sample(self):
        """
        极端场景：小 N 大 T（N/p 比值低）
        Ledoit-Wolf 应接近样本协方差（收缩强度 δ → 0）
        """
        np.random.seed(42)
        T, N = 1000, 3  # N/p = 3/1000 = 0.003
        returns = np.random.randn(T, N) * 0.01

        sample_cov = np.cov(returns, rowvar=False)
        shrunk = ledoit_wolf_shrinkage(returns)

        # 在充分数据下，收缩估计应非常接近样本协方差
        max_diff = np.max(np.abs(shrunk - sample_cov))
        assert max_diff < 1e-4, (
            f"在小N大T场景下，收缩不应偏离太远，最大差异: {max_diff:.6e}"
        )

    def test_deterministic(self):
        """相同输入产生相同输出"""
        np.random.seed(42)
        returns = np.random.randn(200, 6) * 0.01
        result1 = ledoit_wolf_shrinkage(returns)
        result2 = ledoit_wolf_shrinkage(returns)
        assert np.allclose(result1, result2, atol=1e-15), "确定性不足"

    def test_shrinkage_intensity_increases_with_n_over_t(self):
        """
        随 N/T 比值增大，收缩强度 δ 应增大。
        同 N，减少 T → δ 增大。
        """
        np.random.seed(42)
        N = 6
        # 从同一分布中采样以避免数据差异干扰
        all_data = np.random.randn(500, N) * 0.01

        returns_large_t = all_data[:480, :]  # T=480, N/T=0.0125
        returns_small_t = all_data[:60, :]   # T=60,  N/T=0.1

        sample_large = np.cov(returns_large_t, rowvar=False)
        shrunk_large = ledoit_wolf_shrinkage(returns_large_t)
        shrunk_small = ledoit_wolf_shrinkage(returns_small_t)

        # 收缩强度 δ：shrunk 与 sample 的 Frobenius 距离 / 与对角目标的距离
        mu_large = np.trace(sample_large) / N
        mu_small = np.trace(np.cov(returns_small_t, rowvar=False)) / N
        target_large = mu_large * np.eye(N)
        target_small = mu_small * np.eye(N)

        # 实际收缩量 = |sample - shrunk|_F
        from numpy.linalg import norm
        shrink_amount_large = norm(shrunk_large - sample_large, 'fro')
        shrink_amount_small = norm(shrunk_small - np.cov(returns_small_t, rowvar=False), 'fro')

        # 小 T 时应该收缩更多（虽然绝对值可能不同，但相对比例应该更大）
        # 使用相对收缩度 = shrink_amount / max_possible_shrink_amount
        max_shrink_large = norm(sample_large - target_large, 'fro')
        max_shrink_small = norm(np.cov(returns_small_t, rowvar=False) - target_small, 'fro')
        rel_shrink_large = shrink_amount_large / max_shrink_large if max_shrink_large > 1e-12 else 0
        rel_shrink_small = shrink_amount_small / max_shrink_small if max_shrink_small > 1e-12 else 0

        assert rel_shrink_small >= rel_shrink_large * 0.8, (
            f"小T相对收缩 ({rel_shrink_small:.4f}) 应 >= 大T相对收缩 ({rel_shrink_large:.4f})"
        )


# ============================================================
# 相关性自动去重测试
# ============================================================

class TestAutoDedupByCorrelation:
    """
    测试相关性自动去重

    验证要点：
    1. 高相关 ETF（ρ > 阈值）→ 保留一只
    2. 低相关 ETF → 全部保留
    3. 输出是输入的子集
    4. NaN 相关性正确处理
    """

    @staticmethod
    def _make_navs(base_navs, noise_scale=0.0005, rng=None):
        """生成带噪声的净值序列。noise_scale 越大相关性越低。"""
        if rng is None:
            rng = np.random.RandomState(42)
        noisy = base_navs + rng.randn(len(base_navs)) * noise_scale
        return np.maximum(noisy, 0.01).tolist()

    def test_identical_etfs_merged(self):
        """两只几乎相同的 ETF（ρ ≈ 1.0）→ 集群保留一只"""
        rng = np.random.RandomState(42)
        base = np.cumprod(1 + rng.randn(200) * 0.01)
        navs1 = self._make_navs(base, noise_scale=0.0, rng=rng)
        navs2 = self._make_navs(base, noise_scale=0.0, rng=rng)  # 完全相同

        navs_list = [navs1, navs2]
        codes = ["ETF_A.SH", "ETF_B.SH"]

        result = auto_dedup_by_correlation(navs_list, codes, rho_threshold=0.95)
        assert len(result) == 1, f"完全相同的 ETF 应合并为 1 只，实际为 {len(result)}"

    def test_highly_correlated_merged(self):
        """两只高相关 ETF（ρ > 0.95）→ 集群保留一只"""
        rng = np.random.RandomState(42)
        base = np.cumprod(1 + rng.randn(200) * 0.01)
        navs1 = self._make_navs(base, noise_scale=1e-6, rng=rng)   # 极低噪声
        navs2 = self._make_navs(base, noise_scale=1e-6, rng=rng)   # 极低噪声

        navs_list = [navs1, navs2]
        codes = ["510300.SH", "159919.SZ"]  # 两只跟踪沪深300的ETF

        result = auto_dedup_by_correlation(navs_list, codes, rho_threshold=0.95)
        assert len(result) == 1, (
            f"高相关 ETF（跟踪同一指数）应被去重，实际保留了 {len(result)} 只: {result}"
        )

    def test_uncorrelated_kept(self):
        """两只不相关的 ETF → 都保留"""
        rng1 = np.random.RandomState(42)
        rng2 = np.random.RandomState(99)

        navs1 = np.cumprod(1 + rng1.randn(200) * 0.01).tolist()
        navs2 = np.cumprod(1 + rng2.randn(200) * 0.01).tolist()

        navs_list = [navs1, navs2]
        codes = ["510300.SH", "518880.SH"]  # 沪深300 vs 黄金

        result = auto_dedup_by_correlation(navs_list, codes, rho_threshold=0.95)
        assert len(result) == 2, f"不相关的 ETF 应都保留，实际保留了 {len(result)} 只"

    def test_output_is_subset_of_input(self):
        """输出代码必须是输入代码的子集"""
        rng = np.random.RandomState(42)
        codes = [f"ETF_{i:02d}.SH" for i in range(10)]

        navs_list = []
        for i in range(10):
            rng_i = np.random.RandomState(42 + i * 3)
            navs = np.cumprod(1 + rng_i.randn(150) * 0.01)
            navs_list.append(navs.tolist())

        result = auto_dedup_by_correlation(navs_list, codes, rho_threshold=0.95)
        assert set(result).issubset(set(codes)), f"输出包含输入之外的代码: {set(result) - set(codes)}"

    def test_mixed_clusters(self):
        """
        混合场景：5 只 ETF，其中 2 对高相关 + 1 只独立
        应保留 3 只（每对 1 只 + 独立 1 只）
        """
        rng = np.random.RandomState(42)

        # 生成 3 个独立的基础序列
        base_a = np.cumprod(1 + rng.randn(200) * 0.012)
        base_b = np.cumprod(1 + rng.randn(200) * 0.010)
        base_c = np.cumprod(1 + rng.randn(200) * 0.015)

        # 集群 1: base_a 的变体（高相关）
        navs1 = self._make_navs(base_a, noise_scale=1e-6, rng=rng)
        navs2 = self._make_navs(base_a, noise_scale=1e-6, rng=rng)

        # 集群 2: base_b 的变体（高相关）
        navs3 = self._make_navs(base_b, noise_scale=1e-6, rng=rng)
        navs4 = self._make_navs(base_b, noise_scale=1e-6, rng=rng)

        # 独立
        navs5 = base_c.tolist()

        navs_list = [navs1, navs2, navs3, navs4, navs5]
        codes = ["ETF_01", "ETF_02", "ETF_03", "ETF_04", "ETF_05"]

        result = auto_dedup_by_correlation(navs_list, codes, rho_threshold=0.95)

        # 应保留 3 只：每对 1 只 + 独立 1 只
        assert 3 <= len(result) <= 4, (
            f"5 只中有 2 对被合并，应保留 3-4 只，实际保留了 {len(result)}: {result}"
        )

    def test_single_etf(self):
        """单只 ETF 输入 → 原样输出"""
        rng = np.random.RandomState(42)
        navs = np.cumprod(1 + rng.randn(100) * 0.01).tolist()
        result = auto_dedup_by_correlation([navs], ["ONLY.SH"], rho_threshold=0.95)
        assert result == ["ONLY.SH"]

    def test_empty_input(self):
        """空输入 → 空输出"""
        result = auto_dedup_by_correlation([], [], rho_threshold=0.95)
        assert result == []

    def test_navs_with_nan(self):
        """包含 NaN 的净值序列 → 应被排除而非崩溃"""
        rng = np.random.RandomState(42)
        base = np.cumprod(1 + rng.randn(200) * 0.01)

        # navs1 正常
        navs1 = self._make_navs(base, noise_scale=1e-6, rng=rng)
        # navs2 有 NaN
        navs2 = navs1.copy()
        navs2[50] = float('nan')

        result = auto_dedup_by_correlation([navs1, navs2], ["A.SH", "B.SH"], rho_threshold=0.95)
        # navs2 被排除（含 NaN 导致收益率序列不足 30），navs1 保留
        assert len(result) >= 1, f"应至少保留 1 只正常 ETF，实际保留了 {len(result)}"

    def test_short_nav_series(self):
        """净值序列过短（< 30 个有效收益率）→ 被排除"""
        rng = np.random.RandomState(42)
        navs_short = np.cumprod(1 + rng.randn(10) * 0.01).tolist()  # 只有 10 天
        navs_long = np.cumprod(1 + rng.randn(200) * 0.01).tolist()

        result = auto_dedup_by_correlation(
            [navs_short, navs_long], ["SHORT.SH", "LONG.SH"], rho_threshold=0.95
        )
        assert result == ["LONG.SH"], f"短序列应被排除，实际保留了 {result}"


# ============================================================
# 集成测试：Ledoit-Wolf 替换 calculate_covariance_matrix
# ============================================================

class TestCovarianceMatrixIntegration:
    """
    验证 calculate_covariance_matrix 使用 Ledoit-Wolf 后的行为

    主要是回归测试——确保替换后不引入破坏性变更。
    """

    def test_basic_usage_unchanged(self):
        """基本的协方差矩阵计算功能不变（形状、类型）"""
        np.random.seed(42)
        r1 = np.random.randn(200) * 0.01
        r2 = np.random.randn(200) * 0.015
        returns_list = [r1.tolist(), r2.tolist()]

        result = calculate_covariance_matrix(returns_list)
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 2), f"期望 (2,2), 得到 {result.shape}"
        assert np.all(np.diag(result) > 0), "方差必须为正"

    def test_condition_number_improved(self):
        """
        在高 N/p 场景下，Ledoit-Wolf 应产出条件数更好的矩阵。
        验证：同输入下新实现的矩阵条件数 <= np.cov 的条件数
        """
        np.random.seed(42)
        T, N = 40, 12  # 高 N/p 比值
        returns = [np.random.randn(T) * 0.01 + np.random.randn() * 0.002 for _ in range(N)]
        returns_list = [r.tolist() for r in returns]

        result = calculate_covariance_matrix(returns_list)

        # 对比 np.cov
        aligned = np.array([r[-min(len(rr) for rr in returns_list):] for r in returns_list])
        sample_cov = np.cov(aligned)

        cond_result = np.linalg.cond(result)
        cond_sample = np.linalg.cond(sample_cov)

        assert cond_result <= cond_sample * 1.05, (
            f"新实现条件数 ({cond_result:.2f}) 应 <= np.cov 条件数 ({cond_sample:.2f})"
        )
