## Why

首页目前没有任何访问控制，任何人都可以访问。需要增加密码保护，且密码和 admin 后台的密码分开管理。

## What Changes

1. 前端登录页面独立于 admin 登录
2. 前端登录密码独立配置（通过环境变量 `FRONTEND_PASSWORD`）
3. 前端登录态与 admin 登录态独立存储
4. 未登录用户访问首页时显示登录页

## Capabilities

### New Capabilities
- `frontend-login`: 前端登录功能，独立密码验证

### Modified Capabilities
- `homepage`: 受保护，需要登录才能访问

## Impact

- `frontend/src/App.tsx`: 添加登录态判断和登录页渲染
- `frontend/src/pages/Login.tsx`: 新建前端专用登录页
- `backend/main.py`: 添加前端登录接口
- `backend/routes/auth.py`: 新建 auth 路由模块