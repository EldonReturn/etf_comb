## 1. Backend Auth Route

- [x] 1.1 Create `backend/routes/auth.py` with login/logout/session verification
- [x] 1.2 Add `FRONTEND_PASSWORD` env var with hash verification
- [x] 1.3 Create `frontend_session` cookie with 1-hour expiry
- [x] 1.4 Export `verify_session` and `require_auth` for API protection

## 2. Backend Main App

- [x] 2.1 Include auth router in `main.py` at `/api/auth`
- [x] 2.2 Add `Depends(require_auth)` to all `/api/*` endpoints (except `/api/auth/login`)
- [x] 2.3 Add `GET /api/auth/status` endpoint to check login state

## 3. Frontend Login Page

- [x] 3.1 Create `frontend/src/pages/Login.tsx` with password input
- [x] 3.2 Connect to `POST /api/auth/login`
- [x] 3.3 Store `frontend_logged_in` in localStorage on success
- [x] 3.4 Show error message on wrong password

## 4. Frontend App Integration

- [x] 4.1 Add `frontendLoggedIn` state in `App.tsx`
- [x] 4.2 Check localStorage on mount to restore login state
- [x] 4.3 Show `<Login />` instead of main app when not logged in
- [x] 4.4 Call `/api/auth/status` on mount to validate session with backend

## 5. Verify

- [x] 5.1 Verify unauthenticated requests to `/api/*` return 401
- [x] 5.2 Verify login with correct password shows main app
- [x] 5.3 Verify login with wrong password shows error
- [x] 5.4 Verify admin login still works independently at `#admin`