## ADDED Requirements

### Requirement: CDaR (Conditional Drawdown at Risk) calculation

The system SHALL provide a function to compute the Conditional Drawdown at Risk (CDaR) for a given portfolio weight configuration as a smooth approximation of maximum drawdown.

#### Scenario: CDaR computed from aligned NAV series with default alpha
- **WHEN** `portfolio_cdar(weights=[0.6, 0.4], aligned_navs=[[1.0, 1.1, 0.95, 0.90, 0.85], [1.0, 1.05, 1.0, 0.98, 1.02]])` is called without alpha
- **THEN** the function SHALL compute the weighted portfolio drawdown series
- **AND** SHALL sort the drawdown series in ascending order
- **AND** SHALL return the mean of the worst 5% of drawdown values
- **AND** the returned value SHALL be negative (e.g., -0.08 for -8% average worst drawdown)

#### Scenario: CDaR with custom alpha parameter
- **WHEN** `portfolio_cdar(weights=[0.5, 0.5], aligned_navs=navs, alpha=0.10)` is called
- **THEN** the function SHALL use the worst 10% of drawdown values in the average

#### Scenario: CDaR is always less negative than or equal to maximum drawdown
- **WHEN** `portfolio_cdar(weights, aligned_navs)` and `portfolio_max_drawdown(weights, aligned_navs)` are called with the same inputs
- **THEN** CDaR SHALL be greater than or equal to max drawdown (i.e., CDaR ≥ MDD, since both are negative)

#### Scenario: CDaR with single-day NAV series
- **WHEN** `portfolio_cdar(weights, aligned_navs=[[1.0, 1.05]])` is called
- **THEN** the function SHALL return 0.0

### Requirement: Drawdown penalty term in objective function

The system SHALL provide a penalty-based objective function that incorporates drawdown as a soft constraint using a quadratic penalty on CDaR violations.

#### Scenario: Penalty is zero when CDaR is within target
- **WHEN** `drawdown_penalty_objective(weights, returns, cov_matrix, risk_aversion, annual_factor, aligned_navs, gamma=1.0, target_mdd=0.15)` is called
- **AND** the portfolio CDaR is -0.10 (10% drawdown, within 15% target)
- **THEN** the penalty term SHALL be zero
- **AND** the objective value SHALL equal `-(portfolio_return - risk_aversion * portfolio_variance)`

#### Scenario: Penalty is positive quadratic when CDaR exceeds target
- **WHEN** `drawdown_penalty_objective(weights, returns, cov, 0.0, 252, navs, gamma=2.0, target_mdd=0.10)` is called
- **AND** the portfolio CDaR is -0.20 (20% drawdown, exceeds 10% target)
- **THEN** the penalty term SHALL be `2.0 * max(0, 0.20 - 0.10)^2 = 2.0 * 0.01 = 0.02`
- **AND** the objective SHALL be `-(p_return) + 0.02`

### Requirement: Iterative gamma scaling optimization

The system SHALL provide an optimization function that iteratively adjusts the penalty coefficient gamma to find weights satisfying the drawdown constraint.

#### Scenario: Constraint satisfied on first iteration
- **WHEN** `optimize_with_drawdown_penalty(["510300", "510500"], target_max_drawdown=15.0, period="1y")` is called
- **AND** the initial gamma produces weights with max_drawdown ≤ 15%
- **THEN** the function SHALL return after the first iteration
- **AND** `result.success` SHALL be `true`
- **AND** `result.iterations` SHALL be 1

#### Scenario: Gamma increases when constraint not satisfied
- **WHEN** the first iteration produces weights with max_drawdown > target
- **THEN** gamma SHALL be multiplied by 2 for the next iteration
- **AND** the previous iteration's weights SHALL be used as the initial guess (warm-start)

#### Scenario: Maximum iterations reached without satisfying constraint
- **WHEN** 6 iterations have been performed without finding weights satisfying the drawdown constraint
- **THEN** the function SHALL return the best solution found (lowest CDaR violation)
- **AND** `result.success` SHALL be `true`
- **AND** `result.message` SHALL include a warning about the drawdown constraint

#### Scenario: Iterative optimization preserves other constraints
- **WHEN** `optimize_with_drawdown_penalty(["510300", "510500"], target_volatility=0.20, target_max_drawdown=15.0)` is called
- **THEN** the volatility constraint SHALL be enforced as a hard SLSQP constraint
- **AND** the drawdown constraint SHALL be enforced via the iterative penalty mechanism

### Requirement: Post-optimization drawdown verification

The system SHALL verify the actual maximum drawdown of the final weights against the target after optimization completes, using the non-approximated max drawdown function.

#### Scenario: Weights pass verification
- **WHEN** post-optimization verification checks max_drawdown against target
- **AND** `abs(max_drawdown) ≤ target / 100 * 1.01` (within 1% tolerance)
- **THEN** verification SHALL pass without additional action

#### Scenario: Weights fail verification due to CDaR-MDD gap
- **WHEN** post-optimization verification finds `abs(max_drawdown) > target / 100 * 1.01`
- **AND** fewer than 6 iterations have been performed
- **THEN** gamma SHALL be multiplied by 2 and one more iteration SHALL be executed
- **AND** the process SHALL repeat until verification passes or max iterations reached

### Requirement: Optimization result includes max_drawdown

The optimization result SHALL include the computed `max_drawdown` of the final portfolio weights.

#### Scenario: Successful optimization returns max_drawdown
- **WHEN** `optimize_with_drawdown_penalty(...)` returns a successful result
- **THEN** `result.max_drawdown` SHALL be a float representing the portfolio's actual maximum drawdown percentage
- **AND** the value SHALL be negative (e.g., -12.5 for -12.5% drawdown)

#### Scenario: Failed optimization returns max_drawdown as 0.0
- **WHEN** optimization fails before producing valid weights
- **THEN** `result.max_drawdown` SHALL be 0.0