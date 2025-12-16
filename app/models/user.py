from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from sqlalchemy import Text
from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    EMAIL_VERIFICATION_PENDING = "email_verification_pending"


class AuditStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


# Base Models
class UserBase(SQLModel):
    username: str = Field(max_length=50, unique=True, index=True)
    email: str = Field(max_length=255, unique=True, index=True)
    full_name: str = Field(max_length=255)
    phone: Optional[str] = Field(max_length=20, default=None)
    avatar: Optional[str] = Field(max_length=500, default=None)
    status: UserStatus = Field(default=UserStatus.PENDING, index=True)
    department: Optional[str] = Field(max_length=100, default=None)
    two_factor_enabled: bool = Field(default=False)
    email_verified: bool = Field(default=False)


class UserCreate(UserBase):
    password: str
    role_id: Optional[int] = None


class UserUpdate(SQLModel):
    email: Optional[str] = Field(max_length=255, default=None)
    full_name: Optional[str] = Field(max_length=255, default=None)
    phone: Optional[str] = Field(max_length=20, default=None)
    avatar: Optional[str] = Field(max_length=500, default=None)
    status: Optional[UserStatus] = None
    department: Optional[str] = Field(max_length=100, default=None)
    address: Optional[str] = Field(max_length=500, default=None)
    role_id: Optional[int] = None


class UserLogin(SQLModel):
    username: str
    password: str
    grant_type: str = "password"


# User model matching exact production database structure
class User(SQLModel, table=True):
    __tablename__ = "user"  # Match production DB table name

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=255, unique=True)
    email: Optional[str] = Field(max_length=255, default=None, unique=True)
    full_name: Optional[str] = Field(max_length=255, default=None)
    phone: Optional[str] = Field(max_length=20, default=None)
    avatar: Optional[str] = Field(max_length=500, default=None)
    status: Optional[str] = Field(
        default="active"
    )  # enum('active','inactive','suspended','pending')
    department: Optional[str] = Field(max_length=100, default=None)
    role: Optional[str] = Field(
        max_length=50, default="user"
    )  # user, admin, super_admin
    allowed_pages: Optional[dict] = Field(
        default=None, sa_column=Column(JSON)
    )  # ["dashboard", "drivers", etc]
    allowed_actions: Optional[dict] = Field(
        default=None, sa_column=Column(JSON)
    )  # ["outbound_calls", etc]
    address: Optional[str] = Field(max_length=500, default=None)
    two_factor_enabled: Optional[bool] = Field(default=False)
    two_factor_secret: Optional[str] = Field(max_length=100, default=None)
    email_verified: Optional[bool] = Field(default=False)
    email_verification_token: Optional[str] = Field(max_length=255, default=None)
    password_reset_token: Optional[str] = Field(max_length=255, default=None)
    password_reset_expires: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = Field(default=None)  # NO foreign key constraint
    deleted_at: Optional[datetime] = None
    password: Optional[str] = Field(max_length=255, default=None)  # Password hash
    is_active: bool = Field(default=True)


class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"

    id: str = Field(primary_key=True, max_length=255)
    user_id: int = Field(index=True)
    ip_address: Optional[str] = Field(max_length=45, default=None)
    user_agent: Optional[str] = None
    last_activity: Optional[datetime] = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    token_status: str = Field(
        default="active", max_length=20, index=True
    )  # 'active', 'revoked', 'expired'
    token_jti: Optional[str] = Field(
        max_length=255, default=None, index=True
    )  # JWT ID for tracking


class PendingEmailVerification(SQLModel, table=True):
    __tablename__ = "pending_email_verifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=255, index=True)
    email: str = Field(max_length=255, index=True)
    password_hash: str = Field(max_length=255)
    full_name: str = Field(max_length=255)
    otp_code: str = Field(max_length=6, index=True)  # 6-digit OTP
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(index=True)  # OTP expires after 10 minutes


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    user_email: Optional[str] = Field(max_length=255, default=None)
    action: str = Field(max_length=100, index=True)
    resource: str = Field(max_length=100, index=True)
    resource_id: Optional[str] = Field(max_length=100, default=None)
    old_values: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    new_values: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    ip_address: Optional[str] = Field(max_length=45, default=None)
    user_agent: Optional[str] = None
    status: Optional[str] = Field(default="success", index=True)
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, index=True)


# Response Models
class RoleResponse(SQLModel):
    id: int
    name: str
    description: Optional[str]
    permissions: List[str] = []


class UserResponse(SQLModel):
    id: int
    username: str
    email: str
    full_name: str
    phone: Optional[str]
    avatar: Optional[str]
    status: UserStatus
    department: Optional[str]
    role: Optional[RoleResponse]
    permissions: List[str] = []
    two_factor_enabled: bool
    email_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: UserResponse


class UserStats(SQLModel):
    total_users: int
    active_users: int
    inactive_users: int
    suspended_users: int
    pending_users: int
    total_roles: int
    active_sessions: int
    recent_logins: int
