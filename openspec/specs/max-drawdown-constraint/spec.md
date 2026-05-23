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

### Requirement: Maximum drawdown constraint in optimization

The `optimize_with_constraints` function SHALL accept a `target_max_drawdown` parameter and enforce it as an inequality constraint.

#### Scenario: Drawdown constraint satisfied
- **WHEN** `optimize_with_constraints(["510300", "510500"], target_max_drawdown=15.0, period="1y")` is called
- **AND** there exists a feasible portfolio with maximum drawdown ≤ 15%
- **THEN** the optimization SHALL return weights satisfying the constraint
- **AND** `result.success` SHALL be `true`

#### Scenario: Drawdown constraint infeasible
- **WHEN** `optimize_with_constraints(["510300", "510500"], target_max_drawdown=1.0, period="1y")` is called
- **AND** no feasible portfolio has maximum drawdown ≤ 1%
- **THEN** the optimization SHALL return `result.success=false`
- **AND** `result.message` SHALL indicate the constraint could not be satisfied

#### Scenario: Drawdown constraint with volatility constraint combined
- **WHEN** `optimize_with_constraints(["510300", "510500"], target_volatility=0.10, target_max_drawdown=8.0, period="6m")` is called
- **THEN** the optimization SHALL find weights satisfying BOTH constraints
- **AND** `result.success` SHALL be `true` if a feasible solution exists

### Requirement: API accepts maximum drawdown parameter

The portfolio optimization API endpoint SHALL accept `target_max_drawdown` in the request body.

#### Scenario: API accepts drawdown constraint
- **WHEN** POST `/api/portfolio/optimize` with body `{"etf_codes": ["510300"], "target_max_drawdown": 10.0}` is called
- **THEN** the request SHALL be validated successfully
- **AND** the optimization SHALL use the drawdown constraint

#### Scenario: API accepts both volatility and drawdown constraints
- **WHEN** POST `/api/portfolio/optimize` with body `{"etf_codes": ["510300", "510500"], "target_volatility": 12.0, "target_max_drawdown": 8.0}` is called
- **THEN** both constraints SHALL be passed to the optimizer