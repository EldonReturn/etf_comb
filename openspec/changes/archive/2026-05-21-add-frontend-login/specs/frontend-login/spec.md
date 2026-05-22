## ADDED Requirements

### Requirement: Frontend Login Page

未登录用户访问首页时，应显示登录页面，用户输入正确密码后才能进入首页。

#### Scenario: Unauthenticated user visits homepage

- **WHEN** 用户访问首页且未登录
- **THEN** 显示前端登录页，隐藏主应用内容
- **AND** 不发送任何业务 API 请求（如 `/api/etfs`）

#### Scenario: User submits correct password

- **WHEN** 用户在登录页输入正确密码并提交
- **THEN** 隐藏登录页，显示主应用内容
- **AND** 登录态存储在 localStorage，刷新页面后保持登录

#### Scenario: User submits wrong password

- **WHEN** 用户在登录页输入错误密码并提交
- **THEN** 显示错误提示 "密码错误"
- **AND** 不跳转到首页

#### Scenario: Authenticated user refreshes page

- **WHEN** 已登录用户刷新页面
- **THEN** 页面应保持登录状态，不显示登录页

### Requirement: Frontend Login API

前端登录接口独立于 admin 登录，使用不同的密码和 session。

#### Scenario: Login with correct frontend password

- **WHEN** POST `/api/auth/login` with correct password
- **THEN** 返回 200 和成功消息
- **AND** 设置 `frontend_session` cookie（HttpOnly, 1小时有效）

#### Scenario: Login with wrong password

- **WHEN** POST `/api/auth/login` with wrong password
- **THEN** 返回 401 和错误消息

#### Scenario: Access API without authentication

- **WHEN** 请求 `/api/*` 接口且没有有效的 `frontend_session`
- **THEN** 返回 401 Unauthorized
- **AND** 前端收到 401 后跳转到登录页

### Requirement: Separate Auth State from Admin

前端登录态和 admin 登录态完全独立，互不影响。

#### Scenario: User logged into frontend but not admin

- **WHEN** 用户已登录前端，但访问 `#admin` 页面
- **THEN** 显示 admin 登录页，需要单独登录 admin

#### Scenario: User logged into admin but not frontend

- **WHEN** 用户已登录 admin，但访问首页
- **THEN** 显示前端登录页，需要单独登录前端