from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select

from models.user import User, Role, Permission, RolePermission
from logic.auth.service import RoleService, PermissionService, AuditService
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
    """Get all roles"""
    roles = RoleService.get_all_roles()
    
    role_responses = []
    for role in roles:
        permissions = RoleService.get_role_permissions(role.id)
        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=permissions,
            created_at=role.created_at,
            updated_at=role.updated_at
        ))
    
    return role_responses

@router.get("/roles/{role_id}")
@audit_log("view", "roles")
async def get_role(
    request: Request,
    role_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Get role by ID"""
    role = RoleService.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    permissions = RoleService.get_role_permissions(role.id)
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=permissions,
        created_at=role.created_at,
        updated_at=role.updated_at
    )

@router.post("/roles")
@audit_log("create", "roles")
async def create_role(
    request: Request,
    role_data: dict,
    current_user: User = Depends(require_role_management)
):
    """Create new role"""
    with Session(engine) as session:
        # Check if role name already exists
        existing_role = session.exec(select(Role).where(Role.name == role_data.get('name'))).first()
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name already exists"
            )
        
        # Create role
        role = Role(
            name=role_data.get('name'),
            description=role_data.get('description')
        )
        session.add(role)
        session.commit()
        session.refresh(role)
        
        # Assign permissions if provided
        permissions = role_data.get('permissions', [])
        if permissions:
            all_permissions = PermissionService.get_all_permissions()
            permission_map = {p.name: p.id for p in all_permissions}
            
            for perm_name in permissions:
                if perm_name in permission_map:
                    role_permission = RolePermission(
                        role_id=role.id,
                        permission_id=permission_map[perm_name]
                    )
                    session.add(role_permission)
            
            session.commit()
        
        # Log role creation
        AuditService.log_action(
            user_id=current_user.id,
            action="create",
            resource="roles",
            resource_id=str(role.id),
            new_values={"name": role.name, "permissions": permissions},
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent")
        )
        
        assigned_permissions = RoleService.get_role_permissions(role.id)
        return RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=assigned_permissions,
            created_at=role.created_at,
            updated_at=role.updated_at
        )

@router.put("/roles/{role_id}")
@audit_log("update", "roles")
async def update_role(
    request: Request,
    role_id: int,
    role_data: dict,
    current_user: User = Depends(require_role_management)
):
    """Update role"""
    with Session(engine) as session:
        role = session.get(Role, role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Store old values for audit
        old_permissions = RoleService.get_role_permissions(role.id)
        old_values = {
            "name": role.name,
            "description": role.description,
            "permissions": old_permissions
        }
        
        # Update role fields
        if 'name' in role_data:
            # Check if new name already exists
            existing_role = session.exec(
                select(Role).where(Role.name == role_data['name'], Role.id != role_id)
            ).first()
            if existing_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role name already exists"
                )
            role.name = role_data['name']
        
        if 'description' in role_data:
            role.description = role_data['description']
        
        session.add(role)
        
        # Update permissions if provided
        if 'permissions' in role_data:
            # Remove existing permissions
            existing_role_perms = session.exec(
                select(RolePermission).where(RolePermission.role_id == role_id)
            ).all()
            for rp in existing_role_perms:
                session.delete(rp)
            
            # Add new permissions
            permissions = role_data['permissions']
            all_permissions = PermissionService.get_all_permissions()
            permission_map = {p.name: p.id for p in all_permissions}
            
            for perm_name in permissions:
                if perm_name in permission_map:
                    role_permission = RolePermission(
                        role_id=role.id,
                        permission_id=permission_map[perm_name]
                    )
                    session.add(role_permission)
        
        session.commit()
        session.refresh(role)
        
        # Log role update
        new_permissions = RoleService.get_role_permissions(role.id)
        new_values = {
            "name": role.name,
            "description": role.description,
            "permissions": new_permissions
        }
        
        AuditService.log_action(
            user_id=current_user.id,
            action="update",
            resource="roles",
            resource_id=str(role.id),
            old_values=old_values,
            new_values=new_values,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent")
        )
        
        return RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=new_permissions,
            created_at=role.created_at,
            updated_at=role.updated_at
        )

@router.delete("/roles/{role_id}")
@audit_log("delete", "roles")
async def delete_role(
    request: Request,
    role_id: int,
    current_user: User = Depends(require_role_management)
):
    """Delete role"""
    with Session(engine) as session:
        role = session.get(Role, role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Check if role is in use
        from models.user import UserRole
        users_with_role = session.exec(select(UserRole).where(UserRole.role_id == role_id)).first()
        if users_with_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete role that is assigned to users"
            )
        
        # Store role info for audit
        role_info = {"name": role.name, "description": role.description}
        
        session.delete(role)
        session.commit()
        
        # Log role deletion
        AuditService.log_action(
            user_id=current_user.id,
            action="delete",
            resource="roles",
            resource_id=str(role_id),
            old_values=role_info,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent")
        )
        
        return {"message": "Role deleted successfully"}