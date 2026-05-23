## 1. Add get_annual_factor Helper Function

- [x] 1.1 Add `get_annual_factor(period: Optional[str]) -> int` to `portfolio_service.py`
- [x] 1.2 Implement period-to-annual-factor mapping: 1m=12, 3m=4, 6m=2, 1y+=1

## 2. Modify calculate_volatility Function

- [x] 2.1 Add `annual_factor: int = 252` parameter to `calculate_volatility`
- [x] 2.2 Change `np.sqrt(TRADING_DAYS_PER_YEAR)` to `np.sqrt(annual_factor)`

## 3. Update calculate_volatility Callers in portfolio_service.py

- [x] 3.1 Add `annual_factor` parameter to `calculate_portfolio_metrics`
- [x] 3.2 Pass `get_annual_factor(period)` to `calculate_volatility` in `calculate_portfolio_metrics`
- [x] 3.3 Pass `get_annual_factor(period)` to `calculate_volatility` in `calculate_single_etf_metrics`
- [x] 3.4 Pass `get_annual_factor(period)` to `calculate_portfolio_metrics` in `evaluate_portfolio`

## 4. Modify maximize_return_objective in optimizer_service.py

- [x] 4.1 Add `annual_factor: int = 252` parameter to `maximize_return_objective`
- [x] 4.2 Change `* 252` to `* annual_factor` in volatility calculation

## 5. Update optimize_max_return Function

- [x] 5.1 Compute `annual_factor = get_annual_factor(period)` after parsing period
- [x] 5.2 Pass `annual_factor` to `maximize_return_objective` in minimize call
- [x] 5.3 Pass `annual_factor` to `calculate_volatility` after optimization

## 6. Update optimize_with_constraints Function

- [x] 6.1 Compute `annual_factor = get_annual_factor(period)`
- [x] 6.2 Change `* np.sqrt(252)` to `* np.sqrt(annual_factor)` in volatility constraint
- [x] 6.3 Pass `annual_factor` to `maximize_return_objective` in minimize call
- [x] 6.4 Pass `annual_factor` to `calculate_volatility` after optimization

## 7. Update Test File

- [x] 7.1 Add `annual_factor` parameter to `TestVolatility.calculate_volatility`
- [x] 7.2 Update test cases to use appropriate annualization factors