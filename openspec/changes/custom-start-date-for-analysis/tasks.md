## 1. Backend Core - Date Parsing

- [ ] 1.1 Modify `period_to_days()` in `backend/services/portfolio_service.py` to detect and parse ISO 8601 date format (YYYY-MM-DD)
- [ ] 1.2 Add `parse_date_string()` function to differentiate between period strings (e.g., "1m") and date strings (e.g., "2020-01-01")
- [ ] 1.3 Add `date_to_days()` function to calculate days from a custom start date to today

## 2. Backend - NAV Data Fetching

- [ ] 2.1 Modify `get_etf_nav_series()` to accept optional `start_date` parameter
- [ ] 2.2 Modify `get_etf_nav_dates()` to accept optional `start_date` parameter
- [ ] 2.3 Add data availability check for ETFs with inception dates after the requested start date

## 3. Backend - API Endpoints

- [ ] 3.1 Update `/portfolio/optimize` endpoint in `backend/main.py` to accept `start_date` in request body
- [ ] 3.2 Update `/portfolio/evaluate` endpoint to accept `start_date` in request body
- [ ] 3.3 Update `/portfolio/compare` endpoint to accept `start_date` in request body
- [ ] 3.4 Add validation for `start_date` (must be valid date, not in future, at least 30 days before today)

## 4. Frontend - API Layer

- [ ] 4.1 Update `optimizePortfolio()` in `frontend/src/api/index.ts` to accept and send `start_date` parameter
- [ ] 4.2 Update `evaluatePortfolio()` to accept and send `start_date` parameter
- [ ] 4.3 Update `comparePortfolios()` to accept and send `start_date` parameter

## 5. Frontend - UI Components

- [ ] 5.1 Add custom start date checkbox and date input to `OptimizerPanel.tsx`
- [ ] 5.2 Add date input validation (max = today, min = reasonable past date like 2010-01-01)
- [ ] 5.3 Implement enable/disable logic for custom date mode vs predefined period mode
- [ ] 5.4 Add warning display for insufficient data period (< 30 days)
- [ ] 5.5 Update any other components that use period selection for consistency