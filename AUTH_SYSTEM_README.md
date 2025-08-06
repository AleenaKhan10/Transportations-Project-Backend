# AGY Intelligence Hub - Authentication & Admin System

This document describes the comprehensive authentication and admin management system implemented for the AGY Intelligence Hub backend.

## Overview

The system provides:
- **Role-Based Access Control (RBAC)** with flexible permissions
- **User Management** with full CRUD operations
- **Session Management** and tracking
- **Audit Logging** for all admin actions
- **JWT-based Authentication** with refresh tokens
- **Rate Limiting** and security middleware
- **Export/Import** functionality for bulk operations

## Database Schema

The system uses the following main tables:
- `users` - User accounts with profiles and settings
- `roles` - System roles (Super Admin, Manager, Operator, Viewer)
- `permissions` - Granular permissions for different resources
- `user_roles` - Junction table linking users to roles
- `role_permissions` - Junction table linking roles to permissions
- `user_sessions` - Active user sessions
- `audit_logs` - Complete audit trail of all actions

## Setup Instructions

### 1. Database Setup

#### Option A: Use the setup script (Recommended)
```bash
cd app
python setup_database.py
```

#### Option B: Run SQL manually
```bash
mysql -u your_user -p your_database < ../database_setup.sql
```

### 2. Environment Variables

Add these to your `.env` file:
```env
# JWT Settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database (existing)
DB_USER=your_db_user
DB_PASS=your_db_password
DB_HOST=your_db_host
DB_NAME=your_db_name

# Optional: For session cleanup
REDIS_URL=redis://localhost:6379
```

### 3. Dependencies

The system requires these additional Python packages:
```bash
pip install python-jose[cryptography] passlib[bcrypt] python-multipart
```

## Default Admin Account

After setup, you can login with:
- **Username**: `admin`
- **Password**: `admin123`

**⚠️ IMPORTANT: Change this password immediately in production!**

## API Endpoints

### Authentication Endpoints

#### POST /auth/login
Login with username/password and receive JWT tokens.

**Request:**
```json
{
  "username": "admin",
  "password": "admin123",
  "grant_type": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@agylogistics.com",
    "role": {
      "name": "Super Admin",
      "permissions": ["Manage Users", "View Dashboard", ...]
    }
  }
}
```

#### POST /auth/users
Create a new user (requires authentication).

#### POST /auth/refresh
Refresh access token using refresh token.

#### POST /auth/logout
Logout and invalidate session.

### User Management Endpoints (Admin)

#### GET /admin/users
List all users with filtering and pagination.

**Query Parameters:**
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20)
- `search` - Search in username, email, full_name
- `status` - Filter by user status
- `department` - Filter by department

#### GET /admin/users/{id}
Get user details by ID.

#### PUT /admin/users/{id}
Update user information.

#### DELETE /admin/users/{id}
Delete user.

#### POST /admin/users/{id}/suspend
Suspend user account.

#### POST /admin/users/{id}/activate
Activate user account.

#### GET /admin/users/stats
Get user statistics dashboard.

### Role Management Endpoints

#### GET /admin/roles
List all roles with permissions.

#### POST /admin/roles
Create new role.

#### PUT /admin/roles/{id}
Update role and permissions.

#### DELETE /admin/roles/{id}
Delete role (if not in use).

### Permission Endpoints

#### GET /admin/permissions
List all available permissions.

#### GET /admin/permissions/resource/{resource}
Get permissions for specific resource.

### Session Management

#### GET /admin/sessions
List active user sessions.

#### DELETE /admin/sessions/{id}
Terminate specific session.

#### DELETE /admin/sessions/user/{user_id}
Terminate all sessions for a user.

### Audit Logs

#### GET /admin/audit-logs
View audit logs with filtering.

**Query Parameters:**
- `user_id` - Filter by user
- `action` - Filter by action type
- `resource` - Filter by resource
- `start_date` - Filter by date range
- `end_date` - Filter by date range

### Export/Import

#### GET /admin/users/export?format=csv
Export users to CSV/Excel.

#### POST /admin/users/import
Import users from CSV file.

#### GET /admin/users/template
Download CSV template for import.

## Default Roles and Permissions

### Super Admin
- Full system access
- All permissions granted

### Manager
- User management (view/create/edit)
- Report access
- View trailers, drivers, alerts

### Operator
- Dashboard access
- View-only access to reports, trailers, drivers, alerts

### Viewer
- Dashboard access
- View-only access to reports and basic data

## Security Features

### 1. Authentication
- JWT tokens with configurable expiration
- Refresh token mechanism
- Secure password hashing with bcrypt

### 2. Authorization
- Role-based access control
- Granular permissions per resource/action
- Permission checking middleware

### 3. Rate Limiting
- Login attempts: 5 per 15 minutes
- Password reset: 3 per hour
- Admin endpoints: 100 per minute per user

### 4. Audit Logging
- All admin actions logged
- Authentication events tracked
- IP address and user agent recorded
- Success/failure status tracked

### 5. Session Management
- Session tracking and cleanup
- Force logout capability
- Expired session cleanup

## Usage Examples

### 1. Login and Get Token
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123&grant_type=password"
```

### 2. Create New User
```bash
curl -X POST "http://localhost:8000/auth/users" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "email": "john@company.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "department": "Engineering",
    "role_id": 2
  }'
```

### 3. List Users with Filtering
```bash
curl -X GET "http://localhost:8000/admin/users?page=1&limit=10&status=active" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Export Users
```bash
curl -X GET "http://localhost:8000/admin/users/export?format=csv" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o users_export.csv
```

## Migration from Existing System

If you have existing users in the old format, the system provides backward compatibility:
- Old `User` model is still supported
- Legacy authentication functions work
- Gradual migration can be performed

## Troubleshooting

### Common Issues

1. **"Permission denied" errors**
   - Ensure user has correct role assigned
   - Check if role has required permissions

2. **"Token expired" errors**
   - Use refresh token to get new access token
   - Check token expiration settings

3. **Rate limiting errors**
   - Wait for rate limit window to reset
   - Check if too many requests from same IP

4. **Database connection errors**
   - Verify database credentials
   - Ensure database tables are created

### Logging

All authentication and admin actions are logged in the `audit_logs` table. Use the audit endpoints to investigate issues.

## Production Deployment

### Security Checklist

- [ ] Change default admin password
- [ ] Use strong SECRET_KEY for JWT
- [ ] Enable HTTPS in production
- [ ] Configure proper CORS settings
- [ ] Set up Redis for session storage
- [ ] Enable rate limiting with Redis backend
- [ ] Regular backup of audit logs
- [ ] Monitor for suspicious activities

### Performance Optimization

- [ ] Database indexing on frequently queried columns
- [ ] Connection pooling for database
- [ ] Caching for user permissions and roles
- [ ] Regular cleanup of expired sessions

## API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

This provides interactive API documentation for all endpoints.

## Support

For issues or questions about the authentication system:
1. Check the audit logs for detailed error information
2. Verify user permissions and role assignments
3. Check server logs for technical issues
4. Ensure all environment variables are properly set