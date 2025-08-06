from typing import Optional
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlmodel import Session, select, func

from models.user import User, UserSession
from logic.auth.service import SessionService, AuditService
from logic.auth.security import get_current_active_user, audit_log
from db.database import engine

router = APIRouter(prefix="/admin", tags=["admin-sessions"])

class SessionResponse(dict):
    def __init__(self, id: str, user_id: int, user_email: str, ip_address: str = None, 
                 user_agent: str = None, last_activity=None, expires_at=None, is_active: bool = True):
        super().__init__()
        self['id'] = id
        self['user_id'] = user_id
        self['user_email'] = user_email
        self['ip_address'] = ip_address
        self['user_agent'] = user_agent
        self['last_activity'] = last_activity
        self['expires_at'] = expires_at
        self['is_active'] = is_active

@router.get("/sessions")
@audit_log("list", "sessions")
async def get_sessions(
    request: Request,
    user_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """Get active sessions"""
    with Session(engine) as session:
        query = select(UserSession, User.email).join(User, UserSession.user_id == User.id)
        
        if user_id:
            query = query.where(UserSession.user_id == user_id)
        
        # Only show active sessions
        query = query.where(UserSession.is_active == True)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = session.exec(count_query).one()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        results = session.exec(query).all()
        
        sessions = []
        for user_session, user_email in results:
            sessions.append(SessionResponse(
                id=user_session.id,
                user_id=user_session.user_id,
                user_email=user_email,
                ip_address=user_session.ip_address,
                user_agent=user_session.user_agent,
                last_activity=user_session.last_activity,
                expires_at=user_session.expires_at,
                is_active=user_session.is_active
            ))
        
        return {
            "sessions": sessions,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": ceil(total / limit)
        }

@router.get("/sessions/{session_id}")
@audit_log("view", "sessions")
async def get_session(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get session by ID"""
    with Session(engine) as session:
        result = session.exec(
            select(UserSession, User.email)
            .join(User, UserSession.user_id == User.id)
            .where(UserSession.id == session_id)
        ).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        user_session, user_email = result
        
        return SessionResponse(
            id=user_session.id,
            user_id=user_session.user_id,
            user_email=user_email,
            ip_address=user_session.ip_address,
            user_agent=user_session.user_agent,
            last_activity=user_session.last_activity,
            expires_at=user_session.expires_at,
            is_active=user_session.is_active
        )

@router.delete("/sessions/{session_id}")
@audit_log("terminate", "sessions")
async def terminate_session(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Terminate session"""
    success = SessionService.invalidate_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Log session termination
    AuditService.log_action(
        user_id=current_user.id,
        action="terminate",
        resource="sessions",
        resource_id=session_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    return {"message": "Session terminated successfully"}

@router.delete("/sessions/user/{user_id}")
@audit_log("terminate_all", "sessions")
async def terminate_user_sessions(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Terminate all user sessions"""
    with Session(engine) as session:
        # Get all active sessions for the user
        user_sessions = session.exec(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        ).all()
        
        # Invalidate all sessions
        terminated_count = 0
        for user_session in user_sessions:
            user_session.is_active = False
            session.add(user_session)
            terminated_count += 1
        
        session.commit()
        
        # Log bulk session termination
        AuditService.log_action(
            user_id=current_user.id,
            action="terminate_all",
            resource="sessions",
            resource_id=str(user_id),
            new_values={"terminated_count": terminated_count},
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent")
        )
        
        return {"message": f"Terminated {terminated_count} sessions successfully"}

@router.post("/sessions/cleanup")
@audit_log("cleanup", "sessions")
async def cleanup_expired_sessions(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Cleanup expired sessions"""
    SessionService.cleanup_expired_sessions()
    
    return {"message": "Expired sessions cleaned up successfully"}