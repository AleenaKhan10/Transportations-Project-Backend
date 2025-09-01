from typing import List, Optional
from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlmodel import Session, select, func, or_

from config import settings
from models.user import (
    User, UserCreate, UserUpdate, UserResponse, UserStats, UserStatus
)
from logic.auth.service import UserService, AuditService
from logic.auth.security import (
    require_user_management, require_user_view, get_current_active_user,
    audit_log, rate_limit, oauth2_scheme
)
from db.database import engine

router = APIRouter(prefix="/admin", tags=["admin-users"])

def build_user_response(user: User) -> UserResponse:
    """Build user response with roles and permissions - FAST VERSION"""
    with Session(engine) as session:
        # Simplified version without roles and permissions
        
        role_response = None
        permission_names = []
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email or "",  # Provide default empty string if None
        full_name=user.full_name or user.username,  # Provide default if None
        phone=user.phone,
        avatar=user.avatar,
        status=user.status or "active",  # Provide default status if None
        department=user.department,
        role=role_response,
        permissions=permission_names,
        two_factor_enabled=user.two_factor_enabled or False,  # Provide default if None
        email_verified=user.email_verified or False,  # Provide default if None
        last_login_at=user.last_login_at,
        created_at=user.created_at or datetime.utcnow(),  # Provide default if None
        updated_at=user.updated_at or datetime.utcnow()  # Provide default if None
    )

@router.get("/users")
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
        
        # Skip role filtering since roles are removed
        
        # Get total count
        total_query = select(func.count()).select_from(query.subquery())
        total = session.exec(total_query).one()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        users = session.exec(query).all()
        
        # Build response - batch process for better performance
        user_responses = []
        
        # Batch fetch all user roles and permissions to reduce queries
        user_ids = [user.id for user in users]
        
        # Build simplified responses without roles/permissions
        for user in users:
            user_responses.append(UserResponse(
                id=user.id,
                username=user.username,
                email=user.email or "",
                full_name=user.full_name or user.username,
                phone=user.phone,
                avatar=user.avatar,
                status=user.status or "active",
                department=user.department,
                role=None,
                permissions=[],
                two_factor_enabled=user.two_factor_enabled or False,
                email_verified=user.email_verified or False,
                last_login_at=user.last_login_at,
                created_at=user.created_at or datetime.utcnow(),
                updated_at=user.updated_at or datetime.utcnow()
            ))
        
        return {
            "users": user_responses,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": ceil(total / limit)
        }

@router.get("/users/stats", response_model=UserStats)
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
        
        # Count roles (set to 0 since roles are removed)
        total_roles = 0
        
        # Count recent logins (last 24 hours)
        recent_cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        recent_logins = session.exec(
            select(func.count(User.id)).where(User.last_login_at >= recent_cutoff)
        ).one()
        
        # Count active sessions
        from models.user import UserSession
        active_sessions = session.exec(
            select(func.count(UserSession.id))
            .where(UserSession.is_active == True)
            .where(UserSession.expires_at > datetime.utcnow())
        ).one()
        
        return UserStats(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            suspended_users=suspended_users,
            pending_users=pending_users,
            total_roles=total_roles,
            active_sessions=active_sessions,  # Now shows actual active sessions
            recent_logins=recent_logins
        )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_user_view)
):
    """Get user by ID - FAST VERSION"""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return build_user_response(user)

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: int,
    user_data: dict,  # Accept dict instead of UserUpdate to handle camelCase
    current_user: User = Depends(require_user_management)
):
    """Update user - FAST VERSION"""
    with Session(engine) as session:
        # Single query to get user
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Store old values for audit
        old_values = {
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "status": user.status,
            "department": user.department
        }
        
        # Map camelCase to snake_case
        field_mapping = {
            "fullName": "full_name",
            "roleId": "role_id"
        }
        
        # Convert camelCase keys to snake_case
        update_data = {}
        for key, value in user_data.items():
            # Map camelCase to snake_case if needed
            mapped_key = field_mapping.get(key, key)
            if mapped_key != "role_id" and hasattr(user, mapped_key):
                update_data[mapped_key] = value
        
        # Update user fields directly
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        session.add(user)
        
        # Skip role assignment since roles are removed
        
        session.commit()
        session.refresh(user)
        
        # Build new values for audit
        new_values = update_data.copy()
        if user_data.get("roleId") or user_data.get("role_id"):
            new_values["role_id"] = user_data.get("roleId") or user_data.get("role_id")
        
        # Fast audit log without extra queries
        from logic.auth.service import AuditService
        AuditService.log_business_event(
            user_id=current_user.id,
            action="user_updated",
            resource="users",
            resource_id=str(user_id),
            old_values=old_values,
            new_values=new_values,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success"
        )
        
        return build_user_response(user)

