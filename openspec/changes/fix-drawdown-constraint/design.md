## Context

当前 ETF 组合优化系统使用 `scipy.optimize.minimize(method='SLSQP')` 求解最大收益组合，支持三个约束：权重和为 1、波动率上限、最大回撤上限。其中波动率是光滑函数（`sqrt(wᵀΣw)`），SLSQP 可以可靠处理。但最大回撤计算使用了 `np.maximum.accumulate` + `np.min`，导致约束函数在权重空间上产生不可微的"断层"，SLSQP 的有限差分梯度估算在这种函数上严重失真，最终优化器要么收敛到不满足约束的点，要么返回 success=False。

此外，优化后的权重经过 clamp→normalize→drop→renormalize 四步后处理，但从不重新验证回撤是否仍然满足目标。用户无法从优化结果直接看到实际回撤值（API 不返回），只能通过应用组合后在分析面板间接查看，造成"约束失效"的体验。

## Goals / Non-Goals

**Goals:**
- 将最大回撤约束从 SLSQP 硬约束改为罚项 + 迭代升温，消除非光滑函数对梯度优化的干扰
- 实现 CDaR (Conditional Drawdown at Risk) 作为回撤的平滑近似，提升梯度估算稳定性
- 优化结果 API 响应增加 `max_drawdown` 字段，让用户直接验证
- 后处理完成后验证回撤，超标时自动收紧约束重试

**Non-Goals:**
- 不更换优化器（继续使用 SLSQP）
- 不改变前端 UI（约束输入和 API 调用方式不变）
- 不修改波动率约束逻辑（波动率函数本身光滑，硬约束可靠）
- 不引入新依赖

## Decisions

### Decision 1: 罚项形式 → 二次罚项（Quadratic Penalty）

```
P(w) = max(0, CDaR(w) - target_mdd/100)²
```

**理由：**
- **线性罚项**：梯度恒定，SLSQP 可能"接受"少量 penalty 换取更高收益，约束形同虚设
- **二次罚项**：越违反推得越猛，自然收敛到边界附近；梯度在边界处为 0，不会过约束
- **屏障函数**（-log）：边界处梯度爆炸，SLSQP 步长控制差，容易在远处发散

**备选方案：** Augmented Lagrangian（乘子法）。理论更严格（精确收敛到约束边界），但需要外循环更新乘子，实现复杂度高。对于 ETF 数量 < 30 的场景，二次罚项 + 迭代升温已足够。

### Decision 2: 回撤平滑近似 → CDaR（α=0.05）

```python
def portfolio_cdar(weights, aligned_navs, alpha=0.05):
    # 计算所有时点的回撤序列
    drawdowns = [...]  # 同现有逻辑
    # 取最差 α% 的回撤平均值
    worst_n = max(1, int(len(drawdowns) * alpha))
    worst_drawdowns = np.sort(drawdowns)[:worst_n]
    return float(np.mean(worst_drawdowns))
```

**理由：**
- 比 `min(drawdowns)` 光滑（取均值 vs 取单个点），对权重微调不敏感
- 金融行业认可（类似 CVaR/Expected Shortfall 概念）
- 计算成本与 max drawdown 几乎相同（多一个 sort + mean）
- α=0.05 意味着关注最差 5% 时段的回撤，约 12 个交易日（250 天 × 5%），比单日最大回撤更稳健

**备选方案：**
- **Soft-Min**: `-1/α·log(mean(exp(-α·dd)))`。理论上光滑，但需要标定 α 参数，数值不稳定（exp 容易溢出）
- **Lᵖ 范数**: `(mean(|dd|ᵖ))^(1/p)`。p 越大越接近 max，但梯度也越差。需要额外参数。

### Decision 3: 惩罚系数策略 → 迭代升温（Iterative Gamma Scaling）

```
γ₀ = 0.5
for iter in 1..6:
    solve: min -(wᵀr) + γ·max(0, CDaR(w)-target)²
    s.t.: Σw=1, 0≤w≤1, vol≤target
    
    check: max_drawdown(w*) ≤ target_mdd*(1+ε)
    if satisfied: return w*
    
    γ ← γ × 2
    warm_start = w*
return best feasible or lowest violation
```

**理由：**
- γ 太小 → 约束不生效；γ 太大 → 只关心回撤、忽略收益。无法预先知道合适的值
- 迭代升温自动搜索合适的 γ：每轮用上一轮的最优解 warm-start，SLSQP 收敛极快
- 6 轮最多 6000 次迭代（每轮 1000），实际远少（warm-start 后 100-200 次就能收敛）

**备选方案：**
- **固定 γ**：不同 ETF 组合、不同时段需要不同的 γ，无法一个值通吃
- **自适应 γ**：SGD 风格的动态调整。复杂度高，在 SLSQP 这种黑盒优化器上不适用

### Decision 4: 约束类型分配

```
                   硬约束 (SLSQP)     软约束 (罚项)
                   ─────────────      ────────────
  Σw = 1               ✓                  
  0 ≤ w ≤ 1            ✓                  
  vol ≤ target         ✓ (光滑函数)        
  mdd ≤ target                            ✓ (非光滑 → 罚项)
```

**理由：** 波动率是光滑的二次型 `wᵀΣw`，SLSQP 硬约束完全没有梯度问题。只把出问题的回撤改为罚项，最小化改动。

### Decision 5: 后处理验证

优化完成后，用**真实 max_drawdown（非 CDaR）**验证最终权重：

```python
actual_mdd = portfolio_max_drawdown(final_weights, aligned_navs)
if target_mdd and abs(actual_mdd) > target_mdd/100 * 1.01:
    # 超标 > 1% tolerance → 再加一轮升温
    # 或标记 result.warning
```

**理由：** CDaR 是 max_drawdown 的上界近似（CDaR ≤ MDD，因为 MDD 是最差值）。CDaR 满足 ≤ target 不保证 MDD ≤ target。后处理验证用真实的 max_drawdown 作为保底。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| CDaR(α=0.05) ≤ target 但实际 MDD 稍超 target | 后处理验证用真实 MDD 兜底；必要时收紧 α 到 0.02 |
| 迭代升温在极端数据下不收敛（6 轮后仍未满足） | 返回最佳可行解 + warning message，不清算失败 |
| 二次罚项使问题变为非凸（局部最优而非全局最优） | SLSQP 已假设局部最优；对 ETF 组合（凸目标 + 非凸罚项）实际表现良好 |
| 新增 max_drawdown 字段可能影响前端类型定义 | 响应新增字段向下兼容，TypeScript 类型只需可选字段扩展 |

## Open Questions

- γ 的初始值 0.5 和翻倍因子 2 是否需要针对不同时间区段（1m vs 5y）做自适应调整？建议先用固定值，观察测试结果后再优化
- CDaR 的 α 参数是否需要暴露给用户（高级选项）？初期不暴露，保持简洁
