## ADDED Requirements

### Requirement: Manual ETF sync trigger
The system SHALL provide an endpoint POST /admin/sync that triggers ETF data synchronization when requested by an authenticated admin.

#### Scenario: Trigger sync successfully
- **WHEN** authenticated admin requests POST /admin/sync
- **THEN** system initiates ETF data synchronization process
- **AND** system returns 200 status with JSON {"status": "started", "message": "Sync initiated"}

#### Scenario: Sync already in progress
- **WHEN** authenticated admin requests POST /admin/sync while another sync is already running
- **THEN** system returns 409 status with JSON {"error": "Sync already in progress"}

### Requirement: Sync status endpoint
The system SHALL provide an endpoint GET /admin/sync/status that returns the current synchronization status.

#### Scenario: Get sync status when idle
- **WHEN** authenticated admin requests GET /admin/sync/status
- **THEN** system returns 200 status with JSON {"status": "idle", "last_sync": "<timestamp>", "last_result": "<success|failed>"}