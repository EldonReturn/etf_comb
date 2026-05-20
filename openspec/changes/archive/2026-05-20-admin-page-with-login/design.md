## Context

This project is a React/Vite frontend with FastAPI backend for ETF portfolio optimization. The backend is Python-based with database models using SQLAlchemy. The frontend currently has no admin section.

Admin functionality needed:
- Secure login with password
- Manually trigger ETF data synchronization

## Goals / Non-Goals

**Goals:**
- Simple password-based admin authentication (no user management needed)
- Session-based auth using secure httpOnly cookies
- Provide button to trigger ETF data sync operation
- Show sync status/history

**Non-Goals:**
- User registration or multi-user support
- Role-based permissions beyond single admin
- Visit logging functionality
- Real-time log streaming

## Decisions

1. **Backend route: `/admin/login` for auth, `/admin/dashboard` for panel**
   - Simplicity: separate namespace keeps admin routes distinct
   - Dashboard protected by session middleware

2. **Session auth using existing Python session mechanism**
   - Use FastAPI's built-in session middleware with secure cookies
   - Store admin password hash in environment variable `ADMIN_PASSWORD_HASH`
   - Default password can be set via `ADMIN_PASSWORD` env var (hashed on startup if not set)

3. **ETF sync via existing etf_data_service**
   - Call `etf_data_service.sync_all()` or similar method
   - Return success/failure status to admin dashboard

4. **Frontend: Simple React components in `/admin` route**
   - Login form component
   - Dashboard with sync button and status display
   - Use existing API fetch patterns from `frontend/src/api/index.ts`

5. **Login page design**
   - Centered card layout (no header/toolbar, standalone page)
   - Single password input with lock icon
   - Primary color submit button
   - Error message display (red background)
   - No "remember me" checkbox
   - No "forgot password" link

## Risks / Trade-offs

- [Risk] Hardcoded admin password → [Mitigation] Use strong env var, force change on first deploy
- [Risk] Session hijacking → [Mitigation] httpOnly, secure cookies; short session expiry
- [Risk] Sync blocking UI → [Mitigation] Make sync API async, show loading state