## ADDED Requirements

### Requirement: Max drawdown constraint input field

The optimizer panel SHALL display an input field for maximum drawdown constraint in the constraint section.

#### Scenario: Input field displayed
- **WHEN** user views the optimizer panel
- **THEN** there SHALL be an input field labeled "目标最大回撤上限 (%)" in the constraint section

#### Scenario: Input accepts numeric values
- **WHEN** user enters "15" in the max drawdown input field
- **THEN** the value SHALL be stored as 15

#### Scenario: Input can be cleared
- **WHEN** user clears the max drawdown input field
- **THEN** the constraint SHALL not be sent to the API (treated as no constraint)

### Requirement: Max drawdown parameter passed to API

The `optimizePortfolio` function SHALL accept and pass the `target_max_drawdown` parameter to the backend API.

#### Scenario: API called with max drawdown constraint
- **WHEN** user sets max drawdown to 15 and clicks optimize
- **THEN** the API request SHALL include `"target_max_drawdown": 15`

#### Scenario: API called without max drawdown constraint
- **WHEN** user leaves max drawdown input empty and clicks optimize
- **THEN** the API request SHALL NOT include `target_max_drawdown` field