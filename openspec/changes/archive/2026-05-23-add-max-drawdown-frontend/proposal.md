## Why

用户需要在组合优化界面设置最大回撤限制，后端 `optimize_with_constraints` 已支持 `target_max_drawdown` 参数，但前端界面尚未提供对应的输入控件。

## What Changes

- 在 `OptimizerPanel` 组件的"优化约束"区域添加最大回撤限制输入框
- 在 `optimizePortfolio` API 函数中添加 `target_max_drawdown` 参数
- 与现有波动率约束并列显示，用户可同时设置两个约束

## Capabilities

### New Capabilities
- `max-drawdown-constraint-ui`: 在优化器界面添加最大回撤约束输入控件

### Modified Capabilities
- (none - 扩展现有的优化器UI和API，不修改核心行为)

## Impact

- **前端组件**: `frontend/src/components/OptimizerPanel.tsx` - 添加输入控件
- **API函数**: `frontend/src/api/index.ts` - `optimizePortfolio` 添加参数
- **样式**: 可能需要调整CSS以适应新增的输入框