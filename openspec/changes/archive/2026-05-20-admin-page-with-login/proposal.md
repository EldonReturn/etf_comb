## Why

Need a secure admin backend page to monitor application activity and manage data synchronization. Currently there's no visibility into visit logs or ability to manually trigger ETF data sync operations.

## What Changes

- Add password-protected admin login page
- Add admin dashboard for ETF data synchronization management
- Implement session-based authentication for admin access

## Capabilities

### New Capabilities
- `admin-auth`: Admin login with password authentication and session management
- `etf-sync`: Manual trigger and monitor ETF data synchronization operations

### Modified Capabilities
- (none)

## Impact

- New `/admin/login` route for authentication
- New `/admin/dashboard` route for admin panel (protected)
- New API endpoint for sync triggering
- Session management with secure cookie-based authentication