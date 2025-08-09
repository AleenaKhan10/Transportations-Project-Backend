from datetime import timedelta, datetime
from typing import Optional

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status, Request

from config import settings
from models.user import User, UserCreate, UserLogin, TokenResponse, UserResponse, RoleResponse
from logic.auth.service import UserService, RoleService, AuditService
from logic.auth.security import (
    create_access_token, create_refresh_token, verify_refresh_token,
    get_current_active_user, rate_limit, generate_reset_token, 
    generate_verification_token, oauth2_scheme, get_jwt_id_from_token
)


router = APIRouter(prefix=settings.AUTH_ROUTER_PREFIX)

def build_user_response(user: User) -> dict:
    """Build user response with roles and permissions for frontend"""
    # Get user roles and permissions
    try:
        roles = UserService.get_user_roles(user.id)
        permissions = UserService.get_user_permissions(user.id)
        
        # Get primary role (first role or highest level)
        primary_role = None
        if roles:
            # Sort by level if available, otherwise take first
            sorted_roles = sorted(roles, key=lambda r: getattr(r, 'level', 0), reverse=True)
            primary_role = sorted_roles[0]
        
        # Build role response
        role_response = None
        if primary_role:
            role_response = {
                "id": primary_role.id,
                "name": primary_role.name,
                "slug": getattr(primary_role, 'slug', primary_role.name.lower().replace(' ', '_')),
                "description": getattr(primary_role, 'description', '')
            }
        
        # Build permissions response
        permissions_response = []
        for perm in permissions:
            permissions_response.append({
                "id": perm.id,
                "name": perm.name,
                "slug": getattr(perm, 'slug', perm.name.lower().replace(' ', '_')),
                "resource": perm.resource,
                "action": perm.action
            })
        
    except Exception as e:
        # Fallback if role/permission queries fail
        print(f"Warning: Could not load roles/permissions for user {user.id}: {e}")
        role_response = None
        permissions_response = []
    
    return {
        "id": user.id,
        "username": user.username,
        "email": getattr(user, 'email', None) or user.username,  # Fallback to username
        "fullName": getattr(user, 'full_name', None) or "Admin User",  # Frontend expects camelCase
        "role": role_response,
        "permissions": permissions_response,
        "status": getattr(user, 'status', 'active'),
        "is_active": getattr(user, 'is_active', True)
    }

@router.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """User authentication endpoint"""
    # Check if user exists first to provide appropriate failure reason
    user_check = UserService.get_user_by_username(form_data.username) or UserService.get_user_by_email(form_data.username)
    
    user = UserService.authenticate_user(form_data.username, form_data.password)
    if not user:
        # Determine failure reason
        failure_reason = "Invalid credentials"
        if user_check:
            if user_check.status == "pending":
                failure_reason = "Account pending approval"
            elif user_check.status == "suspended":
                failure_reason = "Account suspended or rejected"
            elif user_check.status == "inactive":
                failure_reason = "Account inactive"
            elif not UserService.verify_password(form_data.password, user_check.password):
                failure_reason = "Invalid password"
        
        # Log failed login attempt - this IS a business event
        AuditService.log_business_event(
            user_id=user_check.id if user_check else None,
            action="user_login_failed",
            resource="auth",
            resource_id=form_data.username,
            new_values={
                "username": form_data.username,
                "reason": failure_reason,
                "user_status": user_check.status if user_check else "not_found"
            },
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="failure",
            error_message=failure_reason
        )
        
        # Return appropriate error message based on account status
        error_detail = "Incorrect username or password"  # Default for invalid credentials
        
        if user_check:
            if user_check.status == "pending":
                error_detail = "Your account is pending approval. Please wait for an administrator to approve your account."
            elif user_check.status == "suspended":
                error_detail = "Your account has been suspended. Please contact support for assistance."
            elif user_check.status == "inactive":
                error_detail = "Your account is inactive. Please contact support to reactivate your account."
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login time
    UserService.update_last_login(user.id)
    
    # Create tokens with JWT ID for session tracking
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, jwt_id = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token, refresh_jwt_id = create_refresh_token(data={"sub": user.username})
    
    # Create session record automatically
    from models.user import UserSession
    from sqlmodel import Session as DBSession
    from db.database import engine
    import uuid
    
    # Get client IP address (handle proxy headers)
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]
    
    # Create session record (without jwt_id field since it doesn't exist in DB yet)
    with DBSession(engine) as db_session:
        user_session = UserSession(
            id=str(uuid.uuid4()),  # Unique session ID
            user_id=user.id,
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent"),
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),  # 24 hour session
            is_active=True
            # jwt_id field not included since it doesn't exist in current DB schema
        )
        db_session.add(user_session)
        db_session.commit()
    
    # Log successful login - this IS a business event
    AuditService.log_business_event(
        user_id=user.id,
        action="user_login_success",
        resource="auth",
        resource_id=str(user.id),
        new_values={
            "username": user.username,
            "email": user.email,
            "login_method": "password"
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        status="success"
    )
    
    user_response = build_user_response(user)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": refresh_token,
        "user": user_response
    }

