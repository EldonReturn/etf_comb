## Context

组合优化器 (`optimizer_service.py`) 目前使用均值-方差框架，目标函数为 `maximize_return_objective = -(收益 - λ × 波动率²)`。用户提出需要加入最大回撤（Maximum Drawdown）的考量。

最大回撤的特点：
- **路径依赖**: 需要知道组合净值的历史走势
- **非凸**: 无法像波动率那样加到目标函数里（不能求导）
- **约束形式**: 最适合作为不等式约束 `actual_drawdown ≤ target_drawdown`

## Goals / Non-Goals

**Goals:**
- 在 `optimize_with_constraints` 中添加 `target_max_drawdown` 参数
- 新增辅助函数计算给定权重的组合最大回撤
- 支持与 `target_volatility` 联合约束

**Non-Goals:**
- 不修改现有的 `maximize_return_objective` 目标函数
- 不添加最小回撤约束
- 不在优化结果中返回实际最大回撤（已有 evaluate_portfolio 提供此功能）

## Decisions

### 1. 实现方式：不等式约束
**决定**: 将 `target_max_drawdown` 作为不等式约束添加。

**理由**: 最大回撤非凸，不能加到目标函数里。不等式约束是 scipy.optimize SLSQP 支持的标准形式。

**替代方案考虑**:
- 将回撤惩罚加入目标函数 → 非凸，局部最优解不是全局最优
- 使用启发式算法（如遗传算法） → 计算成本高，SLSQP 已足够

### 2. 约束函数设计
**约束形式**: `target_max_drawdown/100 - portfolio_max_drawdown(weights, aligned_navs) ≥ 0`

`portfolio_max_drawdown` 函数内部：
1. 根据权重计算组合净值序列 `portfolio_navs`
2. 计算 rolling max 和 drawdown
3. 返回最小 drawdown（负值，如 -0.15 表示 -15%）

### 3. 数值约定
- API 输入 `target_max_drawdown: float` = 百分比（正数，如 15 表示 15%）
- 内部转换为小数：`target_max_drawdown / 100`

## Risks / Trade-offs

**[风险]**: 约束函数计算成本高
- 每次优化迭代都需要计算组合净值并求最大回撤
- **缓解**: 约束仅在满足条件时激活；ETF 数量通常 ≤ 10

**[风险]**: 可能无解
- 如果 `target_max_drawdown` 设置过低，可能找不到满足约束的组合
- **缓解**: scipy.optimize 会返回失败状态，message 说明原因

## Open Questions

- 是否需要在 `OptimizationResult` 中返回实际最大回撤？（目前可复用 `evaluate_portfolio`）
- 是否需要暴露 `min_max_drawdown` 约束（避免过于保守）？