@router.delete("/users/{user_id}")
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
    
    # Get user data before deletion for audit
    user_to_delete = UserService.get_user_by_id(user_id)
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_values = {
        "username": user_to_delete.username,
        "email": user_to_delete.email,
        "full_name": user_to_delete.full_name,
        "status": user_to_delete.status
    }
    
    success = UserService.delete_user(user_id, deleted_by=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Log user deletion - this IS a business event
    from logic.auth.service import AuditService
    AuditService.log_business_event(
        user_id=current_user.id,
        action="user_deleted",
        resource="users",
        resource_id=str(user_id),
        old_values=old_values,
        new_values=None,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        status="success"
    )
    
    return {"message": "User deleted successfully"}

@router.post("/users/{user_id}/suspend")
async def suspend_user(
    request: Request,
    user_id: int,
    reason: str = Query(..., description="Reason for suspension"),
    current_user: User = Depends(require_user_management)
):
    """Suspend user - FAST VERSION"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend your own account"
        )
    
    with Session(engine) as session:
        # Single query to get and update user
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        old_status = user.status
        old_username = user.username
        
        # Direct update - no separate service call
        user.status = "suspended"
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        
        # Fast audit log without extra queries
        from logic.auth.service import AuditService
        AuditService.log_business_event(
            user_id=current_user.id,
            action="user_suspended",
            resource="users",
            resource_id=str(user_id),
            old_values={"status": old_status, "username": old_username},
            new_values={
                "status": "suspended",
                "reason": reason,
                "suspended_by": current_user.username
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success"
        )
    
    return {"message": "User suspended successfully"}

@router.post("/users/{user_id}/activate")
async def activate_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_user_management)
):
    """Activate user - FAST VERSION"""
    with Session(engine) as session:
        # Single query to get and update user
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        old_status = user.status
        
        # Direct update - no separate service call
        user.status = "active"
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        
        # Fast audit log without extra queries
        from logic.auth.service import AuditService
        AuditService.log_business_event(
            user_id=current_user.id,
            action="user_activated",
            resource="users",
            resource_id=str(user_id),
            old_values={"status": old_status},
            new_values={"status": "active", "activated_by": current_user.username},
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success"
        )
    
    return {"message": "User activated successfully"}

@router.post("/users/{user_id}/approve")
async def approve_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_user_management)
):
    """Approve pending user - FAST VERSION"""
    with Session(engine) as session:
        # Single query to get and update user
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not in pending status"
            )
        
        old_status = user.status
        old_username = user.username
        
        # Direct update - no separate service call
        user.status = "active"
        user.is_active = True  # Enable login
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        
        # Fast audit log without extra queries
        from logic.auth.service import AuditService
        AuditService.log_business_event(
            user_id=current_user.id,
            action="user_approved",
            resource="users",
            resource_id=str(user_id),
            old_values={"status": old_status, "username": old_username},
            new_values={
                "status": "active",
                "approved_by": current_user.username,
                "approval_date": datetime.utcnow().isoformat()
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success"
        )
    
    return {"message": "User approved successfully"}

@router.post("/users/{user_id}/reject")
async def reject_user(
    request: Request,
    user_id: int,
    reason: str = Query(None, description="Reason for rejection"),
    current_user: User = Depends(require_user_management)
):
    """Reject pending user (sets status to suspended) - FAST VERSION"""
    with Session(engine) as session:
        # Single query to get and update user
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not in pending status"
            )
        
        old_status = user.status
        old_username = user.username
        
        # Direct update - no separate service call
        user.status = "suspended"  # We use suspended for rejected users
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        
        # Fast audit log without extra queries
        from logic.auth.service import AuditService
        AuditService.log_business_event(
            user_id=current_user.id,
            action="user_rejected",
            resource="users",
            resource_id=str(user_id),
            old_values={"status": old_status, "username": old_username},
            new_values={
                "status": "suspended",  # We use suspended for rejected users
                "rejected_by": current_user.username,
                "rejection_reason": reason or "No reason provided",
                "rejection_date": datetime.utcnow().isoformat()
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success"
        )
    
    return {"message": "User rejected successfully"}

@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_user_management)
):
    """Admin reset user password - WORKING VERSION"""
    import secrets
    import string
    
    # Generate temporary password
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    with Session(engine) as session:
        # Get user
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Hash and update password in database
        from logic.auth.service import UserService
        hashed_password = UserService.hash_password(temp_password)
        user.password = hashed_password
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        
        # Log password reset - this IS a business event
        from logic.auth.service import AuditService
        AuditService.log_business_event(
            user_id=current_user.id,
            action="password_reset_by_admin",
            resource="users",
            resource_id=str(user_id),
            old_values={"username": user.username},
            new_values={
                "password_reset_by": current_user.username,
                "reset_date": datetime.utcnow().isoformat()
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success"
        )
    
    return {
        "message": "Password reset successfully",
        "temporary_password": temp_password,
        "note": "User can login with this temporary password and should change it immediately"
    }

@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    request: Request,
    user_id: int,
    include_inactive: bool = Query(False, description="Include terminated sessions for history"),
    current_user: User = Depends(require_user_view)
):
    """Get sessions for a specific user (active by default, or all if include_inactive=true)"""
    with Session(engine) as session:
        from models.user import UserSession
        
        # Build query for user sessions
        query = (
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.last_activity.desc())
        )
        
        # Apply filters based on include_inactive parameter
        if not include_inactive:
            # Default: only active and non-expired sessions
            query = query.where(UserSession.is_active == True).where(UserSession.expires_at > datetime.utcnow())
        # If include_inactive=true, show all sessions (active and terminated)
        
        user_sessions = session.exec(query).all()
        
        sessions = []
        for sess in user_sessions:
            sessions.append({
                "session_id": sess.id,
                "ip_address": sess.ip_address,
                "user_agent": sess.user_agent,
                "created_at": sess.created_at,
                "last_activity": sess.last_activity,
                "expires_at": sess.expires_at,
                "is_active": sess.is_active,  # Include is_active field
                "is_current": False  # We don't track current session in this simple implementation
            })
        
        return {
            "user_id": user_id,
            "sessions": sessions,
            "total_sessions": len(sessions),
            "include_inactive": include_inactive
        }

@router.get("/sessions/all")
async def get_all_active_sessions(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    include_inactive: bool = Query(False, description="Include terminated sessions for history"),
    current_user: User = Depends(require_user_view)
):
    """Get all sessions across all users (active by default, or all if include_inactive=true)"""
    with Session(engine) as session:
        from models.user import UserSession
        
        # Query for sessions with user info
        query = (
            select(UserSession, User)
            .join(User, UserSession.user_id == User.id)
            .order_by(UserSession.last_activity.desc())
        )
        
        # Apply filters based on include_inactive parameter
        if not include_inactive:
            # Default: only active and non-expired sessions
            query = query.where(UserSession.is_active == True).where(UserSession.expires_at > datetime.utcnow())
        # If include_inactive=true, show all sessions (active and terminated)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = session.exec(count_query).one()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        results = session.exec(query).all()
        
        sessions = []
        for user_session, user in results:
            sessions.append({
                "session_id": user_session.id,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "ip_address": user_session.ip_address,
                "user_agent": user_session.user_agent,
                "created_at": user_session.created_at,
                "last_activity": user_session.last_activity,
                "expires_at": user_session.expires_at,
                "is_active": user_session.is_active  # Include is_active field
            })
        
        return {
            "sessions": sessions,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": ceil(total / limit)
        }

@router.post("/users/{user_id}/force-logout")
async def force_logout_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_user_management)
):
    """Force logout user (terminate all sessions) with token revocation"""
    with Session(engine) as session:
        from models.user import UserSession
        from logic.auth.service import AuditService, TokenStatusService
        
        # Get user info for logging
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Use TokenStatusService to revoke all user tokens
        sessions_terminated = TokenStatusService.revoke_all_user_tokens(
            user_id=user_id,
            reason="admin_force_logout"
        )
        
        # Log session termination - this IS a business event
        AuditService.log_business_event(
            user_id=current_user.id,
            action="session_terminated",
            resource="users",
            resource_id=str(user_id),
            old_values={"username": user.username},
            new_values={
                "terminated_by": current_user.username,
                "sessions_terminated": sessions_terminated,
                "termination_date": datetime.utcnow().isoformat(),
                "method": "token_blacklisting"
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success"
        )
    
    return {
        "message": "User sessions terminated successfully",
        "sessions_terminated": sessions_terminated
    }

@router.post("/sessions/{session_id}/terminate")
async def terminate_single_session(
    request: Request,
    session_id: str,
    current_user: User = Depends(require_user_management)
):
    """Terminate a single session by session ID with token revocation"""
    with Session(engine) as session:
        from models.user import UserSession
        from logic.auth.service import AuditService, TokenStatusService
        
        # Find the session
        user_session = session.get(UserSession, session_id)
        if not user_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Get user info for logging
        user = session.get(User, user_session.user_id)
        
        # Store session info for return message
        has_token_jti = bool(user_session.token_jti)
        
        # Revoke only the specific session token
        if user_session.token_jti:
            success = TokenStatusService.revoke_token(
                jti=user_session.token_jti,
                reason="admin_session_termination"
            )
            sessions_terminated = 1 if success else 0
        else:
            # If no token_jti, mark the session as inactive directly
            user_session.is_active = False
            user_session.token_status = "revoked"
            session.add(user_session)
            session.commit()
            sessions_terminated = 1
        
        # Log session termination
        AuditService.log_business_event(
            user_id=current_user.id,
            action="session_terminated",
            resource="sessions",
            resource_id=session_id,
            old_values={
                "session_id": session_id,
                "target_user": user.username if user else "unknown"
            },
            new_values={
                "terminated_by": current_user.username,
                "termination_date": datetime.utcnow().isoformat(),
                "sessions_affected": sessions_terminated,
                "method": "token_blacklisting"
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success"
        )
    
    return {
        "message": "Session terminated successfully", 
        "sessions_affected": sessions_terminated,
        "note": "Single session token revoked" if has_token_jti else "Session marked inactive"
    }

@router.post("/sessions/revoke-current-token") 
async def revoke_current_token(
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(require_user_management)
):
    """Revoke the current token being used (for testing)"""
    from logic.auth.security import get_jwt_id_from_token
    from logic.auth.service import TokenStatusService, AuditService
    
    jti = get_jwt_id_from_token(token)
    
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token does not have JWT ID"
        )
    
    # Revoke the token
    success = TokenStatusService.revoke_token(jti, reason="admin_test")
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token session not found"
        )
    
    # Log the revocation
    AuditService.log_business_event(
        user_id=current_user.id,
        action="token_revoked",
        resource="tokens",
        resource_id=jti,
        new_values={
            "revoked_by": current_user.username,
            "reason": "admin_test"
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        status="success"
    )
    
    return {
        "message": "Token revoked successfully",
        "jti": jti,
        "note": "This token should no longer work for authentication"
    }




@router.post("/sessions/cleanup-expired")
async def cleanup_expired_sessions(
    request: Request,
    current_user: User = Depends(require_user_management)
):
    """Cleanup expired sessions (admin endpoint)"""
    from logic.auth.service import TokenStatusService, AuditService
    
    cleanup_count = TokenStatusService.cleanup_expired_sessions()
    
    # Log session cleanup - this IS a business event
    AuditService.log_business_event(
        user_id=current_user.id,
        action="sessions_cleanup",
        resource="sessions",
        resource_id="expired",
        new_values={
            "cleanup_by": current_user.username,
            "sessions_cleaned": cleanup_count,
            "cleanup_date": datetime.utcnow().isoformat()
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        status="success"
    )
    
    return {
        "message": "Expired sessions cleanup completed",
        "sessions_cleaned": cleanup_count
    }

@router.post("/users/change-password")
async def change_password(
    request: Request,
    current_password: str = Query(..., description="Current password"),
    new_password: str = Query(..., description="New password"),
    current_user: User = Depends(get_current_active_user)
):
    """User change their own password"""
    from logic.auth.service import UserService
    
    # Verify current password
    if not UserService.verify_password(current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password (basic validation)
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long"
        )
    
    with Session(engine) as session:
        # Get user and update password
        user = session.get(User, current_user.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Hash and update password
        hashed_password = UserService.hash_password(new_password)
        user.password = hashed_password
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        
        # Log password change - this IS a business event
        from logic.auth.service import AuditService
        AuditService.log_business_event(
            user_id=current_user.id,
            action="password_changed",
            resource="auth",
            resource_id=str(current_user.id),
            old_values={"username": current_user.username},
            new_values={
                "password_changed_by": "self",
                "change_date": datetime.utcnow().isoformat()
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="success"
        )
    
    return {"message": "Password changed successfully"}

@router.post("/users/bulk-update")
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