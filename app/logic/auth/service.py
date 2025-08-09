from typing import Optional, List
from datetime import datetime, timedelta
from sqlmodel import Session, select, func
from passlib.context import CryptContext
import secrets
import uuid

from models.user import (
    User, UserCreate, UserUpdate,
    UserSession, AuditLog, UserStatus, AuditStatus
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
    def create_user(user_data: UserCreate, created_by: Optional[int] = None, status: Optional[str] = None) -> User:
        with Session(engine) as session:
            # Hash password
            password_hash = UserService.hash_password(user_data.password)
            
            # Create user with specified status (default to active for admin-created users)
            user = User(
                username=user_data.username,
                password=password_hash,
                email=getattr(user_data, 'email', None),
                full_name=getattr(user_data, 'full_name', user_data.username),
                status=status or "active",  # Use provided status or default to active
                is_active=True
            )
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
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
            if not user or not UserService.verify_password(password, user.password):
                return None
            # Check if user status allows login
            if hasattr(user, 'status') and user.status:
                # Only active users can login
                if user.status not in ["active"]:
                    return None
            if hasattr(user, 'is_active') and not user.is_active:
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
    def get_user_permissions(user_id: int) -> List:
        return []
    
    @staticmethod
    def get_user_roles(user_id: int) -> List:
        return []
    
    
    @staticmethod
    def update_last_login(user_id: int):
        with Session(engine) as session:
            user = session.get(User, user_id)
            if user:
                user.last_login_at = datetime.utcnow()
                session.add(user)
                session.commit()


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
        """Mark expired sessions as inactive (soft delete approach)"""
        with Session(engine) as session:
            expired_sessions = session.exec(
                select(UserSession)
                .where(UserSession.expires_at < datetime.utcnow())
                .where(UserSession.is_active == True)
            ).all()
            
            cleanup_count = 0
            for sess in expired_sessions:
                sess.is_active = False  # Soft delete - keep for audit trail
                session.add(sess)
                cleanup_count += 1
            
            session.commit()
            return cleanup_count
    
    @staticmethod
    def invalidate_user_sessions(user_id: int) -> int:
        """Invalidate all active sessions for a user"""
        with Session(engine) as session:
            active_sessions = session.exec(
                select(UserSession)
                .where(UserSession.user_id == user_id)
                .where(UserSession.is_active == True)
            ).all()
            
            invalidated_count = 0
            for sess in active_sessions:
                sess.is_active = False
                session.add(sess)
                invalidated_count += 1
            
            session.commit()
            return invalidated_count
    
    @staticmethod
    def get_active_sessions_count() -> int:
        """Get count of currently active sessions"""
        with Session(engine) as session:
            return session.exec(
                select(func.count(UserSession.id))
                .where(UserSession.is_active == True)
                .where(UserSession.expires_at > datetime.utcnow())
            ).one()

class TokenStatusService:
    @staticmethod
    def revoke_token(jti: str, reason: str = "admin_revoked"):
        """Revoke a specific token by JWT ID"""
        with Session(engine) as session:
            session_updated = session.exec(
                select(UserSession).where(UserSession.token_jti == jti)
            ).first()
            
            if session_updated:
                session_updated.token_status = "revoked"
                session_updated.is_active = False
                session.add(session_updated)
                session.commit()
                return True
            return False
    
    @staticmethod
    def get_token_status(jti: str) -> str:
        """Get current token status ('active', 'revoked', 'expired', or 'not_found')"""
        with Session(engine) as session:
            user_session = session.exec(
                select(UserSession).where(UserSession.token_jti == jti)
            ).first()
            
            if not user_session:
                return "not_found"
            
            # Check if token is expired
            if user_session.expires_at < datetime.utcnow():
                # Auto-mark as expired if not already
                if user_session.token_status == "active":
                    user_session.token_status = "expired"
                    session.add(user_session)
                    session.commit()
                return "expired"
            
            return user_session.token_status
    
    @staticmethod
    def revoke_all_user_tokens(user_id: int, reason: str = "force_logout"):
        """Revoke all active tokens for a user (force logout)"""
        with Session(engine) as session:
            active_sessions = session.exec(
                select(UserSession)
                .where(UserSession.user_id == user_id)
                .where(UserSession.token_status == "active")
            ).all()
            
            revoked_count = len(active_sessions)
            for user_session in active_sessions:
                user_session.token_status = "revoked"
                user_session.is_active = False
                session.add(user_session)
            
            session.commit()
            return revoked_count
    
    @staticmethod
    def cleanup_expired_sessions():
        """Mark expired sessions"""
        with Session(engine) as session:
            expired_sessions = session.exec(
                select(UserSession)
                .where(UserSession.expires_at < datetime.utcnow())
                .where(UserSession.token_status == "active")
            ).all()
            
            for session_obj in expired_sessions:
                session_obj.token_status = "expired"
                session_obj.is_active = False
                session.add(session_obj)
            
            session.commit()
            return len(expired_sessions)

class AuditService:
    @staticmethod
    def log_business_event(
        user_id: Optional[int],
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ):
        """Log meaningful business events, not API requests"""
        with Session(engine) as session:
            user_email = None
            if user_id:
                user = session.get(User, user_id)
                if user:
                    user_email = user.email or user.username
            
            # Only log meaningful business events
            business_actions = [
                # Authentication events
                'user_login_success', 'user_login_failed', 'user_logout', 
                'session_expired', 'password_changed', 'password_reset_requested',
                
                # User management events
                'user_created', 'user_updated', 'user_deleted', 
                'user_suspended', 'user_activated', 'user_role_changed',
                'user_permissions_modified', 'user_approved', 'user_rejected',
                
                # System administration
                'role_created', 'role_updated', 'role_deleted',
                'system_settings_changed', 'data_exported', 'data_imported',
                'session_terminated'
            ]
            
            if action not in business_actions:
                return  # Skip non-business events
            
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
        """Legacy method for backward compatibility"""
        status_str = status.value if hasattr(status, 'value') else str(status)
        AuditService.log_business_event(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status_str,
            error_message=error_message
        )

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

