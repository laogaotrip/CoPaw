# -*- coding: utf-8 -*-
"""Authentication API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..auth import (
    authenticate,
    get_registered_username,
    has_registered_users,
    is_auth_enabled,
    register_user,
    set_auth_enabled,
    set_user_password,
    verify_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class AuthStatusResponse(BaseModel):
    enabled: bool
    has_users: bool


class AuthSettingsResponse(BaseModel):
    enabled: bool
    has_users: bool
    username: str


class UpdateAuthSettingsRequest(BaseModel):
    enabled: bool | None = None
    password: str | None = None


@router.post("/login")
async def login(req: LoginRequest):
    """Authenticate with username and password."""
    if not is_auth_enabled():
        return LoginResponse(token="", username="")

    token = authenticate(req.username, req.password)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return LoginResponse(token=token, username=req.username)


@router.post("/register")
async def register(req: RegisterRequest):
    """Register the single user account (only allowed once)."""
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    if has_registered_users():
        raise HTTPException(
            status_code=403,
            detail="User already registered",
        )

    if not req.username.strip() or not req.password.strip():
        raise HTTPException(
            status_code=400,
            detail="Username and password are required",
        )

    token = register_user(req.username.strip(), req.password)
    if token is None:
        raise HTTPException(
            status_code=409,
            detail="Registration failed",
        )

    return LoginResponse(token=token, username=req.username.strip())


@router.get("/status")
async def auth_status():
    """Check if authentication is enabled and whether a user exists."""
    return AuthStatusResponse(
        enabled=is_auth_enabled(),
        has_users=has_registered_users(),
    )


@router.get("/settings", response_model=AuthSettingsResponse)
async def get_auth_settings():
    """Get current auth switch and account status."""
    return AuthSettingsResponse(
        enabled=is_auth_enabled(),
        has_users=has_registered_users(),
        username=get_registered_username(),
    )


@router.put("/settings", response_model=AuthSettingsResponse)
async def update_auth_settings(req: UpdateAuthSettingsRequest):
    """Update auth switch and/or admin password."""
    if req.enabled is None and req.password is None:
        raise HTTPException(
            status_code=400,
            detail="At least one of enabled/password is required",
        )

    if req.enabled is not None:
        set_auth_enabled(req.enabled)

    if req.password is not None:
        password = req.password.strip()
        if not password:
            raise HTTPException(
                status_code=400,
                detail="Password cannot be empty",
            )
        set_user_password(password)

    return AuthSettingsResponse(
        enabled=is_auth_enabled(),
        has_users=has_registered_users(),
        username=get_registered_username(),
    )


@router.get("/verify")
async def verify(request: Request):
    """Verify that the caller's Bearer token is still valid."""
    if not is_auth_enabled():
        return {"valid": True, "username": ""}

    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return {"valid": True, "username": username}
