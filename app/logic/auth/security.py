from typing import Optional, List
from datetime import datetime, timedelta
from functools import wraps
import secrets

from jose import JWTError, jwt
from sqlmodel import Session, select
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, Query, status, Header, Request

from config import settings
from models.user import User, UserStatus
from logic.auth.service import UserService, SessionService, AuditService
from db.database import engine


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.TOKEN_ENDPOINT_PATH)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, jwt_id: Optional[str] = None):
    import uuid
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add JWT ID for session tracking
    jti = jwt_id or str(uuid.uuid4())
    to_encode.update({"exp": expire, "jti": jti})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, jti

def create_refresh_token(data: dict, jwt_id: Optional[str] = None):
    import uuid
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # Refresh token expires in 7 days
    
    # Add JWT ID for session tracking
    jti = jwt_id or str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, jti

def verify_refresh_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if username is None or token_type != "refresh":
            return None
        return username
    except JWTError:
        return None

def get_jwt_id_from_token(token: str) -> Optional[str]:
    """Extract JWT ID from token for session tracking"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("jti")
    except JWTError:
        return None

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        jti: str = payload.get("jti")  # JWT ID
        
        if username is None:
            raise credentials_exception
        
        # Check token status (SIMPLE and RELIABLE)
        if jti:
            from logic.auth.service import TokenStatusService
            token_status = TokenStatusService.get_token_status(jti)
            
            if token_status == "revoked":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            elif token_status == "expired":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            elif token_status == "not_found":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
    except JWTError:
        raise credentials_exception
    
    user = UserService.get_user_by_username(username)
    if user is None or user.status != UserStatus.ACTIVE:
        raise credentials_exception
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

class PermissionChecker:
    def __init__(self, required_permission: str = None, required_resource: str = None, required_action: str = None):
        self.required_permission = required_permission
        self.required_resource = required_resource
        self.required_action = required_action
    
    def __call__(self, current_user: User = Depends(get_current_active_user)):
        user_permissions = UserService.get_user_permissions(current_user.id)
        user_permission_names = [perm.name for perm in user_permissions]
        
        # Check specific permission name
        if self.required_permission and self.required_permission not in user_permission_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{self.required_permission}' required"
            )
        
        # Check resource and action combination
        if self.required_resource and self.required_action:
            # Get all permissions for the resource
            from logic.auth.service import PermissionService
            resource_permissions = PermissionService.get_permissions_by_resource(self.required_resource)
            required_perm = next(
                (p.name for p in resource_permissions if p.action == self.required_action), 
                None
            )
            if required_perm and required_perm not in user_permission_names:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission for '{self.required_action}' on '{self.required_resource}' required"
                )
        
        return current_user

# Permission dependencies
require_user_management = PermissionChecker(required_permission="Manage Users")
require_user_view = PermissionChecker(required_permission="View Users")
require_role_management = PermissionChecker(required_permission="Manage Roles")
require_audit_view = PermissionChecker(required_permission="View Audit Logs")
require_system_settings = PermissionChecker(required_permission="System Settings")

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This is handled by the PermissionChecker dependency
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Rate limiting storage (in production, use Redis)
rate_limit_storage = {}

def rate_limit(max_requests: int, window_minutes: int):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host
            current_time = datetime.utcnow()
            
            # Clean old entries
            cutoff_time = current_time - timedelta(minutes=window_minutes)
            if client_ip in rate_limit_storage:
                rate_limit_storage[client_ip] = [
                    timestamp for timestamp in rate_limit_storage[client_ip] 
                    if timestamp > cutoff_time
                ]
            else:
                rate_limit_storage[client_ip] = []
            
            # Check rate limit
            if len(rate_limit_storage[client_ip]) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            
            # Add current request
            rate_limit_storage[client_ip].append(current_time)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Audit logging decorator
def audit_log(action: str, resource: str):
    """Decorator to automatically log actions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = None
            try:
                # Try to get current user from request
                token = request.headers.get("Authorization", "").replace("Bearer ", "")
                if token:
                    try:
                        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                        username = payload.get("sub")
                        if username:
                            user = UserService.get_user_by_username(username)
                    except JWTError:
                        pass
                
                # Execute the function
                result = await func(request, *args, **kwargs)
                
                # Log successful action
                AuditService.log_action(
                    user_id=user.id if user else None,
                    action=action,
                    resource=resource,
                    ip_address=request.client.host,
                    user_agent=request.headers.get("User-Agent")
                )
                
                return result
                
            except Exception as e:
                # Log failed action
                AuditService.log_action(
                    user_id=user.id if user else None,
                    action=action,
                    resource=resource,
                    ip_address=request.client.host,
                    user_agent=request.headers.get("User-Agent"),
                    status="failure",
                    error_message=str(e)
                )
                raise
        
        return wrapper
    return decorator

def generate_reset_token() -> str:
    """Generate a secure password reset token"""
    return secrets.token_urlsafe(32)

def generate_verification_token() -> str:
    """Generate a secure email verification token"""
    return secrets.token_urlsafe(32)

def verify_static_token(x_api_key: str = Header(..., description="Your secret API token.")):
    """
    Dependency to verify the secret token in the X-Auth-Token header for ingestion services.
    """
    if x_api_key != settings.DUMMY_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing API token")

def verify_webhook_token(token: str = Query(..., description="Secret API token.")):
    """
    Dependency to verify the secret token in query parameter for webhook services.
    """
    if token != settings.WEBHOOK_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing API token")
