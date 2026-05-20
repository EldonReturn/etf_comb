## ADDED Requirements

### Requirement: Admin login with password
The system SHALL provide a login endpoint at POST /admin/login that accepts a password and returns a session cookie upon success.

#### Scenario: Successful login
- **WHEN** admin submits correct password via POST /admin/login with JSON body {"password": "<valid_password>"}
- **THEN** system returns 200 status with Set-Cookie header containing session token

#### Scenario: Failed login with wrong password
- **WHEN** admin submits incorrect password via POST /admin/login with JSON body {"password": "<invalid_password>"}
- **THEN** system returns 401 status with JSON body {"error": "Invalid credentials"}

### Requirement: Protected admin endpoints
The system SHALL reject requests to /admin/dashboard and other admin routes when no valid session cookie is present.

#### Scenario: Access dashboard without session
- **WHEN** user requests GET /admin/dashboard without valid session cookie
- **THEN** system returns 401 status with JSON body {"error": "Unauthorized"}

#### Scenario: Access dashboard with valid session
- **WHEN** user requests GET /admin/dashboard with valid session cookie
- **THEN** system returns 200 status with admin dashboard HTML/JSON

### Requirement: Session timeout
The admin session SHALL expire after 1 hour of inactivity.

#### Scenario: Session expires after timeout
- **WHEN** admin session is older than 1 hour
- **THEN** system treats the session as invalid and returns 401 on protected endpoints

### Requirement: Logout functionality
The system SHALL provide a logout endpoint at POST /admin/logout that invalidates the session.

#### Scenario: Successful logout
- **WHEN** admin requests POST /admin/logout with valid session cookie
- **THEN** system returns 200 status and clears the session cookie