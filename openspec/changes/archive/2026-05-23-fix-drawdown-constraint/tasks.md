## 1. CDaR Calculation

- [x] 1.1 Implement `portfolio_cdar(weights, aligned_navs, alpha=0.05)` in `optimizer_service.py` — compute drawdown series, sort, return mean of worst alpha%
- [x] 1.2 Handle edge cases: less than 2 NAV points returns 0.0, empty input returns 0.0
- [x] 1.3 Write unit tests in `test_services.py`: basic CDaR, custom alpha, CDaR ≥ MDD property, empty/edge cases

## 2. Penalty Objective Function

- [x] 2.1 Implement `drawdown_penalty_objective(weights, returns, cov_matrix, risk_aversion, annual_factor, aligned_navs, gamma, target_mdd)` — combines existing return objective with CDaR quadratic penalty
- [x] 2.2 Ensure penalty is zero when CDaR ≤ target, positive quadratic when violated
- [x] 2.3 Write unit tests: penalty=0 when satisfied, penalty>0 when violated, penalty scales with gamma

## 3. Iterative Gamma Scaling Optimizer

- [x] 3.1 Implement `optimize_with_drawdown_penalty(etf_codes, target_max_drawdown, ...)` — iterative loop with gamma doubling
- [x] 3.2 Implement warm-start: use previous iteration's optimal weights as initial guess
- [x] 3.3 Implement max iterations cap (6) with graceful degradation (return best effort)
- [x] 3.4 Keep hard constraints (sum=1, bounds, volatility) in SLSQP, only drawdown in penalty
- [x] 3.5 Write unit tests: constraint satisfied on first iteration, gamma increases on violation, max iterations reached, volatility constraint preserved

## 4. Post-Optimization Verification

- [x] 4.1 Add real max_drawdown verification step after each iteration using `portfolio_max_drawdown`
- [x] 4.2 If CDaR satisfied but MDD exceeds target by >1%, trigger extra iteration with doubled gamma
- [x] 4.3 Write unit tests: CDaR passes but MDD fails → extra iteration; both pass → no extra iteration

## 5. OptimizationResult and API Update

- [x] 5.1 Add `max_drawdown: float` field to `OptimizationResult` dataclass
- [x] 5.2 Add `iterations: int` field to `OptimizationResult` for observability
- [x] 5.3 Update `optimize_with_constraints` to call the penalty optimizer when `target_max_drawdown` is set
- [x] 5.4 Update API response in `main.py` to include `max_drawdown` and `iterations` in JSON
- [x] 5.5 Ensure all return paths set `max_drawdown` (success, failure, edge cases)

## 6. Frontend Types Update

- [x] 6.1 Add optional `max_drawdown: number` to `OptimizationResult` interface in `api/index.ts`
- [x] 6.2 Display `max_drawdown` in `OptimizerPanel.tsx` result section alongside other metrics

## 7. Integration Testing

- [x] 7.1 Write integration test: optimize with drawdown constraint, verify response includes max_drawdown
- [x] 7.2 Write integration test: verify penalty optimizer produces same or better weights than hard constraint for feasible scenarios
- [x] 7.3 Run full test suite (`pytest`) and verify no regressions