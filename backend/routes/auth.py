"""
Auth路由模块

提供前端用户认证功能：
- POST /api/auth/login - 前端用户登录
- POST /api/auth/logout - 前端用户登出
- GET /api/auth/status - 检查登录状态
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/auth", tags=["前端认证"])

FRONTEND_PASSWORD = os.getenv("FRONTEND_PASSWORD", "")
FRONTEND_PASSWORD_HASH = os.getenv("FRONTEND_PASSWORD_HASH", hashlib.sha256(FRONTEND_PASSWORD.encode()).hexdigest() if FRONTEND_PASSWORD else "")

sessions = {}


class LoginRequest(BaseModel):
    password: str


def verify_password(password: str) -> bool:
    if not FRONTEND_PASSWORD:
        return False
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == FRONTEND_PASSWORD_HASH


def create_session():
    session_id = secrets.token_hex(32)
    sessions[session_id] = {
        "created_at": datetime.now(),
        "last_access": datetime.now()
    }
    return session_id


def verify_session(request: Request) -> Optional[str]:
    session_id = request.cookies.get("frontend_session")
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
        key="frontend_session",
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
    response.delete_cookie("frontend_session")
    return {"message": "Logout successful"}


@router.get("/status")
async def get_status(request: Request, session_id: str = Depends(require_auth)):
    return {"authenticated": True}


@router.post("/check")
async def check_auth(request: Request):
    session_id = verify_session(request)
    return {"authenticated": session_id is not None}