"""
Admin路由模块

提供管理员认证和ETF同步管理功能：
- POST /admin/login - 管理员登录
- POST /admin/logout - 管理员登出
- GET /admin/sync/status - 获取同步状态
- POST /admin/sync - 触发同步
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/admin", tags=["管理员"])

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest())
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))

sessions = {}

SyncState = {
    "status": "idle",
    "last_sync": None,
    "last_result": None,
    "is_running": False,
}


class LoginRequest(BaseModel):
    password: str


class SyncStatusResponse(BaseModel):
    status: str
    last_sync: Optional[str]
    last_result: Optional[str]


class SyncStartedResponse(BaseModel):
    status: str
    message: str


def verify_password(password: str) -> bool:
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == ADMIN_PASSWORD_HASH


def create_session():
    session_id = secrets.token_hex(32)
    sessions[session_id] = {
        "created_at": datetime.now(),
        "last_access": datetime.now()
    }
    return session_id


def verify_session(request: Request) -> Optional[str]:
    session_id = request.cookies.get("admin_session")
    if not session_id or session_id not in sessions:
        return None

    session = sessions[session_id]
    if datetime.now() - session["last_access"] > timedelta(hours=1):
        del sessions[session_id]
        return None

    session["last_access"] = datetime.now()
    return session_id


def require_auth(request: Request):
    session_id = verify_session(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return session_id


@router.post("/login")
async def login(request: LoginRequest, response: Response):
    if not verify_password(request.password):
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid credentials"}
        )

    session_id = create_session()
    response.set_cookie(
        key="admin_session",
        value=session_id,
        httponly=True,
        max_age=3600,
        samesite="lax"
    )
    return {"message": "Login successful"}


@router.post("/logout")
async def logout(request: Request, response: Response, session_id: str = Depends(require_auth)):
    if session_id in sessions:
        del sessions[session_id]
    response.delete_cookie("admin_session")
    return {"message": "Logout successful"}


@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(request: Request, session_id: str = Depends(require_auth)):
    return SyncStatusResponse(
        status=SyncState["status"],
        last_sync=SyncState["last_sync"],
        last_result=SyncState["last_result"]
    )


@router.post("/sync", response_model=SyncStartedResponse)
async def trigger_sync(request: Request, session_id: str = Depends(require_auth)):
    if SyncState["is_running"]:
        return JSONResponse(
            status_code=409,
            content={"error": "Sync already in progress"}
        )

    from backend.services import sync_all_etf_data

    SyncState["is_running"] = True
    SyncState["status"] = "running"
    SyncState["last_sync"] = datetime.now().isoformat()

    try:
        stats = sync_all_etf_data()
        SyncState["status"] = "idle"
        SyncState["last_result"] = "success"
        return SyncStartedResponse(
            status="started",
            message=f"Sync initiated: {stats['etf_count']} ETFs, {stats['nav_count']} NAV records"
        )
    except Exception as e:
        SyncState["status"] = "idle"
        SyncState["last_result"] = "failed"
        return JSONResponse(
            status_code=500,
            content={"error": f"Sync failed: {str(e)}"}
        )
    finally:
        SyncState["is_running"] = False