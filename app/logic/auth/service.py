from typing import Optional, List
from datetime import datetime, timedelta
from sqlmodel import Session, select
from passlib.context import CryptContext
import secrets
import uuid

from models.user import (
    User, UserCreate, UserUpdate, Role, Permission, UserRole, RolePermission,
    UserSession, AuditLog, UserStatus, AuditStatus, UserResponse, RoleResponse
)
from db.database import engine

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_user(user_data: UserCreate, created_by: Optional[int] = None) -> User:
        with Session(engine) as session:
            # Hash password
            password_hash = UserService.hash_password(user_data.password)
            
            # Create user dict without password
            user_dict = user_data.dict(exclude={"password", "role_id"})
            user_dict["password_hash"] = password_hash
            user_dict["created_by"] = created_by
            
            user = User(**user_dict)
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Assign role if provided
            if user_data.role_id:
                UserService.assign_role_to_user(user.id, user_data.role_id, created_by)
            
            return user
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        with Session(engine) as session:
            # Try to find user by username or email
            user = session.exec(
                select(User).where(
                    (User.username == username) | (User.email == username)
                )
            ).first()
            if not user or not UserService.verify_password(password, user.password_hash):
                return None
            if user.status != UserStatus.ACTIVE:
                return None
            return user
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        with Session(engine) as session:
            return session.get(User, user_id)
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        with Session(engine) as session:
            return session.exec(select(User).where(User.username == username)).first()
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        with Session(engine) as session:
            return session.exec(select(User).where(User.email == email)).first()
    
    @staticmethod
    def update_user(user_id: int, user_data: UserUpdate, updated_by: Optional[int] = None) -> Optional[User]:
        with Session(engine) as session:
            user = session.get(User, user_id)
            if not user:
                return None
            
            # Store old values for audit
            old_values = {
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "status": user.status,
                "department": user.department
            }
            
            # Update user fields
            update_data = user_data.dict(exclude_unset=True, exclude={"role_id"})
            for field, value in update_data.items():
                setattr(user, field, value)
            
            user.updated_at = datetime.utcnow()
            session.add(user)
            
            # Update role if provided
            if user_data.role_id:
                UserService.assign_role_to_user(user_id, user_data.role_id, updated_by)
            
            session.commit()
            session.refresh(user)
            
            # Log audit
            new_values = update_data.copy()
            if user_data.role_id:
                new_values["role_id"] = user_data.role_id
            
            AuditService.log_action(
                user_id=updated_by,
                action="update",
                resource="users",
                resource_id=str(user_id),
                old_values=old_values,
                new_values=new_values
            )
            
            return user
    
    @staticmethod
    def delete_user(user_id: int, deleted_by: Optional[int] = None) -> bool:
        with Session(engine) as session:
            user = session.get(User, user_id)
            if not user:
                return False
            
            session.delete(user)
            session.commit()
            
            # Log audit
            AuditService.log_action(
                user_id=deleted_by,
                action="delete",
                resource="users",
                resource_id=str(user_id),
                old_values={"username": user.username, "email": user.email}
            )
            
            return True
    
    @staticmethod
    def get_user_permissions(user_id: int) -> List[str]:
        with Session(engine) as session:
            # Get user roles and their permissions
            query = (
                select(Permission.name)
                .join(RolePermission, Permission.id == RolePermission.permission_id)
                .join(Role, RolePermission.role_id == Role.id)
                .join(UserRole, Role.id == UserRole.role_id)
                .where(UserRole.user_id == user_id)
            )
            permissions = session.exec(query).all()
            return list(permissions)
    
    @staticmethod
    def get_user_roles(user_id: int) -> List[Role]:
        with Session(engine) as session:
            query = (
                select(Role)
                .join(UserRole, Role.id == UserRole.role_id)
                .where(UserRole.user_id == user_id)
            )
            return list(session.exec(query).all())
    
    @staticmethod
    def assign_role_to_user(user_id: int, role_id: int, assigned_by: Optional[int] = None):
        with Session(engine) as session:
            # Remove existing roles
            existing_roles = session.exec(select(UserRole).where(UserRole.user_id == user_id)).all()
            for role in existing_roles:
                session.delete(role)
            
            # Assign new role
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by
            )
            session.add(user_role)
            session.commit()
    
    @staticmethod
    def update_last_login(user_id: int):
        with Session(engine) as session:
            user = session.get(User, user_id)
            if user:
                user.last_login_at = datetime.utcnow()
                session.add(user)
                session.commit()

class RoleService:
    @staticmethod
    def get_all_roles() -> List[Role]:
        with Session(engine) as session:
            return list(session.exec(select(Role)).all())
    
    @staticmethod
    def get_role_by_id(role_id: int) -> Optional[Role]:
        with Session(engine) as session:
            return session.get(Role, role_id)
    
    @staticmethod
    def get_role_permissions(role_id: int) -> List[str]:
        with Session(engine) as session:
            query = (
                select(Permission.name)
                .join(RolePermission, Permission.id == RolePermission.permission_id)
                .where(RolePermission.role_id == role_id)
            )
            return list(session.exec(query).all())

class PermissionService:
    @staticmethod
    def get_all_permissions() -> List[Permission]:
        with Session(engine) as session:
            return list(session.exec(select(Permission)).all())
    
    @staticmethod
    def get_permissions_by_resource(resource: str) -> List[Permission]:
        with Session(engine) as session:
            return list(session.exec(select(Permission).where(Permission.resource == resource)).all())

class SessionService:
    @staticmethod
    def create_session(user_id: int, ip_address: str, user_agent: str, expires_in_hours: int = 24) -> UserSession:
        with Session(engine) as session:
            session_id = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            user_session = UserSession(
                id=session_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at
            )
            
            session.add(user_session)
            session.commit()
            return user_session
    
    @staticmethod
    def get_session(session_id: str) -> Optional[UserSession]:
        with Session(engine) as session:
            return session.get(UserSession, session_id)
    
    @staticmethod
    def invalidate_session(session_id: str) -> bool:
        with Session(engine) as session:
            user_session = session.get(UserSession, session_id)
            if user_session:
                user_session.is_active = False
                session.add(user_session)
                session.commit()
                return True
            return False
    
    @staticmethod
    def cleanup_expired_sessions():
        with Session(engine) as session:
            expired_sessions = session.exec(
                select(UserSession).where(UserSession.expires_at < datetime.utcnow())
            ).all()
            for sess in expired_sessions:
                session.delete(sess)
            session.commit()

class AuditService:
    @staticmethod
    def log_action(
        user_id: Optional[int],
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: AuditStatus = AuditStatus.SUCCESS,
        error_message: Optional[str] = None
    ):
        with Session(engine) as session:
            user_email = None
            if user_id:
                user = session.get(User, user_id)
                if user:
                    user_email = user.email
            
            audit_log = AuditLog(
                user_id=user_id,
                user_email=user_email,
                action=action,
                resource=resource,
                resource_id=resource_id,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                error_message=error_message
            )
            
            session.add(audit_log)
            session.commit()

# Legacy functions for backward compatibility
def create_user(user_data):
    if hasattr(user_data, 'username') and hasattr(user_data, 'password'):
        user_create = UserCreate(
            username=user_data.username,
            password=user_data.password,
            email=f"{user_data.username}@example.com",  # Default email
            full_name=user_data.username
        )
        return UserService.create_user(user_create)
    return UserService.create_user(user_data)

def authenticate_user(user_data):
    if hasattr(user_data, 'username') and hasattr(user_data, 'password'):
        return UserService.authenticate_user(user_data.username, user_data.password)
    return None

