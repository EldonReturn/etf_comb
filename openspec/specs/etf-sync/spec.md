## Purpose

<!-- TBD: Brief description of this capability -->

## Requirements

### Requirement: Batch NAV history persistence
The system SHALL persist ETF NAV history records in batches during sync operations to minimize database transaction overhead.

#### Scenario: Batch insert during sync
- **WHEN** sync_all_etf_data is called
- **THEN** the system SHALL accumulate NAV records in memory and write them in batches not exceeding 5000 records per transaction

#### Scenario: Session reuse
- **WHEN** sync_all_etf_data is processing multiple ETFs
- **THEN** the system SHALL reuse the same database session for both data fetch and persistence phases to avoid session creation overhead

### Requirement: Efficient sync progress reporting
The system SHALL report sync progress at reasonable intervals during batch operations, ensuring users receive timely feedback.

#### Scenario: Progress callback during batch write
- **WHEN** batch of ETFs is being written to database
- **THEN** the system SHALL invoke progress_callback with current count and total count for each ETF processed

### Requirement: Sync statistics reporting
The system SHALL return accurate sync statistics upon completion.

#### Scenario: Successful sync completion
- **WHEN** sync_all_etf_data completes successfully
- **THEN** the system SHALL return dict containing etf_count (total ETFs), nav_count (total NAV records persisted), and errors (failed ETF count)

#### Scenario: Partial failure handling
- **WHEN** sync_all_etf_data encounters errors for some ETFs
- **THEN** the system SHALL continue processing remaining ETFs and report error count in stats

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