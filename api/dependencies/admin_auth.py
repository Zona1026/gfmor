from typing import Optional

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

from core.config import settings


ROLE_STAFF = "一般"
ROLE_MANAGER = "管理層"
ROLE_SUPER = "最高級"

MANAGER_ROLES = {ROLE_MANAGER, ROLE_SUPER}
SUPER_ADMIN_ROLES = {ROLE_SUPER}


def _empty_context():
    context = {
        "subject": None,
        "user_google_id": None,
        "username": None,
        "role": ROLE_STAFF,
        "is_admin": False,
        "is_manager": False,
        "is_super": False,
    }
    return context


def _decode_bearer_token(authorization: Optional[str], required: bool = False):
    if not authorization or not authorization.lower().startswith("bearer "):
        if required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少授權 token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        if required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="授權 token 無效或已過期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None


def auth_context(authorization: Optional[str] = Header(None)):
    context = _empty_context()
    payload = _decode_bearer_token(authorization)
    if not payload:
        return context

    subject = payload.get("sub")
    context["subject"] = subject

    if payload.get("role") != "admin":
        context["user_google_id"] = subject
        return context

    role = payload.get("admin_role") or ROLE_STAFF
    context["username"] = subject
    context["role"] = role
    context["is_admin"] = bool(subject)
    context["is_manager"] = role in MANAGER_ROLES
    context["is_super"] = role in SUPER_ADMIN_ROLES
    return context


def admin_context(authorization: Optional[str] = Header(None)):
    context = auth_context(authorization)
    context["user_google_id"] = None
    return context


def require_admin(authorization: Optional[str] = Header(None)):
    context = admin_context(authorization)
    if not context["is_admin"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要管理員登入",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return context


def require_manager_admin(authorization: Optional[str] = Header(None)):
    context = require_admin(authorization)
    if not context["is_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="僅管理層以上可操作")
    return context


def require_super_admin(authorization: Optional[str] = Header(None)):
    context = require_admin(authorization)
    if not context["is_super"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="僅最高級管理員可操作")
    return context


def require_self_or_admin(google_id: str, authorization: Optional[str] = Header(None)):
    context = auth_context(authorization)
    if context["is_admin"] or context["user_google_id"] == google_id:
        return context
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="無權存取此會員資料")


def require_self_or_manager(google_id: str, authorization: Optional[str] = Header(None)):
    context = auth_context(authorization)
    if context["is_manager"] or context["user_google_id"] == google_id:
        return context
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="無權修改此會員資料")


def ensure_self_or_admin(google_id: str, context):
    if context["is_admin"] or context["user_google_id"] == google_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="無權存取此會員資料")


def ensure_self_or_manager(google_id: str, context):
    if context["is_manager"] or context["user_google_id"] == google_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="無權修改此會員資料")
