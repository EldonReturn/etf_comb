## Context

首页目前没有任何访问控制。系统已有 admin 后台登录功能（`backend/routes/admin.py`），使用独立的 session 管理。需要新增一套独立的前端登录机制，与 admin 完全分离。

**约束：**
- 前端登录密码通过环境变量 `FRONTEND_PASSWORD` 配置
- 前端 session 使用独立的 cookie `frontend_session`
- 所有 `/api/*` 接口需要验证 `frontend_session`
- 前端主应用在未登录时不发送任何业务 API 请求

## Goals / Non-Goals

**Goals:**
- 前端登录页独立于 admin 登录页
- 密码和 session 与 admin 完全分离
- 未登录用户看到登录页，无法访问任何业务数据
- 登录态持久化（刷新页面保持登录）

**Non-Goals:**
- 不修改 admin 登录逻辑
- 不使用第三方认证（OAuth 等）
- 不实现"记住我"功能（session 有效期 1 小时即可）

## Decisions

### Decision 1: Session Cookie 命名分离

**选择：** 前端 session 使用 `frontend_session` cookie，admin 使用 `admin_session`

**理由：** 避免 cookie 名冲突，前端和 admin 登录态互不影响。用户在 frontend 和 admin 需要分别登录。

### Decision 2: 登录态 localStorage 存储

**选择：** 前端记录登录态时额外存储一个 localStorage 标记 `frontend_logged_in`

**理由：** 仅用 cookie 判断 session 的话，刷新页面时前端会有短暂的白屏/闪烁。localStorage 可以在请求发出去之前就判断是否显示登录页，改善用户体验。

### Decision 3: 后端中间件验证 vs 依赖注入

**选择：** 在 `require_auth` 依赖中使用 cookie 验证

**理由：** FastAPI 的 `Depends` 模式已存在于 admin 路由，复用 `verify_session` 函数模式。业务 API 较少，依赖注入方式简洁；若 API 数量多，再考虑全局中间件。

### Decision 4: 前端登录页 vs Admin 登录页

**选择：** 新建 `frontend/src/pages/Login.tsx`，不复用 `pages/admin/Login.tsx`

**理由：** admin 登录页有"管理后台"标题和样式，不适合作为主应用登录页。两个登录页 UI 不同，分开维护更清晰。

## Risks / Trade-offs

[Risk] 密码明文存储在环境变量 →  Mitigation: 仅用于演示，生产环境应哈希存储

[Risk] 前后端 session 同时过期但时间不同步 →  Mitigation: 后端 session 有效期 1 小时，前端 localStorage 标记不设过期时间（随 cookie 同步失效）

## Migration Plan

1. 部署后端 `backend/routes/auth.py`（新增接口）
2. 部署后端 `main.py`（添加 auth 路由）
3. 部署前端 `Login.tsx`（新文件）
4. 部署前端 `App.tsx`（添加登录判断逻辑）
5. 验证未登录访问 `/api/*` 返回 401
6. 验证登录后正常访问

## Open Questions

- 是否需要为 admin 页面也加上独立的登录验证？（目前 admin 已使用 admin_session）
- FRONTEND_PASSWORD 默认值是什么？（建议设置为空字符串强制要求配置）