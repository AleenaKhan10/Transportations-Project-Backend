from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select

from models.user import User
from logic.auth.service import AuditService
from logic.auth.security import (
    require_role_management, get_current_active_user, audit_log
)
from db.database import engine

router = APIRouter(prefix="/admin", tags=["admin-roles"])

class RoleCreate(dict):
    def __init__(self, name: str, description: str = None, permissions: List[str] = None):
        super().__init__()
        self['name'] = name
        self['description'] = description
        self['permissions'] = permissions or []

class RoleUpdate(dict):
    def __init__(self, name: str = None, description: str = None, permissions: List[str] = None):
        super().__init__()
        if name is not None:
            self['name'] = name
        if description is not None:
            self['description'] = description
        if permissions is not None:
            self['permissions'] = permissions

class RoleResponse(dict):
    def __init__(self, id: int, name: str, description: str = None, permissions: List[str] = None, created_at=None, updated_at=None):
        super().__init__()
        self['id'] = id
        self['name'] = name
        self['description'] = description
        self['permissions'] = permissions or []
        self['created_at'] = created_at
        self['updated_at'] = updated_at

@router.get("/roles")
@audit_log("list", "roles")
async def get_roles(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Get all roles - returns empty since roles removed"""
    return []

@router.get("/roles/{role_id}")
@audit_log("view", "roles")
async def get_role(
    request: Request,
    role_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Get role by ID - always returns not found since roles removed"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Role not found"
    )

@router.post("/roles")
@audit_log("create", "roles")
async def create_role(
    request: Request,
    role_data: dict,
    current_user: User = Depends(require_role_management)
):
    """Create new role - disabled since roles removed"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Role creation disabled"
    )

@router.put("/roles/{role_id}")
@audit_log("update", "roles")
async def update_role(
    request: Request,
    role_id: int,
    role_data: dict,
    current_user: User = Depends(require_role_management)
):
    """Update role - always returns not found since roles removed"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Role not found"
    )

@router.delete("/roles/{role_id}")
@audit_log("delete", "roles")
async def delete_role(
    request: Request,
    role_id: int,
    current_user: User = Depends(require_role_management)
):
    """Delete role - always returns not found since roles removed"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Role not found"
    )