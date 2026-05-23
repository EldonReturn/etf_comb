## Context

`OptimizerPanel` 组件提供组合优化界面，用户可设置波动率约束。后端已支持最大回撤约束，前端需添加对应的UI输入控件。

## Goals / Non-Goals

**Goals:**
- 在"优化约束"区域添加最大回撤限制输入框
- 与波动率约束并列显示
- 调用API时传递 `target_max_drawdown` 参数

**Non-Goals:**
- 不修改优化结果展示逻辑
- 不添加最大回撤相关的图表或指标

## Decisions

### 1. 控件样式
**决定**: 与现有的波动率输入框保持一致。

**理由**: 保持UI一致性，用户已熟悉现有控件的操作方式。

### 2. 数据传递
**决定**: `optimizePortfolio` API 函数添加 `target_max_drawdown` 参数。

**理由**: 后端已支持此参数，前端只需透传。

## Risks / Trade-offs

- **风险**: 用户可能同时设置波动率和回撤约束，但两个约束可能无解
- **缓解**: 后端会返回优化失败，UI显示错误信息

## Open Questions

- (none)