## Why

组合优化器当前使用均值-方差框架（收益-波动率），但用户希望加入最大回撤的考量。最大回撤是路径依赖的、非凸的指标，需要作为不等式约束来实现，而非直接加入目标函数。

## What Changes

- 在 `optimize_with_constraints` 函数中添加 `target_max_drawdown` 参数
- 新增 `portfolio_max_drawdown` 辅助函数计算给定权重的组合最大回撤
- 在 API 层 `OptimizeRequest` 中添加 `target_max_drawdown` 字段
- 支持与 `target_volatility` 同时使用，形成帕累托最优边界

## Capabilities

### New Capabilities
- `max-drawdown-constraint`: 在组合优化中加入最大回撤上限约束

### Modified Capabilities
- (none - 不修改现有 specs 的行为，只是扩展 optimizer_service 的功能)

## Impact

- **代码**: `backend/services/optimizer_service.py` - 新增约束逻辑
- **API**: `backend/main.py` - `OptimizeRequest` 新增字段
- **测试**: `backend/tests/` - 需添加最大回撤约束的单元测试