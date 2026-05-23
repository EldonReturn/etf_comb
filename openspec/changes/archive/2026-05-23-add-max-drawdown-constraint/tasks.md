## 1. Backend - Add portfolio_max_drawdown helper function

- [x] 1.1 Add `portfolio_max_drawdown(weights, aligned_navs)` function in `optimizer_service.py`
- [x] 1.2 Function calculates weighted portfolio NAV series and returns minimum drawdown (negative value)

## 2. Backend - Modify optimize_with_constraints

- [x] 2.1 Add `target_max_drawdown: Optional[float] = None` parameter to function signature
- [x] 2.2 Add inequality constraint when `target_max_drawdown` is provided
- [x] 2.3 Pass `aligned_navs` to constraint function (captured via closure)

## 3. Backend - Update API endpoint

- [x] 3.1 Add `target_max_drawdown: Optional[float] = None` to `OptimizeRequest` in `main.py`
- [x] 3.2 Pass parameter to `optimize_with_constraints` call

## 4. Testing

- [x] 4.1 Add unit test for `portfolio_max_drawdown` function
- [ ] 4.2 Add test for drawdown constraint satisfied scenario (requires integration test)
- [ ] 4.3 Add test for drawdown constraint infeasible scenario (requires integration test)
- [ ] 4.4 Add test for combined volatility and drawdown constraints (requires integration test)

## 5. Verification

- [x] 5.1 Run `pytest backend/tests/` to verify all tests pass (189 passed, 1 pre-existing failure unrelated to this change)