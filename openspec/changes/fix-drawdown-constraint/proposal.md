## Why

组合优化中最大回撤约束使用了 SLSQP 硬约束，但由于回撤函数（`np.maximum.accumulate` + `np.min`）不可微，SLSQP 的有限差分梯度估算严重失真，导致优化器返回的权重不满足回撤限制。此外，优化后的权重经过 4 步后处理（clamp、normalize、drop、renormalize）后不再验证约束是否仍然成立。

## What Changes

- 将最大回撤从 SLSQP 硬约束改为**二次罚项**，纳入目标函数，避免非光滑约束导致的梯度误判
- 引入**迭代升温机制**（Iterative Gamma Scaling），自动调整惩罚系数直到回撤满足目标
- 实现**CDaR (Conditional Drawdown at Risk)** 作为回撤的平滑近似，替代不可微的 `min(drawdowns)`
- 在优化结果返回前增加**后处理验证**，若最终回撤超标则标记 warning 或收紧约束重试
- 优化结果 API 响应中新增 `max_drawdown` 字段，使用户可以直接验证约束是否被遵守

## Capabilities

### New Capabilities
- `drawdown-penalty-optimizer`: 基于二次罚项 + 迭代升温的回撤约束优化引擎，使用 CDaR 平滑近似替代原始最大回撤计算

### Modified Capabilities
- `max-drawdown-constraint`: 回撤约束的底层实现从 SLSQP 不等式约束改为罚项 + 迭代升温 + 后处理验证策略

## Impact

- `backend/services/optimizer_service.py`: 新增 CDaR 计算函数、罚项目标函数、迭代升温优化函数；修改 `optimize_with_constraints` 移除硬约束改用罚项
- `backend/main.py`: `OptimizeRequest` 模型不变，优化 API 响应增加 `max_drawdown` 字段
- Specs: `max-drawdown-constraint` 的约束实现需求更新
- 前端不变：`OptimizerPanel` 和 `api/index.ts` 无需修改（API 参数兼容，响应新增字段向下兼容）
