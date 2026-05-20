## 1. Modify save_etf_nav_to_db for batch support

- [x] 1.1 Update save_etf_nav_to_db signature to accept list of codes and their DataFrames
- [x] 1.2 Implement batch mapping generation for multiple ETFs
- [x] 1.3 Add bulk_insert_mappings call with accumulated mappings
- [x] 1.4 Ensure function returns total records saved

## 2. Implement buffer-based batch writing in sync_all_etf_data

- [x] 2.1 Initialize NAV buffer dictionary to accumulate records by ETF code
- [x] 2.2 Implement batch flush logic when buffer exceeds 5000 records
- [x] 2.3 Modify ETF processing loop to accumulate NAV records instead of immediate write
- [x] 2.4 Add final flush call after processing all ETFs
- [x] 2.5 Ensure progress_callback fires correctly during batch processing

## 3. Optimize session management in sync_all_etf_data

- [x] 3.1 Use single database session for entire sync operation
- [x] 3.2 Move ETF info save and NAV batch writes under same session
- [x] 3.3 Handle session cleanup in finally block

## 4. Verify and test

- [x] 4.1 Run existing tests to ensure no regressions
- [x] 4.2 Verify sync completes without errors
- [x] 4.3 Confirm stats returned have correct structure (etf_count, nav_count, errors)