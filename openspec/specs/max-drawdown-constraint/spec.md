## ADDED Requirements

### Requirement: Portfolio maximum drawdown calculation

The system SHALL calculate the maximum drawdown for a given portfolio weight configuration.

#### Scenario: Maximum drawdown computed from aligned NAV series
- **WHEN** `portfolio_max_drawdown(weights=[0.6, 0.4], aligned_navs=[[1.0, 1.1, 0.95], [1.0, 1.05, 1.0]])` is called
- **THEN** the result SHALL be the drawdown of the weighted portfolio NAV series
- **AND** the returned value SHALL be negative (e.g., -0.05 for -5% drawdown)

#### Scenario: Single ETF portfolio drawdown
- **WHEN** `portfolio_max_drawdown(weights=[1.0], aligned_navs=[[1.0, 1.2, 0.9]])` is called
- **THEN** the result SHALL equal the drawdown of the single NAV series

## MODIFIED Requirements

### Requirement: Maximum drawdown constraint in optimization

The `optimize_with_constraints` function SHALL accept a `target_max_drawdown` parameter and enforce it via a penalty mechanism (iterative gamma scaling with CDaR-based quadratic penalty) rather than as a hard SLSQP inequality constraint.

#### Scenario: Drawdown constraint satisfied via penalty
- **WHEN** `optimize_with_constraints(["510300", "510500"], target_max_drawdown=15.0, period="1y")` is called
- **AND** there exists a feasible portfolio with maximum drawdown ≤ 15%
- **THEN** the optimization SHALL return weights satisfying the constraint via the penalty mechanism
- **AND** `result.success` SHALL be `true`
- **AND** `result.max_drawdown` SHALL be included in the response

#### Scenario: Drawdown constraint infeasible
- **WHEN** `optimize_with_constraints(["510300", "510500"], target_max_drawdown=1.0, period="1y")` is called
- **AND** no feasible portfolio has maximum drawdown ≤ 1%
- **THEN** the optimization SHALL return the best-effort solution
- **AND** `result.success` SHALL be `true`
- **AND** `result.message` SHALL indicate the drawdown constraint could not be fully satisfied

#### Scenario: Drawdown constraint with volatility constraint combined
- **WHEN** `optimize_with_constraints(["510300", "510500"], target_volatility=0.10, target_max_drawdown=8.0, period="6m")` is called
- **THEN** the optimization SHALL find weights attempting to satisfy BOTH constraints
- **AND** the volatility constraint SHALL be enforced as a hard SLSQP constraint
- **AND** the drawdown constraint SHALL be enforced as a penalty term

### Requirement: API accepts maximum drawdown parameter

The portfolio optimization API endpoint SHALL accept `target_max_drawdown` in the request body and SHALL include `max_drawdown` in the optimization response.

#### Scenario: API accepts drawdown constraint
- **WHEN** POST `/api/portfolio/optimize` with body `{"etf_codes": ["510300"], "target_max_drawdown": 10.0}` is called
- **THEN** the request SHALL be validated successfully
- **AND** the optimization SHALL use the penalty-based drawdown enforcement

#### Scenario: API accepts both volatility and drawdown constraints
- **WHEN** POST `/api/portfolio/optimize` with body `{"etf_codes": ["510300", "510500"], "target_volatility": 12.0, "target_max_drawdown": 8.0}` is called
- **THEN** both constraints SHALL be passed to the optimizer

#### Scenario: API response includes max_drawdown
- **WHEN** POST `/api/portfolio/optimize` returns successfully
- **THEN** the response body SHALL include a `max_drawdown` field containing the portfolio's actual maximum drawdown
- **AND** the value SHALL be a negative float representing percentage (e.g., -8.5 for -8.5%)