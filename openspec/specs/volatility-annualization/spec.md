## ADDED Requirements

### Requirement: Volatility Annualization Using Monthly Factor

The system SHALL compute portfolio volatility using a time-period-based annualization factor instead of a fixed trading days factor.

#### Scenario: Annualization factor computed from monthly period
- **WHEN** `get_annual_factor("1m")` is called
- **THEN** it SHALL return `12`
- **WHEN** `get_annual_factor("3m")` is called
- **THEN** it SHALL return `4`
- **WHEN** `get_annual_factor("6m")` is called
- **THEN** it SHALL return `2`

#### Scenario: Annualization factor computed from yearly period
- **WHEN** `get_annual_factor("1y")` is called
- **THEN** it SHALL return `1`
- **WHEN** `get_annual_factor("2y")` is called
- **THEN** it SHALL return `1`

#### Scenario: Default annualization factor
- **WHEN** `get_annual_factor(None)` is called
- **THEN** it SHALL return `1`

### Requirement: calculate_volatility accepts annual_factor parameter

The `calculate_volatility` function SHALL accept an `annual_factor` parameter and use it for volatility annualization.

#### Scenario: Volatility computed with custom annual factor
- **WHEN** `calculate_volatility([0.01, -0.02, 0.015], 4)` is called on 3-month data
- **THEN** the result SHALL equal `daily_volatility * sqrt(4)`
- **WHEN** `calculate_volatility([0.01, -0.02, 0.015], 12)` is called on 1-month data
- **THEN** the result SHALL equal `daily_volatility * sqrt(12)`

#### Scenario: Volatility defaults to 252 for backward compatibility
- **WHEN** `calculate_volatility([0.01, -0.02, 0.015])` is called without annual_factor
- **THEN** the result SHALL equal `daily_volatility * sqrt(252)`

### Requirement: Portfolio optimization uses period-based annualization

The portfolio optimization functions SHALL pass the annualization factor derived from `period` to the volatility calculation.

#### Scenario: optimize_max_return uses correct annualization
- **WHEN** `optimize_max_return(["510300", "510500"], period="3m")` is called
- **THEN** the internal volatility calculation SHALL use `sqrt(4)` factor
- **AND** the objective function SHALL use `annual_factor=4`

#### Scenario: optimize_with_constraints uses correct annualization
- **WHEN** `optimize_with_constraints(["510300", "510500"], target_volatility=0.15, period="1m")` is called
- **THEN** the volatility constraint SHALL use `sqrt(12)` factor

#### Scenario: Evaluation functions use correct annualization
- **WHEN** `evaluate_portfolio({"510300": 0.6, "510500": 0.4}, period="6m")` is called
- **THEN** the returned volatility SHALL be computed with `sqrt(2)` factor