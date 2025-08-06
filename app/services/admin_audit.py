from typing import Optional
from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Request, Query
from sqlmodel import Session, select, func, and_

from models.user import User, AuditLog, AuditStatus
from logic.auth.security import require_audit_view, audit_log
from db.database import engine

router = APIRouter(prefix="/admin", tags=["admin-audit"])

class AuditLogResponse(dict):
    def __init__(self, id: int, user_id: int = None, user_email: str = None, 
                 action: str = None, resource: str = None, resource_id: str = None,
                 changes: dict = None, ip_address: str = None, user_agent: str = None,
                 status: str = None, error_message: str = None, timestamp=None):
        super().__init__()
        self['id'] = id
        self['user_id'] = user_id
        self['user_email'] = user_email
        self['action'] = action
        self['resource'] = resource
        self['resource_id'] = resource_id
        self['changes'] = changes or {}
        self['ip_address'] = ip_address
        self['user_agent'] = user_agent
        self['status'] = status
        self['error_message'] = error_message
        self['timestamp'] = timestamp

@router.get("/audit-logs")
@audit_log("list", "audit")
async def get_audit_logs(
    request: Request,
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    resource: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_audit_view)
):
    """Get audit logs with filtering"""
    with Session(engine) as session:
        query = select(AuditLog)
        
        # Apply filters
        filters = []
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if action:
            filters.append(AuditLog.action == action)
        if resource:
            filters.append(AuditLog.resource == resource)
        if start_date:
            filters.append(AuditLog.timestamp >= start_date)
        if end_date:
            filters.append(AuditLog.timestamp <= end_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(AuditLog.timestamp.desc())
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = session.exec(count_query).one()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        audit_logs = session.exec(query).all()
        
        # Build response
        logs = []
        for log in audit_logs:
            changes = {}
            if log.old_values or log.new_values:
                changes = {
                    "old": log.old_values,
                    "new": log.new_values
                }
            
            logs.append(AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                user_email=log.user_email,
                action=log.action,
                resource=log.resource,
                resource_id=log.resource_id,
                changes=changes,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                status=log.status.value if log.status else None,
                error_message=log.error_message,
                timestamp=log.timestamp
            ))
        
        return {
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": ceil(total / limit)
        }

@router.get("/audit-logs/actions")
@audit_log("list_actions", "audit")
async def get_audit_actions(
    request: Request,
    current_user: User = Depends(require_audit_view)
):
    """Get all unique audit actions"""
    with Session(engine) as session:
        actions = session.exec(select(AuditLog.action).distinct()).all()
        return list(actions)

@router.get("/audit-logs/resources")
@audit_log("list_resources", "audit")
async def get_audit_resources(
    request: Request,
    current_user: User = Depends(require_audit_view)
):
    """Get all unique audit resources"""
    with Session(engine) as session:
        resources = session.exec(select(AuditLog.resource).distinct()).all()
        return list(resources)

@router.get("/audit-logs/stats")
@audit_log("stats", "audit")
async def get_audit_stats(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(require_audit_view)
):
    """Get audit log statistics"""
    with Session(engine) as session:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = start_date.replace(day=start_date.day - days + 1)
        
        # Total logs in period
        total_logs = session.exec(
            select(func.count(AuditLog.id))
            .where(AuditLog.timestamp >= start_date)
        ).one()
        
        # Success vs failure counts
        success_logs = session.exec(
            select(func.count(AuditLog.id))
            .where(
                and_(
                    AuditLog.timestamp >= start_date,
                    AuditLog.status == AuditStatus.SUCCESS
                )
            )
        ).one()
        
        failure_logs = session.exec(
            select(func.count(AuditLog.id))
            .where(
                and_(
                    AuditLog.timestamp >= start_date,
                    AuditLog.status == AuditStatus.FAILURE
                )
            )
        ).one()
        
        # Top actions
        top_actions = session.exec(
            select(AuditLog.action, func.count(AuditLog.id).label('count'))
            .where(AuditLog.timestamp >= start_date)
            .group_by(AuditLog.action)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        ).all()
        
        # Top resources
        top_resources = session.exec(
            select(AuditLog.resource, func.count(AuditLog.id).label('count'))
            .where(AuditLog.timestamp >= start_date)
            .group_by(AuditLog.resource)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        ).all()
        
        return {
            "period_days": days,
            "total_logs": total_logs,
            "success_logs": success_logs,
            "failure_logs": failure_logs,
            "top_actions": [{"action": action, "count": count} for action, count in top_actions],
            "top_resources": [{"resource": resource, "count": count} for resource, count in top_resources]
        }