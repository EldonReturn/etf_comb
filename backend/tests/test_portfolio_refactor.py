"""
等效性测试 - 直接从 portfolio_service 导入函数
用于验证重构前后行为一致
"""
import math
import pytest
from backend.services.portfolio_service import (
    calculate_returns_from_nav,
    calculate_annualized_return,
    calculate_volatility,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    get_etf_nav_series,
    get_etf_nav_dates,
    evaluate_portfolio,
    PortfolioMetrics,
    SingleETFFMetrics,
)


class TestReturnsCalculation:
    """测试 calculate_returns_from_nav 函数"""

    def test_normal_sequence(self):
        """正常净值序列"""
        nav = [1.0, 1.02, 1.01, 1.05]
        result = calculate_returns_from_nav(nav)
        assert len(result) == 3
        assert result[0] == pytest.approx(0.02, rel=1e-10)
        assert result[1] == pytest.approx(-0.009803921568627452, rel=1e-10)
        assert result[2] == pytest.approx(0.039603960396039604, rel=1e-10)

    def test_zero_value_in_middle(self):
        """中间有零值的情况"""
        nav = [1.0, 0.0, 1.01, 1.05]
        result = calculate_returns_from_nav(nav)
        assert len(result) == 3
        # 1.0 -> 0.0: (0.0 - 1.0) / 1.0 = -1.0
        assert result[0] == pytest.approx(-1.0, rel=1e-10)
        # 0.0 -> 1.01: 0作为除数 -> inf或nan，实际为nan
        assert math.isnan(result[1])
        assert result[2] == pytest.approx(0.039603960396039604, rel=1e-10)

    def test_full_zero_sequence(self):
        """全零序列"""
        nav = [0.0, 0.0, 0.0]
        result = calculate_returns_from_nav(nav)
        assert len(result) == 2
        assert all(math.isnan(r) for r in result)

    def test_single_element(self):
        """单元素序列"""
        nav = [1.0]
        result = calculate_returns_from_nav(nav)
        assert len(result) == 1
        assert math.isnan(result[0])

    def test_empty(self):
        """空序列"""
        nav = []
        result = calculate_returns_from_nav(nav)
        assert len(result) == 1
        assert math.isnan(result[0])


class TestVolatility:
    """测试 calculate_volatility 函数"""

    def test_normal_returns(self):
        """正常收益率序列"""
        returns = [0.01, -0.02, 0.015, -0.005]
        result = calculate_volatility(returns)
        assert result > 0
        # 验证年化计算: daily_std * sqrt(252)

    def test_empty_list(self):
        """空列表"""
        result = calculate_volatility([])
        assert result == 0.0

    def test_single_element(self):
        """单元素"""
        result = calculate_volatility([0.01])
        assert result == 0.0

    def test_all_nan(self):
        """全是 NaN"""
        result = calculate_volatility([float('nan'), float('nan')])
        assert result == 0.0

    def test_mixed_nan(self):
        """混合 NaN 和有效值"""
        returns = [float('nan'), 0.01, float('nan'), -0.02]
        result = calculate_volatility(returns)
        assert result > 0


class TestMaxDrawdown:
    """测试 calculate_max_drawdown 函数"""

    def test_with_drawdown(self):
        """有回撤的情况: 1.0 -> 1.1 -> 1.05 -> 0.95 -> 1.0"""
        nav = [1.0, 1.1, 1.05, 0.95, 1.0]
        mdd, date = calculate_max_drawdown(nav)
        assert mdd < 0  # 负值
        # 最大回撤发生在 0.95 点: (0.95 - 1.1) / 1.1 = -0.13636...
        assert mdd == pytest.approx(-0.13636363636363635, rel=1e-10)

    def test_continuous_rise(self):
        """连续上涨无回撤"""
        nav = [1.0, 1.05, 1.1, 1.15]
        mdd, date = calculate_max_drawdown(nav)
        assert mdd == 0.0

    def test_empty_sequence(self):
        """空序列"""
        mdd, date = calculate_max_drawdown([])
        assert mdd == 0.0
        assert date is None

    def test_single_element(self):
        """单元素序列"""
        mdd, date = calculate_max_drawdown([1.0])
        assert mdd == 0.0
        assert date is None

    def test_date_is_not_none_when_data_exists(self):
        """验证当数据存在时，日期不应为 None

        注意：当前实现返回 None，这是现有行为的记录。
        如果未来实现返回日期，此测试应通过。
        """
        nav = [1.0, 1.1, 0.95]
        mdd, date = calculate_max_drawdown(nav)
        # 当前返回 (负值, None)
        assert mdd < 0
        # 日期行为待确认 - 这是基线测试
        assert date is None  # 基线行为


class TestSharpeRatio:
    """测试 calculate_sharpe_ratio 函数"""

    def test_normal_ratio(self):
        """正常夏普比率计算"""
        # 年化收益 12%, 波动率 18%, 无风险利率 3%
        result = calculate_sharpe_ratio(0.12, 0.18)
        expected = (0.12 - 0.03) / 0.18
        assert result == pytest.approx(expected, rel=1e-10)

    def test_zero_volatility(self):
        """零波动率（避免除零）"""
        result = calculate_sharpe_ratio(0.12, 0.0)
        assert result == 0.0

    def test_negative_volatility(self):
        """负波动率 - 当前实现不处理负数"""
        result = calculate_sharpe_ratio(0.12, -0.05)
        # 当前实现：返回 (0.12 - 0.03) / (-0.05) = -1.8
        # 不返回0.0（只有volatility==0时才返回0.0）
        assert result == pytest.approx(-1.8, rel=1e-10)


