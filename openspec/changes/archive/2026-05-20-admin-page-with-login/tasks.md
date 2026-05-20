## 1. Backend - Admin Auth

- [x] 1.1 Create admin router in backend/routes/admin.py with login, logout, dashboard, sync endpoints
- [x] 1.2 Add session authentication using FastAPI's SessionMiddleware with configurable admin password
- [x] 1.3 Add environment variables ADMIN_PASSWORD and SESSION_SECRET to backend

## 2. Backend - ETF Sync Endpoint

- [x] 2.1 Add sync state tracking (in-memory or database flag)
- [x] 2.2 Implement POST /admin/sync endpoint that calls etf_data_service.sync_all()
- [x] 2.3 Implement GET /admin/sync/status endpoint returning current status
- [x] 2.4 Handle concurrent sync requests with 409 response

## 3. Frontend - Admin Login Page

- [x] 3.1 Create frontend/src/pages/admin/Login.tsx with password form
- [x] 3.2 Handle login success/failure with appropriate UI feedback
- [x] 3.3 Store session in localStorage or cookie (httpOnly preferred if possible)

## 4. Frontend - Admin Dashboard

- [x] 4.1 Create frontend/src/pages/admin/Dashboard.tsx with protected route
- [x] 4.2 Add "Trigger Sync" button with loading state
- [x] 4.3 Add sync status display with last sync timestamp
- [x] 4.4 Add time range selector for sync period

## 5. Frontend - Routing

- [x] 5.1 Add /admin/login route in App.tsx (using hash-based routing #admin)
- [x] 5.2 Add /admin/dashboard route in App.tsx (protected)
- [x] 5.3 Create AuthGuard component to redirect unauthenticated users to login
- [x] 5.4 Create API functions for admin endpoints in frontend/src/api/index.ts (using existing /api/admin/* endpoints)

## 6. Main Page Cleanup

- [x] 6.1 Remove sync button from main toolbar (moved to admin dashboard)
- [x] 6.2 Remove syncing state and handleSync function from App.tsx