"""
服务模块初始化文件

导出所有服务供其他模块使用。
"""

from backend.services.etf_data_service import (
    fetch_etf_list_from_em,
    fetch_etf_history,
    sync_all_etf_data,
    get_etf_info_from_db,
    get_etf_history_from_db,
    save_etf_info_to_db,
    save_etf_nav_to_db,
    clear_etf_data,
    fetch_trade_dates,
    get_trade_dates,
)

from backend.services.portfolio_service import (
    calculate_returns_from_nav,
    calculate_annualized_return,
    calculate_volatility,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_portfolio_metrics,
    evaluate_portfolio,
    compare_portfolios,
    get_etf_nav_series,
    calculate_single_etf_metrics,
    PortfolioMetrics,
    SingleETFFMetrics,
)

from backend.services.optimizer_service import (
    optimize_max_return,
    optimize_with_constraints,
    portfolio_return,
    portfolio_volatility,
    calculate_covariance_matrix,
    OptimizationResult,
)

__all__ = [
    # 数据服务
    "fetch_etf_list_from_em",
    "fetch_etf_history",
    "sync_all_etf_data",
    "get_etf_info_from_db",
    "get_etf_history_from_db",
    "save_etf_info_to_db",
    "save_etf_nav_to_db",
    "clear_etf_data",
    "fetch_trade_dates",
    "get_trade_dates",
    # 组合服务
    "calculate_returns_from_nav",
    "calculate_annualized_return",
    "calculate_volatility",
    "calculate_sharpe_ratio",
    "calculate_max_drawdown",
    "calculate_portfolio_metrics",
    "evaluate_portfolio",
    "compare_portfolios",
    "get_etf_nav_series",
    "calculate_single_etf_metrics",
    "PortfolioMetrics",
    "SingleETFFMetrics",
    # 优化服务
    "optimize_max_return",
    "optimize_with_constraints",
    "portfolio_return",
    "portfolio_volatility",
    "calculate_covariance_matrix",
    "OptimizationResult",
    ]