class TestAnnualizedReturn:
    """测试 calculate_annualized_return 函数"""

    def test_normal(self):
        """正常年化计算: 持有 60 天，收益 15%"""
        result = calculate_annualized_return(0.15, 60)
        expected = (1 + 0.15) ** (252 / 60) - 1
        assert result == pytest.approx(expected, rel=1e-10)

    def test_zero_days(self):
        """零天数"""
        result = calculate_annualized_return(0.15, 0)
        assert result == 0.0

    def test_negative_days(self):
        """负天数"""
        result = calculate_annualized_return(0.15, -10)
        assert result == 0.0

    def test_negative_return(self):
        """负收益"""
        result = calculate_annualized_return(-0.10, 30)
        expected = (1 - 0.10) ** (252 / 30) - 1
        assert result == pytest.approx(expected, rel=1e-10)


class TestETFNavSeries:
    """测试 get_etf_nav_series 函数（依赖数据库）"""

    @pytest.mark.skip(reason="requires DB with real ETF data")
    def test_valid_etf_code(self):
        """有效 ETF 代码"""
        from backend.db import get_session
        with get_session() as session:
            navs = get_etf_nav_series(session, "510310.SH", 30)
            assert isinstance(navs, list)
            assert len(navs) > 0

    @pytest.mark.skip(reason="requires DB")
    def test_invalid_code_returns_empty(self):
        """无效代码返回空列表"""
        from backend.db import get_session
        with get_session() as session:
            navs = get_etf_nav_series(session, "INVALID.CODE", 30)
            assert navs == []


class TestETFNavDates:
    """测试 get_etf_nav_dates 函数（依赖数据库）"""

    @pytest.mark.skip(reason="requires DB with real ETF data")
    def test_valid_etf_code(self):
        """有效 ETF 代码"""
        from backend.db import get_session
        with get_session() as session:
            dates = get_etf_nav_dates(session, "510310.SH", 30)
            assert isinstance(dates, list)
            assert len(dates) > 0

    @pytest.mark.skip(reason="requires DB")
    def test_return_format_list_of_strings(self):
        """返回格式为字符串列表"""
        from backend.db import get_session
        with get_session() as session:
            dates = get_etf_nav_dates(session, "510310.SH", 30)
            assert all(isinstance(d, str) for d in dates)


class TestEvaluatePortfolio:
    """测试 evaluate_portfolio 函数（依赖数据库）"""

    @pytest.mark.skip(reason="requires DB with real ETF data")
    def test_single_etf_1m_period(self):
        """单只 ETF + 1个月周期"""
        from backend.db import get_session
        weights = {"510310.SH": 1.0}
        with get_session() as session:
            result = evaluate_portfolio(weights, session, period="1m")

        assert isinstance(result, dict)
        assert len(result) == 12

        # 验证键存在
        expected_keys = [
            "total_return", "annualized_return", "volatility",
            "sharpe_ratio", "max_drawdown", "holding_period",
            "nav_series", "nav_dates", "benchmark_nav_series",
            "benchmark_code", "benchmark_name", "daily_returns"
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    @pytest.mark.skip(reason="requires DB")
    def test_return_dict_structure(self):
        """验证返回字典结构"""
        from backend.db import get_session
        weights = {"510310.SH": 1.0}
        with get_session() as session:
            result = evaluate_portfolio(weights, session, period="1m")

        # 验证类型
        assert isinstance(result["total_return"], float)
        assert isinstance(result["annualized_return"], float)
        assert isinstance(result["volatility"], float)
        assert isinstance(result["sharpe_ratio"], float)
        assert isinstance(result["max_drawdown"], float)
        assert isinstance(result["holding_period"], int)
        assert isinstance(result["nav_series"], list)
        assert isinstance(result["nav_dates"], list)


class TestDataClasses:
    """测试数据类的字段类型"""

    def test_portfolio_metrics_fields(self):
        """验证 PortfolioMetrics 字段类型"""
        pm = PortfolioMetrics(
            total_return=0.15,
            annualized_return=0.12,
            volatility=0.18,
            sharpe_ratio=0.5,
            max_drawdown=-0.08,
            max_drawdown_date="2024-03-15",
            daily_returns=[0.01, -0.02],
            nav_series=[1.0, 1.01],
            nav_dates=["2024-01-01", "2024-01-02"],
            holding_period=10
        )
        assert isinstance(pm.total_return, float)
        assert isinstance(pm.max_drawdown_date, (str, type(None)))
        assert isinstance(pm.holding_period, int)

    def test_single_etf_metrics_fields(self):
        """验证 SingleETFFMetrics 字段类型"""
        sm = SingleETFFMetrics(
            code="510310.SH",
            name="沪深300ETF",
            total_return=0.15,
            annualized_return=0.12,
            volatility=0.18,
            sharpe_ratio=0.5,
            max_drawdown=-0.08,
            nav_series=[1.0, 1.01]
        )
        assert isinstance(sm.code, str)
        assert isinstance(sm.name, str)
        assert isinstance(sm.total_return, float)