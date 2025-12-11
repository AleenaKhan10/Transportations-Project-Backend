from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session

from models.user import User, UserUpdate
from logic.auth.security import get_current_active_user
from logic.auth.service import AuditService
from db.database import engine

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{user_id}")
async def get_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """Get user details including role and allowed pages"""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Return user details with role and allowed pages
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "address": user.address,
            "avatar": user.avatar,
            "status": user.status,
            "department": user.department,
            "role": user.role or "user",
            "allowed_pages": user.allowed_pages or [],
            "two_factor_enabled": user.two_factor_enabled,
            "email_verified": user.email_verified,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }


@router.put("/{user_id}")
async def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Update user information (name, email, phone, address)"""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Store old values for audit
        old_values = {
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "address": user.address,
        }

        # Update user fields
        update_data = user_data.dict(exclude_unset=True, exclude={"role_id"})
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        session.refresh(user)

        # Log the update
        AuditService.log_business_event(
            user_id=current_user.id,
            action="user_updated",
            resource="users",
            resource_id=str(user_id),
            old_values=old_values,
            new_values=update_data,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success",
        )

        return {
            "success": True,
            "message": "User updated successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "address": user.address,
                "avatar": user.avatar,
                "status": user.status,
                "department": user.department,
                "role": user.role,
                "allowed_pages": user.allowed_pages,
            },
        }


@router.post("/{user_id}/role")
async def update_user_role(
    request: Request,
    user_id: int,
    role_data: dict,  # expects {"role": "admin"} or {"role": "super_admin"} or {"role": "user"}
    current_user: User = Depends(get_current_active_user),
):
    """Update user role (admin, super_admin, user)"""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        role_slug = role_data.get("role")
        if not role_slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Role slug is required"
            )

        # Validate role slug
        valid_roles = ["user", "admin", "super_admin"]
        if role_slug not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
            )

        old_role = user.role
        user.role = role_slug
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()

        # Log the role change
        AuditService.log_business_event(
            user_id=current_user.id,
            action="user_role_changed",
            resource="users",
            resource_id=str(user_id),
            old_values={"role": old_role},
            new_values={"role": role_slug},
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success",
        )

        return {
            "success": True,
            "message": f"User role updated to {role_slug}",
            "role": role_slug,
        }


@router.post("/{user_id}/permissions")
async def update_user_permissions(
    request: Request,
    user_id: int,
    permissions_data: dict,  # expects {"pages": ["dashboard", "drivers", "admin_panel"]}
    current_user: User = Depends(get_current_active_user),
):
    """Update user page permissions"""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        pages = permissions_data.get("pages", [])
        actions = permissions_data.get("actions", [])
        if not isinstance(pages, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Pages must be an array"
            )

        if not isinstance(actions, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Actions must be an array",
            )

        # Store old permissions for audit
        old_pages = user.allowed_pages

        # Update allowed pages
        user.allowed_pages = pages
        user.allowed_actions = actions
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()

        # Log the permission change
        AuditService.log_business_event(
            user_id=current_user.id,
            action="user_permissions_changed",
            resource="users",
            resource_id=str(user_id),
            old_values={"allowed_pages": old_pages},
            new_values={"allowed_pages": pages},
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success",
        )

        return {
            "success": True,
            "message": "User permissions updated successfully",
            "allowed_pages": pages,
            "allowed_actions": actions,
        }


@router.put("/{user_id}/approve")
async def approve_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """Approve a pending user"""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if user.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User is not in pending status (current status: {user.status})",
            )

        old_status = user.status
        user.status = "active"
        user.is_active = True  # Enable login
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()

        # Log the approval
        AuditService.log_business_event(
            user_id=current_user.id,
            action="user_approved",
            resource="users",
            resource_id=str(user_id),
            old_values={"status": old_status},
            new_values={
                "status": "active",
                "approved_by": current_user.username,
                "approval_date": datetime.utcnow().isoformat(),
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success",
        )

        return {
            "success": True,
            "message": "User approved successfully",
            "status": "active",
        }


@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """Delete a user completely"""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Store user info for audit before deletion
        user_info = {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "status": user.status,
        }

        # Delete the user
        session.delete(user)
        session.commit()

        # Log the deletion
        AuditService.log_business_event(
            user_id=current_user.id,
            action="user_deleted",
            resource="users",
            resource_id=str(user_id),
            old_values=user_info,
            new_values={"deleted_by": current_user.username},
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success",
        )

        return {
            "success": True,
            "message": f"User {user_info['username']} deleted successfully",
        }
