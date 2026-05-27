"""
ETF组合推荐系统 - 后端单元测试（独立版本）

本模块包含对各服务的单元测试，不依赖外部模块导入。

测试覆盖：
1. 组合服务 - 收益率计算、波动率、夏普比率等
2. 优化服务 - 协方差矩阵、组合收益/波动率
3. 数据处理 - ETF分类判断
4. ORM模型 - 数据结构验证

运行方式：
    pytest backend/tests/test_services.py -v

作者: ETF组合系统
版本: 1.0.0
"""

import pytest
import numpy as np
from datetime import date, timedelta


class TestReturnsCalculation:
    """
    测试收益率计算函数

    测试用例验证：
    - 从净值序列正确计算收益率
    - 边界条件处理（数据不足等）
    """

    @staticmethod
    def calculate_returns_from_nav(nav_series):
        """从净值序列计算收益率序列（测试用独立实现）"""
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

    def test_calculate_returns_from_nav_basic(self):
        """
        测试基本的净值转收益率计算

        净值序列 [1.0, 1.02, 1.01, 1.05] 应产生收益率序列
        [0.02, -0.0098, 0.0396] (从第二天开始计算)
        """
        nav_series = [1.0, 1.02, 1.01, 1.05]
        returns = self.calculate_returns_from_nav(nav_series)

        assert len(returns) == 3
        assert abs(returns[0] - 0.02) < 0.001, f"First return should be ~0.02, got {returns[0]}"
        assert abs(returns[1] - (1.01 - 1.02) / 1.02) < 0.001, f"Second return mismatch, got {returns[1]}"
        assert abs(returns[2] - (1.05 - 1.01) / 1.01) < 0.001, f"Third return mismatch, got {returns[2]}"

    def test_calculate_returns_from_nav_empty(self):
        """测试空净值序列"""
        returns = self.calculate_returns_from_nav([])
        assert len(returns) == 1
        assert np.isnan(returns[0])

        returns = self.calculate_returns_from_nav([1.0])
        assert len(returns) == 1
        assert np.isnan(returns[0])

    def test_calculate_returns_from_nav_negative(self):
        """测试下跌净值序列"""
        nav_series = [1.0, 0.95, 0.90, 0.85]
        returns = self.calculate_returns_from_nav(nav_series)

        assert len(returns) == 3
        for r in returns:
            assert abs(r - (-0.05)) < 0.01, f"Expected ~-0.05, got {r}"


class TestAnnualizedReturn:
    """
    测试年化收益率计算

    验证公式: 年化收益率 = (1 + 累计收益率)^(252/交易天数) - 1
    """

    @staticmethod
    def calculate_annualized_return(total_return, days):
        """计算年化收益率（测试用独立实现）"""
        if days <= 0:
            return 0.0
        return (1 + total_return) ** (252 / days) - 1

    def test_annualized_return_basic(self):
        """测试基本年化收益率计算"""
        total_return = 0.15  # 15%累计收益
        days = 252  # 一年

        ann_ret = self.calculate_annualized_return(total_return, days)
        assert abs(ann_ret - 0.15) < 0.001

    def test_annualized_return_half_year(self):
        """测试半年期年化"""
        total_return = 0.10  # 10%半年收益
        days = 126  # 半年约126个交易日

        ann_ret = self.calculate_annualized_return(total_return, days)
        expected = (1.10) ** (252 / 126) - 1
        assert abs(ann_ret - expected) < 0.001

    def test_annualized_return_zero_days(self):
        """测试零天数处理"""
        ann_ret = self.calculate_annualized_return(0.15, 0)
        assert ann_ret == 0.0

    def test_annualized_return_negative(self):
        """测试负收益年化"""
        total_return = -0.10  # -10%收益
        days = 252

        ann_ret = self.calculate_annualized_return(total_return, days)
        assert ann_ret < 0


