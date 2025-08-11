import csv
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Response, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, or_

from models.user import User, UserStatus
from logic.auth.service import UserService, AuditService
from logic.auth.security import require_user_management, audit_log
from db.database import engine

router = APIRouter(prefix="/admin", tags=["admin-export"])

@router.get("/users/export")
@audit_log("export", "users")
async def export_users(
    request: Request,
    format: str = Query("csv", regex="^(csv|xlsx)$"),
    status: Optional[UserStatus] = Query(None),
    department: Optional[str] = Query(None),
    current_user: User = Depends(require_user_management)
):
    """Export users to CSV or Excel format"""
    
    with Session(engine) as session:
        # Build query with filters
        query = select(User)
        
        if status:
            query = query.where(User.status == status)
        if department:
            query = query.where(User.department == department)
        
        users = session.exec(query).all()
        
        if format == "csv":
            return export_users_csv(users)
        elif format == "xlsx":
            return export_users_xlsx(users)

def export_users_csv(users: List[User]) -> StreamingResponse:
    """Export users to CSV format"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Username", "Email", "Full Name", "Phone", "Status", 
        "Department", "Two Factor Enabled", "Email Verified", 
        "Last Login", "Created At", "Updated At"
    ])
    
    # Write data
    for user in users:
        writer.writerow([
            user.id,
            user.username,
            user.email,
            user.full_name,
            user.phone or "",
            user.status.value,
            user.department or "",
            user.two_factor_enabled,
            user.email_verified,
            user.last_login_at.isoformat() if user.last_login_at else "",
            user.created_at.isoformat(),
            user.updated_at.isoformat()
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_export.csv"}
    )

def export_users_xlsx(users: List[User]) -> StreamingResponse:
    """Export users to Excel format"""
    # For simplicity, return CSV format
    # In production, you would use openpyxl or xlsxwriter
    return export_users_csv(users)

@router.post("/users/import")
@audit_log("import", "users")
async def import_users(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_user_management)
):
    """Import users from CSV file"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    content = await file.read()
    csv_content = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    
    imported = 0
    failed = 0
    errors = []
    
    for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because of header
        try:
            # Validate required fields
            required_fields = ['username', 'email', 'full_name']
            missing_fields = [field for field in required_fields if not row.get(field)]
            
            if missing_fields:
                errors.append(f"Row {row_num}: Missing required fields: {', '.join(missing_fields)}")
                failed += 1
                continue
            
            # Check if user already exists
            existing_user = UserService.get_user_by_username(row['username'])
            if existing_user:
                errors.append(f"Row {row_num}: Username '{row['username']}' already exists")
                failed += 1
                continue
            
            existing_email = UserService.get_user_by_email(row['email'])
            if existing_email:
                errors.append(f"Row {row_num}: Email '{row['email']}' already exists")
                failed += 1
                continue
            
            # Create user data
            from models.user import UserCreate
            user_data = UserCreate(
                username=row['username'],
                email=row['email'],
                full_name=row['full_name'],
                phone=row.get('phone', ''),
                password='TempPassword123!',  # Temporary password - should be changed on first login
                department=row.get('department', ''),
                status=UserStatus(row.get('status', 'pending').lower()) if row.get('status') else UserStatus.PENDING
            )
            
            # Create user
            UserService.create_user(user_data, created_by=current_user.id)
            imported += 1
            
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            failed += 1
    
    # Log import results
    AuditService.log_action(
        user_id=current_user.id,
        action="import",
        resource="users",
        new_values={
            "imported": imported,
            "failed": failed,
            "filename": file.filename
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    
    return {
        "imported": imported,
        "failed": failed,
        "errors": errors[:10]  # Return only first 10 errors to avoid large responses
    }

@router.get("/users/template")
async def get_import_template(current_user: User = Depends(require_user_management)):
    """Download CSV template for user import"""
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header with example data
    writer.writerow([
        "username", "email", "full_name", "phone", "department", "status"
    ])
    writer.writerow([
        "john.doe", "john.doe@company.com", "John Doe", "+1234567890", "Engineering", "active"
    ])
    writer.writerow([
        "jane.smith", "jane.smith@company.com", "Jane Smith", "+1234567891", "Marketing", "pending"
    ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=user_import_template.csv"}
    )