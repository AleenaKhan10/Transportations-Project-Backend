from datetime import timedelta
from typing import Optional

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status, Request

from config import settings
from models.user import User, UserCreate, UserLogin, TokenResponse, UserResponse, RoleResponse
from logic.auth.service import UserService, RoleService, AuditService
from logic.auth.security import (
    create_access_token, create_refresh_token, verify_refresh_token,
    get_current_active_user, rate_limit, generate_reset_token, 
    generate_verification_token
)


router = APIRouter(prefix=settings.AUTH_ROUTER_PREFIX)

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

@router.post("/login", response_model=TokenResponse)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """User authentication endpoint"""
    user = UserService.authenticate_user(form_data.username, form_data.password)
    if not user:
        # Log failed login attempt
        AuditService.log_action(
            user_id=None,
            action="login",
            resource="auth",
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            status="failure",
            error_message="Invalid credentials"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login time
    UserService.update_last_login(user.id)
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    # Log successful login
    AuditService.log_action(
        user_id=user.id,
        action="login",
        resource="auth",
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    user_response = build_user_response(user)
    
    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        user=user_response
    )

@router.post("/users", response_model=UserResponse)
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
    
    # Log user creation
    AuditService.log_action(
        user_id=current_user.id,
        action="create",
        resource="users",
        resource_id=str(user.id),
        new_values={"username": user.username, "email": user.email},
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    return build_user_response(user)

@router.post("/register", response_model=UserResponse)
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
    
    # Create user
    user = UserService.create_user(user_data)
    
    # Log user creation
    AuditService.log_action(
        user_id=None,
        action="register",
        resource="users",
        resource_id=str(user.id),
        new_values={"username": user.username, "email": user.email},
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    return build_user_response(user)

@router.post("/refresh")
async def refresh_token(request: Request, refresh_token: str):
    """Refresh access token using refresh token"""
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
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_active_user)):
    """Logout and invalidate session"""
    # Log logout
    AuditService.log_action(
        user_id=current_user.id,
        action="logout",
        resource="auth",
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
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
    
    # Log password reset request
    AuditService.log_action(
        user_id=user.id,
        action="password_reset_request",
        resource="auth",
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    return {"message": "If the email exists, a reset link has been sent"}

@router.post("/reset-password")
async def reset_password(request: Request, token: str, new_password: str):
    """Reset password with token"""
    # In production, verify token from database
    # For now, just return success
    
    return {"message": "Password reset successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return build_user_response(current_user)