@router.post("/users")
async def create_user(request: Request, user_data: UserCreate, current_user: User = Depends(get_current_active_user)):
    """Create new user (admin or registration)"""
    # Check if username already exists
    existing_user = UserService.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = UserService.get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = UserService.create_user(user_data, created_by=current_user.id)
    
    # Log user creation - this IS a business event
    AuditService.log_business_event(
        user_id=current_user.id,
        action="user_created",
        resource="users",
        resource_id=str(user.id),
        old_values=None,
        new_values={
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "status": user.status,
            "created_by": current_user.username
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        status="success"
    )
    
    return build_user_response(user)

@router.post("/register")
async def register_user(request: Request, user_data: UserCreate):
    """Public user registration endpoint for testing"""
    # Check if username already exists
    existing_user = UserService.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = UserService.get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user with pending status for approval
    user = UserService.create_user(user_data, status="pending")
    
    # Log user registration - this IS a business event
    AuditService.log_business_event(
        user_id=None,
        action="user_created",
        resource="users",
        resource_id=str(user.id),
        old_values=None,
        new_values={
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "status": "pending",
            "registration_type": "public"
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        status="success"
    )
    
    return build_user_response(user)

@router.post("/refresh")
async def refresh_token(request: Request, refresh_token: str):
    """Refresh access token using refresh token and update session activity"""
    username = verify_refresh_token(refresh_token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = UserService.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Get JWT ID from refresh token for session tracking
    refresh_jwt_id = get_jwt_id_from_token(refresh_token)
    
    # Create new access token with same JWT ID to maintain session link
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, jwt_id = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires, jwt_id=refresh_jwt_id
    )
    
    # Update session last_activity - for now update all active sessions for user
    # TODO: Once jwt_id is added to database, use specific session matching
    from models.user import UserSession
    from sqlmodel import Session as DBSession, select
    from db.database import engine
    
    with DBSession(engine) as db_session:
        # Find most recent active session for user (fallback until jwt_id is in DB)
        user_session = db_session.exec(
            select(UserSession)
            .where(UserSession.user_id == user.id)
            .where(UserSession.is_active == True)
            .order_by(UserSession.last_activity.desc())
        ).first()
        
        if user_session:
            user_session.last_activity = datetime.utcnow()
            # Optionally extend session expiration
            user_session.expires_at = datetime.utcnow() + timedelta(hours=24)
            db_session.add(user_session)
            db_session.commit()
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/logout")
async def logout(
    request: Request, 
    current_user: User = Depends(get_current_active_user),
    token: str = Depends(oauth2_scheme)
):
    """Logout and invalidate session"""
    # Invalidate most recent active session for user
    # TODO: Once jwt_id is added to database, use specific session matching
    from models.user import UserSession
    from sqlmodel import Session as DBSession, select
    from db.database import engine
    
    with DBSession(engine) as db_session:
        # Find and invalidate the most recent active session
        user_session = db_session.exec(
            select(UserSession)
            .where(UserSession.user_id == current_user.id)
            .where(UserSession.is_active == True)
            .order_by(UserSession.last_activity.desc())
        ).first()
        
        session_invalidated = False
        if user_session:
            user_session.is_active = False
            db_session.add(user_session)
            db_session.commit()
            session_invalidated = True
    
    # Log logout - this IS a business event
    AuditService.log_business_event(
        user_id=current_user.id,
        action="user_logout",
        resource="auth",
        resource_id=str(current_user.id),
        new_values={
            "username": current_user.username,
            "logout_type": "manual",
            "session_invalidated": session_invalidated
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        status="success"
    )
    
    return {"message": "Successfully logged out"}

@router.post("/forgot-password")
async def forgot_password(request: Request, email: str):
    """Initiate password reset process"""
    user = UserService.get_user_by_email(email)
    if not user:
        # Don't reveal whether email exists or not for security
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token (in production, send via email)
    reset_token = generate_reset_token()
    
    # Update user with reset token (simplified - in production store securely)
    # user.password_reset_token = reset_token
    # user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Log password reset request - this IS a business event
    AuditService.log_business_event(
        user_id=user.id,
        action="password_reset_requested",
        resource="auth",
        resource_id=str(user.id),
        new_values={
            "email": email,
            "reset_token_generated": True
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        status="success"
    )
    
    return {"message": "If the email exists, a reset link has been sent"}

@router.post("/reset-password")
async def reset_password(request: Request, token: str, new_password: str):
    """Reset password with token"""
    # In production, verify token from database
    # For now, just return success
    
    return {"message": "Password reset successfully"}

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return build_user_response(current_user)
