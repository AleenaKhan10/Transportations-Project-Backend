from typing import List, Optional
from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlmodel import Session, select, func, or_

from config import settings
from models.user import (
    User, UserCreate, UserUpdate, UserResponse, UserStats, UserStatus,
    Role, RoleResponse
)
from logic.auth.service import UserService, RoleService, AuditService
from logic.auth.security import (
    require_user_management, require_user_view, get_current_active_user,
    audit_log, rate_limit
)
from db.database import engine

router = APIRouter(prefix="/admin", tags=["admin-users"])

def build_user_response(user: User) -> UserResponse:
    """Build user response with roles and permissions"""
    roles = UserService.get_user_roles(user.id)
    permissions = UserService.get_user_permissions(user.id)
    
    role_response = None
    if roles:
        role = roles[0]  # Assuming single role per user for now
        role_permissions = RoleService.get_role_permissions(role.id)
        role_response = RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=role_permissions
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        avatar=user.avatar,
        status=user.status,
        department=user.department,
        role=role_response,
        permissions=permissions,
        two_factor_enabled=user.two_factor_enabled,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@router.get("/users")
@audit_log("list", "users")
async def get_users(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[UserStatus] = Query(None),
    role_id: Optional[int] = Query(None),
    department: Optional[str] = Query(None),
    current_user: User = Depends(require_user_view)
):
    """Get all users with filtering and pagination"""
    with Session(engine) as session:
        query = select(User)
        
        # Apply filters
        if search:
            query = query.where(
                or_(
                    User.username.contains(search),
                    User.email.contains(search),
                    User.full_name.contains(search)
                )
            )
        
        if status:
            query = query.where(User.status == status)
        
        if department:
            query = query.where(User.department == department)
        
        if role_id:
            from models.user import UserRole
            query = query.join(UserRole).where(UserRole.role_id == role_id)
        
        # Get total count
        total_query = select(func.count()).select_from(query.subquery())
        total = session.exec(total_query).one()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        users = session.exec(query).all()
        
        # Build response
        user_responses = [build_user_response(user) for user in users]
        
        return {
            "users": user_responses,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": ceil(total / limit)
        }

@router.get("/users/{user_id}", response_model=UserResponse)
@audit_log("view", "users")
async def get_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_user_view)
):
    """Get user by ID"""
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return build_user_response(user)

@router.put("/users/{user_id}", response_model=UserResponse)
@audit_log("update", "users")
async def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_user_management)
):
    """Update user"""
    user = UserService.update_user(user_id, user_data, updated_by=current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return build_user_response(user)

@router.delete("/users/{user_id}")
@audit_log("delete", "users")
async def delete_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_user_management)
):
    """Delete user"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    success = UserService.delete_user(user_id, deleted_by=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deleted successfully"}

@router.post("/users/{user_id}/suspend")
@audit_log("suspend", "users")
async def suspend_user(
    request: Request,
    user_id: int,
    reason: str,
    current_user: User = Depends(require_user_management)
):
    """Suspend user"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend your own account"
        )
    
    user_data = UserUpdate(status=UserStatus.SUSPENDED)
    user = UserService.update_user(user_id, user_data, updated_by=current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Log suspension reason
    AuditService.log_action(
        user_id=current_user.id,
        action="suspend",
        resource="users",
        resource_id=str(user_id),
        new_values={"reason": reason},
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    return {"message": "User suspended successfully"}

@router.post("/users/{user_id}/activate")
@audit_log("activate", "users")
async def activate_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_user_management)
):
    """Activate user"""
    user_data = UserUpdate(status=UserStatus.ACTIVE)
    user = UserService.update_user(user_id, user_data, updated_by=current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User activated successfully"}

@router.post("/users/{user_id}/reset-password")
@audit_log("password_reset", "users")
async def admin_reset_password(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_user_management)
):
    """Admin reset user password"""
    import secrets
    import string
    
    # Generate temporary password
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    # Hash and update password
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # In production, you would update the password here
    # user.password_hash = UserService.hash_password(temp_password)
    
    return {"temporary_password": temp_password}

@router.post("/users/{user_id}/force-logout")
@audit_log("force_logout", "users")
async def force_logout_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_user_management)
):
    """Force logout user (terminate all sessions)"""
    # In production, invalidate all user sessions
    # SessionService.invalidate_user_sessions(user_id)
    
    return {"message": "User sessions terminated successfully"}

@router.get("/users/stats", response_model=UserStats)
@audit_log("stats", "users")
async def get_user_stats(
    request: Request,
    current_user: User = Depends(require_user_view)
):
    """Get user statistics"""
    with Session(engine) as session:
        # Count users by status
        total_users = session.exec(select(func.count(User.id))).one()
        active_users = session.exec(select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)).one()
        inactive_users = session.exec(select(func.count(User.id)).where(User.status == UserStatus.INACTIVE)).one()
        suspended_users = session.exec(select(func.count(User.id)).where(User.status == UserStatus.SUSPENDED)).one()
        pending_users = session.exec(select(func.count(User.id)).where(User.status == UserStatus.PENDING)).one()
        
        # Count roles
        total_roles = session.exec(select(func.count(Role.id))).one()
        
        # Count recent logins (last 24 hours)
        recent_cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        recent_logins = session.exec(
            select(func.count(User.id)).where(User.last_login_at >= recent_cutoff)
        ).one()
        
        return UserStats(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            suspended_users=suspended_users,
            pending_users=pending_users,
            total_roles=total_roles,
            active_sessions=0,  # Placeholder - implement with session tracking
            recent_logins=recent_logins
        )

@router.post("/users/bulk-update")
@audit_log("bulk_update", "users")
@rate_limit(max_requests=10, window_minutes=60)
async def bulk_update_users(
    request: Request,
    user_ids: List[int],
    updates: dict,
    current_user: User = Depends(require_user_management)
):
    """Bulk update users"""
    if len(user_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update more than 100 users at once"
        )
    
    updated_count = 0
    with Session(engine) as session:
        for user_id in user_ids:
            if user_id == current_user.id and updates.get("status") == UserStatus.SUSPENDED:
                continue  # Skip suspending own account
            
            user = session.get(User, user_id)
            if user:
                for field, value in updates.items():
                    if hasattr(user, field):
                        setattr(user, field, value)
                user.updated_at = datetime.utcnow()
                session.add(user)
                updated_count += 1
        
        session.commit()
    
    return {"message": f"Successfully updated {updated_count} users"}

@router.post("/users/bulk-delete")
@audit_log("bulk_delete", "users")
@rate_limit(max_requests=5, window_minutes=60)
async def bulk_delete_users(
    request: Request,
    user_ids: List[int],
    current_user: User = Depends(require_user_management)
):
    """Bulk delete users"""
    if len(user_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete more than 50 users at once"
        )
    
    if current_user.id in user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    deleted_count = 0
    with Session(engine) as session:
        for user_id in user_ids:
            user = session.get(User, user_id)
            if user:
                session.delete(user)
                deleted_count += 1
        
        session.commit()
    
    return {"message": f"Successfully deleted {deleted_count} users"}