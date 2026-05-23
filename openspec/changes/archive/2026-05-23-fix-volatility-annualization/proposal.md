## Why

波动率年化计算存在量纲不一致问题。当前实现使用固定交易日天数（252）进行年化，但优化目标函数中组合收益已是年化收益率，而波动率平方用的是日波动率 × 252，导致风险厌恶系数 λ 的物理含义被扭曲。

## What Changes

- 修改 `maximize_return_objective` 目标函数，将日协方差矩阵直接年化
- 修改波动率约束，使用基于实际统计时间范围的年化因子
- 新增 `get_annual_factor` 函数，根据 period 计算月数年化因子
- 修改 `calculate_volatility` 增加 `annual_factor` 参数
- 同步修改所有调用 `calculate_volatility` 的函数，传递 period 参数

## Capabilities

### New Capabilities

- `volatility-annualization`: 修正波动率年化计算，使用月数/季度数作为年化因子而非固定 252

### Modified Capabilities

- 无。修正不影响外部行为，仅内部计算逻辑调整

## Impact

- **backend/services/optimizer_service.py**:
  - `maximize_return_objective`: 增加 `annual_factor` 参数
  - `optimize_max_return`: 传入年化因子
  - `optimize_with_constraints`: 波动率约束和目标函数传入年化因子
  - 组合波动率输出时同步修改
- **backend/services/portfolio_service.py**:
  - 新增 `get_annual_factor` 函数
  - `calculate_volatility`: 增加 `annual_factor` 参数
  - `calculate_portfolio_metrics`: 传递 `annual_factor`
  - `calculate_single_etf_metrics`: 传递 `annual_factor`
  - `evaluate_portfolio`: 传递 `annual_factor`
- **backend/tests/test_services.py**:
  - `TestVolatility.calculate_volatility`: 增加 `annual_factor` 参数