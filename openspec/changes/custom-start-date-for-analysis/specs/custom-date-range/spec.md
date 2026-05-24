## ADDED Requirements

### Requirement: Custom start date for analysis period
The system SHALL allow users to specify a custom start date for portfolio analysis and optimization instead of using predefined period strings.

#### Scenario: User selects custom start date in optimizer
- **WHEN** user enables custom start date mode and selects a date
- **THEN** the system SHALL use the selected date as the analysis period start when calling the optimize API
- **AND** the system SHALL calculate the period as the number of days from the selected date to the current date

#### Scenario: User selects date before any ETF inception date
- **WHEN** user selects a start date that is earlier than all selected ETFs' inception dates
- **THEN** the system SHALL use each ETF's actual first available NAV date as its individual period start
- **AND** the system SHALL display a warning that some ETFs have limited data for the selected period

#### Scenario: User selects future date
- **WHEN** user selects a start date that is in the future
- **THEN** the system SHALL display a validation error preventing submission
- **AND** the system SHALL not make an API request with invalid parameters

#### Scenario: User selects very short period
- **WHEN** user selects a start date resulting in fewer than 30 calendar days of data
- **THEN** the system SHALL display a warning that the analysis period may be too short for meaningful results

#### Scenario: User switches back to predefined period
- **WHEN** user unchecks the custom start date option
- **THEN** the system SHALL use the selected predefined period (1m, 3m, 6m, 1y, etc.) as before
- **AND** the custom date input SHALL be disabled

### Requirement: API accepts start_date parameter
The system SHALL accept an optional `start_date` parameter in ISO 8601 format (YYYY-MM-DD) for portfolio-related API endpoints.

#### Scenario: Optimize endpoint receives start_date
- **WHEN** client sends POST /api/portfolio/optimize with `start_date` field
- **THEN** the system SHALL parse the date and use it as the analysis period start
- **AND** the system SHALL ignore the `period` field when `start_date` is provided

#### Scenario: Evaluate endpoint receives start_date
- **WHEN** client sends POST /api/portfolio/evaluate with `start_date` field
- **THEN** the system SHALL calculate metrics from the specified start date to current date

#### Scenario: Compare endpoint receives start_date
- **WHEN** client sends POST /api/portfolio/compare with `start_date` field
- **THEN** the system SHALL apply the same start date to all portfolios being compared

### Requirement: Backward compatibility with period parameter
The system SHALL maintain backward compatibility with the existing `period` parameter when `start_date` is not provided.

#### Scenario: Request with only period parameter
- **WHEN** client sends a request with `period` but without `start_date`
- **THEN** the system SHALL behave exactly as before, using the predefined period interpretation

#### Scenario: Request with neither parameter
- **WHEN** client sends a request without `period` or `start_date`
- **THEN** the system SHALL default to a 1-year period (equivalent to `period=1y`)