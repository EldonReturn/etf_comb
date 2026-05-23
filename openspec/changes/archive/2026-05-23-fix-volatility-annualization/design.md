## Context

当前组合优化使用均值-方差框架（Markowitz Portfolio Optimization），但波动率年化计算存在问题：

1. **目标函数量纲不一致**: `p_return` 是年化收益率，`p_volatility_sq` 是日波动率平方 × 252，未统一成年化
2. **年化因子固定**: 使用固定 252（交易日/年），未考虑实际统计时间范围

当前代码（optimizer_service.py:173）：
```python
p_volatility_sq = np.dot(weights.T, np.dot(cov_matrix, weights)) * 252
```

## Goals / Non-Goals

**Goals:**
- 修正波动率年化计算量纲不一致问题
- 使用月数/季度数作为年化因子（1m=12, 3m=4, 6m=2, 1y+=1）
- 保持 λ 参数的物理含义，使其在合理范围内（如 0.1~10）即可产生效果

**Non-Goals:**
- 不改变优化目标函数的基本形式（仍是最大化收益 - λ × 风险）
- 不引入新的外部依赖
- 不改变 API 接口和返回结果格式

## Decisions

### Decision 1: 年化因子计算方式

**选择**: 按月数计算年化因子
- `1m` → 12（一年有12个月）
- `3m` → 4（一年有4个季度）
- `6m` → 2（一年有2个半年）
- `1y` 及以上 → 1（已经是年）

**替代方案**:
- 按实际观测交易日数 `√(252/n)` 年化 → 未采用，因为波动率变化过于平滑
- 固定 252 → 已在使用，存在量纲问题

### Decision 2: 新增 get_annual_factor 函数

在 `portfolio_service.py` 新增 `get_annual_factor(period)` 函数：

```python
def get_annual_factor(period: Optional[str]) -> int:
    if not period:
        return 1
    num, unit = _parse_period(period)
    if unit == 'm':
        return 12 // num
    return 1
```

**原因**: 集中管理 period → 年化因子 的转换逻辑，便于维护

### Decision 3: calculate_volatility 增加 annual_factor 参数

```python
def calculate_volatility(daily_returns: List[float], annual_factor: int = 252) -> float:
    ...
    annualized_vol = daily_volatility * np.sqrt(annual_factor)
    return annualized_vol
```

**原因**: 需要根据统计时间范围动态调整年化因子，且需要追溯到所有调用处

### Decision 4: 传递 period 参数链路

```
optimize_max_return(period)
  └── maximize_return_objective(annual_factor)
  └── calculate_volatility(annual_factor)

optimize_with_constraints(period)
  └── maximize_return_objective(annual_factor)
  └── calculate_volatility(annual_factor)

evaluate_portfolio(period)
  └── calculate_portfolio_metrics(annual_factor)
        └── calculate_volatility(annual_factor)

calculate_single_etf_metrics(period)
  └── calculate_volatility(annual_factor)
```

## Risks / Trade-offs

- **风险**: 多个函数签名改变，可能影响其他调用方 → 已有确认所有调用处并同步修改
- **风险**: `1m` 数据不足30天时仍按12年化，可能不够精确 → 按用户要求，即使不足仍按月数年化
- **权衡**: 测试文件中的独立实现也需要同步修改 → 不影响生产代码，仅测试覆盖