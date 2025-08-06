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
    role_id: Optional[int] = None

class UserLogin(SQLModel):
    username: str
    password: str
    grant_type: str = "password"

# Database Models
class User(UserBase, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str = Field(max_length=255)
    two_factor_secret: Optional[str] = Field(max_length=100, default=None)
    email_verification_token: Optional[str] = Field(max_length=255, default=None)
    password_reset_token: Optional[str] = Field(max_length=255, default=None)
    password_reset_expires: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = Field(foreign_key="users.id", default=None)
    
    # Relationships
    roles: List["UserRole"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[UserRole.user_id]"}
    )
    sessions: List["UserSession"] = Relationship(back_populates="user")
    audit_logs: List["AuditLog"] = Relationship(back_populates="user")

class Role(SQLModel, table=True):
    __tablename__ = "roles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    users: List["UserRole"] = Relationship(back_populates="role")
    permissions: List["RolePermission"] = Relationship(back_populates="role")

class Permission(SQLModel, table=True):
    __tablename__ = "permissions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    resource: str = Field(max_length=50, index=True)
    action: str = Field(max_length=50)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    roles: List["RolePermission"] = Relationship(back_populates="permission")

class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    role_id: int = Field(foreign_key="roles.id")
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: Optional[int] = Field(foreign_key="users.id", default=None)
    
    # Relationships
    user: User = Relationship(
        back_populates="roles",
        sa_relationship_kwargs={"foreign_keys": "[UserRole.user_id]"}
    )
    role: Role = Relationship(back_populates="users")

class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id")
    permission_id: int = Field(foreign_key="permissions.id")
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    role: Role = Relationship(back_populates="permissions")
    permission: Permission = Relationship(back_populates="roles")

class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"
    
    id: str = Field(primary_key=True, max_length=255)
    user_id: int = Field(foreign_key="users.id", index=True)
    ip_address: Optional[str] = Field(max_length=45, default=None)
    user_agent: Optional[str] = None
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="sessions")

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(foreign_key="users.id", index=True, default=None)
    user_email: Optional[str] = Field(max_length=255, default=None)
    action: str = Field(max_length=100, index=True)
    resource: str = Field(max_length=100, index=True)
    resource_id: Optional[str] = Field(max_length=100, default=None)
    old_values: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    new_values: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    ip_address: Optional[str] = Field(max_length=45, default=None)
    user_agent: Optional[str] = None
    status: AuditStatus = Field(default=AuditStatus.SUCCESS, index=True)
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="audit_logs")

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