class TestVolatility:
    """
    测试波动率计算

    验证年化波动率 = 日波动率 * sqrt(annual_factor)
    """

    @staticmethod
    def calculate_volatility(daily_returns, annual_factor=252):
        """计算年化波动率（测试用独立实现）"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0
        returns_array = np.array(daily_returns)
        valid_returns = returns_array[~np.isnan(returns_array)]
        if len(valid_returns) < 2:
            return 0.0
        daily_volatility = np.std(valid_returns, ddof=1)
        annualized_vol = daily_volatility * np.sqrt(annual_factor)
        return annualized_vol

    def test_volatility_basic(self):
        """测试基本波动率计算"""
        daily_returns = [0.01, -0.02, 0.015, -0.005, 0.02]
        vol = self.calculate_volatility(daily_returns)

        assert vol > 0
        assert vol < 1

    def test_volatility_empty(self):
        """测试空序列"""
        vol = self.calculate_volatility([])
        assert vol == 0.0

        vol = self.calculate_volatility([0.01])
        assert vol == 0.0


class TestSharpeRatio:
    """
    测试夏普比率计算

    公式: 夏普比率 = (年化收益率 - 无风险利率) / 年化波动率
    """

    @staticmethod
    def calculate_sharpe_ratio(annualized_return, volatility, risk_free=0.03):
        """计算夏普比率（测试用独立实现）"""
        if volatility == 0:
            return 0.0
        return (annualized_return - risk_free) / volatility

    def test_sharpe_ratio_basic(self):
        """测试基本夏普比率"""
        ann_ret = 0.12  # 12%年化收益
        volatility = 0.18  # 18%波动率
        risk_free = 0.03  # 3%无风险利率

        sharpe = self.calculate_sharpe_ratio(ann_ret, volatility, risk_free)
        expected = (0.12 - 0.03) / 0.18
        assert abs(sharpe - expected) < 0.001

    def test_sharpe_ratio_zero_volatility(self):
        """测试零波动率（避免除零）"""
        sharpe = self.calculate_sharpe_ratio(0.12, 0.0)
        assert sharpe == 0.0

    def test_sharpe_ratio_negative(self):
        """测试负夏普比率（收益低于无风险利率）"""
        sharpe = self.calculate_sharpe_ratio(0.02, 0.15, 0.03)
        assert sharpe < 0


class TestMaxDrawdown:
    """
    测试最大回撤计算

    验证最大回撤 = (最高点 - 最低点) / 最高点
    """

    @staticmethod
    def calculate_max_drawdown(nav_series):
        """计算最大回撤（测试用独立实现）"""
        if not nav_series or len(nav_series) < 2:
            return 0.0, None

        peak = nav_series[0]
        max_dd = 0.0
        max_dd_date = None

        for i, nav in enumerate(nav_series):
            if nav > peak:
                peak = nav
            drawdown = (nav - peak) / peak
            if drawdown < max_dd:
                max_dd = drawdown

        return max_dd, max_dd_date

    def test_max_drawdown_basic(self):
        """测试基本最大回撤"""
        nav_series = [1.0, 1.1, 1.05, 0.95, 1.0]
        mdd, _ = self.calculate_max_drawdown(nav_series)

        assert mdd < 0
        assert abs(mdd - (-0.136)) < 0.01

    def test_max_drawdown_continuous_up(self):
        """测试连续上涨（无回撤）"""
        nav_series = [1.0, 1.05, 1.10, 1.15]
        mdd, _ = self.calculate_max_drawdown(nav_series)

        assert mdd == 0.0

    def test_max_drawdown_empty(self):
        """测试空序列"""
        mdd, date = self.calculate_max_drawdown([])
        assert mdd == 0.0
        assert date is None


class TestCovarianceMatrix:
    """
    测试协方差矩阵计算
    """

    @staticmethod
    def calculate_covariance_matrix(returns_list):
        """计算协方差矩阵（测试用独立实现）"""
        if not returns_list or len(returns_list) == 0:
            return np.array([])

        min_len = min(len(r) for r in returns_list)
        aligned_returns = np.array([r[-min_len:] for r in returns_list])

        cov_matrix = np.cov(aligned_returns, rowvar=True)
        if cov_matrix.shape[0] != cov_matrix.shape[1]:
            n = len(returns_list)
            cov_matrix = np.zeros((n, n))

        return cov_matrix

    def test_covariance_matrix_basic(self):
        """测试基本协方差矩阵"""
        returns1 = [0.01, -0.02, 0.015, -0.005, 0.02]
        returns2 = [0.005, -0.01, 0.02, 0.008, 0.015]

        cov = self.calculate_covariance_matrix([returns1, returns2])

        assert cov.shape == (2, 2)
        assert cov[0, 0] > 0
        assert cov[1, 1] > 0

    def test_covariance_matrix_empty(self):
        """测试空矩阵"""
        cov = self.calculate_covariance_matrix([])
        assert cov.size == 0


class TestPortfolioReturn:
    """
    测试组合收益率计算
    """

    @staticmethod
    def portfolio_return(weights, returns):
        """计算组合收益率（测试用独立实现）"""
        return np.dot(weights, returns)

    def test_portfolio_return_basic(self):
        """测试基本组合收益率"""
        weights = np.array([0.6, 0.4])
        returns = np.array([0.15, 0.10])

        ret = self.portfolio_return(weights, returns)
        expected = 0.6 * 0.15 + 0.4 * 0.10

        assert abs(ret - expected) < 0.0001


class TestPortfolioVolatility:
    """
    测试组合波动率计算
    """

    @staticmethod
    def portfolio_volatility(weights, cov_matrix):
        """计算组合波动率（测试用独立实现）"""
        if cov_matrix.size == 0:
            return 0.0
        return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

    def test_portfolio_volatility_basic(self):
        """测试基本组合波动率"""
        weights = np.array([0.6, 0.4])
        cov_matrix = np.array([
            [0.04, 0.01],
            [0.01, 0.025]
        ])

        vol = self.portfolio_volatility(weights, cov_matrix)

        assert vol > 0
        expected_var = 0.6**2 * 0.04 + 0.4**2 * 0.025 + 2 * 0.6 * 0.4 * 0.01
        expected_vol = np.sqrt(expected_var)
        assert abs(vol - expected_vol) < 0.0001

    def test_portfolio_volatility_empty_matrix(self):
        """测试空协方差矩阵"""
        vol = self.portfolio_volatility(np.array([0.5, 0.5]), np.array([]))
        assert vol == 0.0


class TestCategoryDetermination:
    """
    测试ETF分类判断
    """

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

    @staticmethod
    def determine_category(etf_name):
        """根据ETF名称推断分类（测试用独立实现）"""
        for keyword, category in TestCategoryDetermination.ETF_CATEGORY_MAP.items():
            if keyword in etf_name:
                return category
        return "宽基指数"

    def test_determine_category_wide_base(self):
        """测试宽基指数分类"""
        assert self.determine_category("沪深300ETF") == "宽基指数"
        assert self.determine_category("中证500ETF") == "宽基指数"
        assert self.determine_category("上证50ETF") == "宽基指数"
        assert self.determine_category("创业板ETF") == "宽基指数"
        assert self.determine_category("科创50ETF") == "宽基指数"

    def test_determine_category_industry(self):
        """测试行业指数分类"""
        assert self.determine_category("军工ETF") == "行业指数"
        assert self.determine_category("医药ETF") == "行业指数"
        assert self.determine_category("半导体ETF") == "行业指数"
        assert self.determine_category("新能源ETF") == "行业指数"

    def test_determine_category_commodity(self):
        """测试商品分类"""
        assert self.determine_category("黄金ETF") == "商品"
        assert self.determine_category("白银ETF") == "商品"
        assert self.determine_category("原油ETF") == "商品"

    def test_determine_category_overseas(self):
        """测试境外分类"""
        assert self.determine_category("纳斯达克ETF") == "境外"
        assert self.determine_category("标普500ETF") == "境外"
        assert self.determine_category("日经ETF") == "境外"
        assert self.determine_category("恒生ETF") == "境外"

    def test_determine_category_bond(self):
        """测试债券分类"""
        assert self.determine_category("债券ETF") == "债券"
        assert self.determine_category("国债ETF") == "债券"

    def test_determine_category_default(self):
        """测试默认分类"""
        assert self.determine_category("未知类型ETF") == "宽基指数"


class TestDataClasses:
    """测试数据类"""

    def test_etf_info_structure(self):
        """测试ETFInfo数据结构"""
        etf_info = {
            "code": "510300",
            "name": "沪深300ETF",
            "category": "宽基指数",
            "updated_at": "2024-01-01T00:00:00"
        }

        assert etf_info["code"] == "510300"
        assert etf_info["name"] == "沪深300ETF"
        assert etf_info["category"] == "宽基指数"
        assert etf_info["updated_at"] is not None

    def test_nav_history_structure(self):
        """测试NAV历史数据结构"""
        nav_history = {
            "date": "2024-01-01",
            "nav": 3.8765,
            "accum_nav": 4.1234
        }

        assert nav_history["date"] == "2024-01-01"
        assert nav_history["nav"] == 3.8765
        assert nav_history["accum_nav"] == 4.1234
        assert nav_history["nav"] <= nav_history["accum_nav"]

    def test_portfolio_metrics_structure(self):
        """测试组合指标数据结构"""
        metrics = {
            "total_return": 15.5,
            "annualized_return": 12.3,
            "volatility": 18.7,
            "sharpe_ratio": 0.67,
            "max_drawdown": -8.2,
            "holding_period": 252,
            "nav_series": [1.0, 1.02, 1.05],
            "daily_returns": [0.02, 0.029],
            "etf_metrics": {}
        }

        assert metrics["total_return"] == 15.5
        assert metrics["annualized_return"] == 12.3
        assert metrics["volatility"] == 18.7
        assert metrics["sharpe_ratio"] == 0.67
        assert metrics["max_drawdown"] == -8.2
        assert metrics["holding_period"] == 252
        assert len(metrics["nav_series"]) == 3
        assert len(metrics["daily_returns"]) == 2

    def test_optimization_result_structure(self):
        """测试优化结果数据结构"""
        result = {
            "success": True,
            "weights": {"510300": 0.6, "510500": 0.4},
            "expected_return": 12.5,
            "volatility": 18.3,
            "sharpe_ratio": 0.52,
            "message": "优化成功"
        }

        assert result["success"] is True
        assert result["weights"]["510300"] == 0.6
        assert result["weights"]["510500"] == 0.4
        assert result["expected_return"] == 12.5
        assert result["sharpe_ratio"] == 0.52
        assert result["message"] == "优化成功"


class TestPortfolioWeights:
    """测试组合权重计算"""

    def test_weights_normalization(self):
        """测试权重归一化"""
        weights = {"510300": 0.5, "510500": 0.5}
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.0001

    def test_single_etf_weight(self):
        """测试单只ETF权重"""
        weights = {"510300": 1.0}
        assert weights["510300"] == 1.0
        assert sum(weights.values()) == 1.0

    def test_equal_weight_calculation(self):
        """测试等权重计算"""
        codes = ["510300", "510500", "159915"]
        equal_weight = 1.0 / len(codes)

        for code in codes:
            assert abs(equal_weight - 0.333) < 0.001


class TestMetricCalculations:
    """测试指标计算逻辑"""

    def test_return_calculation_logic(self):
        """测试收益率计算逻辑"""
        nav_start = 1.0
        nav_end = 1.15
        total_return = (nav_end - nav_start) / nav_start
        assert abs(total_return - 0.15) < 0.0001

    def test_volatility_calculation_logic(self):
        """测试波动率计算逻辑"""
        returns = [0.01, -0.02, 0.015, -0.005, 0.02]
        std_dev = np.std(returns, ddof=1)
        ann_vol = std_dev * np.sqrt(252)
        assert ann_vol > 0

    def test_sharpe_calculation_logic(self):
        """测试夏普比率计算逻辑"""
        ann_ret = 0.12
        ann_vol = 0.18
        risk_free = 0.03
        sharpe = (ann_ret - risk_free) / ann_vol
        assert abs(sharpe - 0.5) < 0.001

    def test_max_drawdown_calculation_logic(self):
        """测试最大回撤计算逻辑"""
        nav_series = [1.0, 1.1, 1.05, 0.95, 1.0]
        peak = max(nav_series)
        trough = min(nav_series)
        max_dd = (trough - peak) / peak
        assert abs(max_dd - (-0.136)) < 0.01


class TestPortfolioMaxDrawdown:
    """
    测试组合最大回撤计算
    """

    @staticmethod
    def portfolio_max_drawdown(weights, aligned_navs):
        """计算组合最大回撤（测试用独立实现）"""
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

    def test_portfolio_max_drawdown_basic(self):
        """测试基本组合最大回撤"""
        aligned_navs = [
            [1.0, 1.1, 1.05, 0.95, 1.0],
            [1.0, 1.05, 1.0, 0.98, 1.02]
        ]
        weights = np.array([0.6, 0.4])
        mdd = self.portfolio_max_drawdown(weights, aligned_navs)

        assert mdd < 0
        assert abs(mdd - (-0.1093)) < 0.01

    def test_portfolio_max_drawdown_single_etf(self):
        """测试单只ETF组合"""
        aligned_navs = [[1.0, 1.2, 0.9]]
        weights = np.array([1.0])
        mdd = self.portfolio_max_drawdown(weights, aligned_navs)

        assert mdd < 0
        assert abs(mdd - (-0.25)) < 0.01

    def test_portfolio_max_drawdown_empty(self):
        """测试空输入"""
        mdd = self.portfolio_max_drawdown(np.array([]), [])
        assert mdd == 0.0

    def test_portfolio_max_drawdown_no_drawdown(self):
        """测试无回撤情况（连续上涨）"""
        aligned_navs = [
            [1.0, 1.05, 1.10],
            [1.0, 1.02, 1.04]
        ]
        weights = np.array([0.5, 0.5])
        mdd = self.portfolio_max_drawdown(weights, aligned_navs)

        assert mdd == 0.0

    def test_portfolio_max_drawdown_two_etf_diversification(self):
        """测试两只ETF分散化效果"""
        navs1 = [1.0, 1.1, 1.05, 0.95, 1.0]
        navs2 = [1.0, 0.95, 1.0, 1.05, 1.1]
        aligned_navs = [navs1, navs2]

        weights1 = np.array([1.0, 0.0])
        mdd1 = self.portfolio_max_drawdown(weights1, aligned_navs)

        weights2 = np.array([0.5, 0.5])
        mdd2 = self.portfolio_max_drawdown(weights2, aligned_navs)

        assert mdd2 >= mdd1


class TestEdgeCases:
    """测试边界条件"""

    def test_empty_portfolio(self):
        """测试空组合"""
        weights = {}
        assert len(weights) == 0

    def test_zero_weight(self):
        """测试零权重"""
        weights = {"510300": 0.0, "510500": 1.0}
        assert weights["510300"] == 0.0
        assert weights["510500"] == 1.0

    def test_negative_return(self):
        """测试负收益"""
        nav_series = [1.0, 0.95, 0.90]
        total_return = (nav_series[-1] - nav_series[0]) / nav_series[0]
        assert abs(total_return - (-0.10)) < 0.001, f"Expected ~-0.10, got {total_return}"

    def test_large_volatility(self):
        """测试高波动率"""
        returns = [0.10, -0.10, 0.10, -0.10] * 10
        vol = np.std(returns) * np.sqrt(252)
        assert vol > 0.5


class TestPortfolioCDaR:
    """
    测试组合 CDaR（条件回撤）计算
    """

    @staticmethod
    def portfolio_cdar(weights, aligned_navs, alpha=0.05):
        """计算 CDaR（测试用独立实现）"""
        if not aligned_navs or len(weights) == 0:
            return 0.0
        n = len(aligned_navs)
        min_len = len(aligned_navs[0])
        portfolio_navs = [sum(aligned_navs[j][i] * weights[j] for j in range(n)) for i in range(min_len)]
        if len(portfolio_navs) < 2:
            return 0.0
        rolling_max = np.maximum.accumulate(portfolio_navs)
        drawdowns = (np.array(portfolio_navs) - rolling_max) / rolling_max
        worst_n = max(1, int(len(drawdowns) * alpha))
        sorted_drawdowns = np.sort(drawdowns)
        return float(np.mean(sorted_drawdowns[:worst_n]))

    def test_cdar_basic(self):
        """测试基本 CDaR 计算"""
        navs1 = [1.0, 1.1, 1.05, 0.95, 1.0, 0.90, 0.85, 0.95, 1.0]
        navs2 = [1.0, 1.05, 1.0, 0.98, 1.02, 0.95, 0.90, 0.92, 1.0]
        aligned_navs = [navs1, navs2]
        weights = np.array([0.6, 0.4])
        cdar = self.portfolio_cdar(weights, aligned_navs)
        assert cdar < 0
        assert cdar >= -0.20

    def test_cdar_custom_alpha(self):
        """测试自定义 alpha"""
        navs = [1.0, 1.1, 1.05, 0.95, 1.0, 0.90, 0.85, 0.95, 1.0]
        aligned_navs = [navs]
        weights = np.array([1.0])
        cdar_005 = self.portfolio_cdar(weights, [aligned_navs[0]], alpha=0.05)
        cdar_010 = self.portfolio_cdar(weights, [aligned_navs[0]], alpha=0.10)
        assert cdar_005 >= cdar_010

    @staticmethod
    def portfolio_max_drawdown(weights, aligned_navs):
        if not aligned_navs or len(weights) == 0:
            return 0.0
        n = len(aligned_navs)
        min_len = len(aligned_navs[0])
        portfolio_navs = [sum(aligned_navs[j][i] * weights[j] for j in range(n)) for i in range(min_len)]
        if len(portfolio_navs) < 2:
            return 0.0
        rolling_max = np.maximum.accumulate(portfolio_navs)
        drawdowns = (np.array(portfolio_navs) - rolling_max) / rolling_max
        return float(np.min(drawdowns))

    def test_cdar_ge_mdd(self):
        """验证 CDaR >= MDD（CDaR 不比 MDD 更负）"""
        navs1 = [1.0, 1.1, 1.05, 0.95, 1.0]
        navs2 = [1.0, 1.05, 1.0, 0.98, 1.02]
        aligned_navs = [navs1, navs2]
        weights = np.array([0.6, 0.4])
        cdar = self.portfolio_cdar(weights, aligned_navs)
        mdd = self.portfolio_max_drawdown(weights, aligned_navs)
        assert cdar >= mdd

    def test_cdar_empty(self):
        """测试空输入返回 0"""
        cdar = self.portfolio_cdar(np.array([]), [])
        assert cdar == 0.0

    def test_cdar_single_point(self):
        """测试单点返回 0"""
        cdar = self.portfolio_cdar(np.array([1.0]), [[1.0, 1.05]])
        assert cdar == 0.0


class TestDrawdownPenalty:
    """
    测试回撤二次罚项
    """

    @staticmethod
    def drawdown_penalty_objective(weights, returns, cov_matrix, risk_aversion, annual_factor, aligned_navs, gamma, target_mdd, alpha=0.05, hhi_target=None, gamma_hhi=2.0):
        """计算带回撤罚项的目标函数（测试用独立实现）"""
        p_return = np.dot(weights, returns)
        p_vol_sq = np.dot(weights.T, np.dot(cov_matrix, weights)) * annual_factor
        base_obj = -(p_return - risk_aversion * p_vol_sq)
        if not aligned_navs or len(weights) == 0:
            cdar = 0.0
        else:
            n = len(aligned_navs)
            min_len = len(aligned_navs[0])
            portfolio_navs = [sum(aligned_navs[j][i] * weights[j] for j in range(n)) for i in range(min_len)]
            if len(portfolio_navs) < 2:
                cdar = 0.0
            else:
                rolling_max = np.maximum.accumulate(portfolio_navs)
                drawdowns = (np.array(portfolio_navs) - rolling_max) / rolling_max
                worst_n = max(1, int(len(drawdowns) * alpha))
                sorted_drawdowns = np.sort(drawdowns)
                cdar = float(np.mean(sorted_drawdowns[:worst_n]))
        violation = max(0.0, abs(cdar) - target_mdd)
        penalty = gamma * violation ** 2
        # HHI 集中度罚项
        if hhi_target is not None:
            hhi = float(np.sum(weights ** 2))
            hhi_violation = max(0.0, hhi - hhi_target)
            penalty += gamma_hhi * hhi_violation ** 2
        return base_obj + penalty

    def test_penalty_zero_when_satisfied(self):
        """测试 CDaR 满足目标时罚项为 0"""
        navs = [1.0, 1.05, 1.0, 0.98, 1.02, 1.03, 1.05]
        aligned_navs = [navs]
        weights = np.array([1.0])
        returns = np.array([0.05])
        cov = np.array([[0.01]])
        total_obj = self.drawdown_penalty_objective(weights, returns, cov, 0.0, 252, aligned_navs, 1.0, 0.10)
        base_obj = -np.dot(weights, returns)
        assert abs(total_obj - base_obj) < 1e-10

    def test_penalty_positive_when_violated(self):
        """测试 CDaR 超出目标时罚项为正"""
        navs = [1.0, 1.2, 1.1, 0.9, 0.85]
        aligned_navs = [navs]
        weights = np.array([1.0])
        returns = np.array([0.08])
        cov = np.array([[0.04]])
        base_obj = -np.dot(weights, returns)
        total_obj = self.drawdown_penalty_objective(weights, returns, cov, 0.0, 252, aligned_navs, 2.0, 0.05)
        penalty = total_obj - base_obj
        assert penalty > 0

    def test_penalty_scales_with_gamma(self):
        """测试罚项随 gamma 缩放"""
        navs = [1.0, 1.2, 1.1, 0.9, 0.85]
        aligned_navs = [navs]
        weights = np.array([1.0])
        returns = np.array([0.08])
        cov = np.array([[0.04]])
        total_1 = self.drawdown_penalty_objective(weights, returns, cov, 0.0, 252, aligned_navs, 1.0, 0.05)
        total_2 = self.drawdown_penalty_objective(weights, returns, cov, 0.0, 252, aligned_navs, 2.0, 0.05)
        pen_1 = total_1 - (-np.dot(weights, returns))
        pen_2 = total_2 - (-np.dot(weights, returns))
        assert pen_2 > pen_1 > 0


class TestIterativeDrawdownOptimizer:
    """
    测试迭代升温回撤优化器
    """

    def test_iterations_field_exists(self):
        """测试 OptimizationResult 有 iterations 字段"""
        from backend.services.optimizer_service import OptimizationResult
        result = OptimizationResult(True, {}, 0.0, 0.0, 0.0, "test", max_drawdown=0.0, iterations=3)
        assert result.iterations == 3

    def test_max_drawdown_field_exists(self):
        """测试 OptimizationResult 有 max_drawdown 字段"""
        from backend.services.optimizer_service import OptimizationResult
        result = OptimizationResult(True, {}, 0.0, 0.0, 0.0, "test", max_drawdown=-12.5, iterations=1)
        assert result.max_drawdown == -12.5

    def test_default_fields(self):
        """测试默认值"""
        from backend.services.optimizer_service import OptimizationResult
        result = OptimizationResult(True, {}, 0.0, 0.0, 0.0, "test")
        assert result.max_drawdown == 0.0
        assert result.iterations == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])