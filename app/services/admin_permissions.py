from typing import List

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from models.user import User
from logic.auth.security import get_current_active_user, audit_log
from db.database import engine

router = APIRouter(prefix="/admin", tags=["admin-permissions"])

class PermissionResponse(dict):
    def __init__(self, id: int, name: str, resource: str, action: str, description: str = None):
        super().__init__()
        self['id'] = id
        self['name'] = name
        self['resource'] = resource
        self['action'] = action
        self['description'] = description

@router.get("/permissions")
@audit_log("list", "permissions")
async def get_permissions(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Get all permissions - returns empty since permissions removed"""
    return []

@router.get("/permissions/resource/{resource}")
@audit_log("list_by_resource", "permissions")
async def get_permissions_by_resource(
    request: Request,
    resource: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get permissions by resource - returns empty since permissions removed"""
    return []

@router.get("/permissions/resources")
@audit_log("list_resources", "permissions")
async def get_permission_resources(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Get all unique permission resources - returns empty since permissions removed"""
    return []